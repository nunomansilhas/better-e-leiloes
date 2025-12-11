"""
Web Scraper para E-Leiloes.pt usando Playwright
"""

import sys
import asyncio

# Fix para Windows - asyncio subprocess com Playwright
# CRÍTICO: WindowsProactorEventLoopPolicy suporta subprocessos
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from typing import List, Optional
from datetime import datetime
import re
from playwright.async_api import async_playwright, Page, Browser
import os

from models import EventData, GPSCoordinates, EventDetails, ValoresLeilao, ScraperStatus


class EventScraper:
    """Scraper assíncrono para e-leiloes.pt"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        
        # Status tracking
        self.is_running = False
        self.events_processed = 0
        self.events_failed = 0
        self.current_page = None
        self.started_at = None
        self.last_update = None
        
        # Config
        self.delay = float(os.getenv("SCRAPE_DELAY", 0.8))
        self.concurrent = int(os.getenv("CONCURRENT_REQUESTS", 4))
        self.user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    async def init_browser(self):
        """Inicializa browser Playwright"""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
    
    async def close(self):
        """Fecha browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_event(self, reference: str) -> EventData:
        """
        Scrape público de um único evento por referência.
        Detecta automaticamente se é imóvel (LO) ou móvel (NP) pela referência.

        Args:
            reference: Referência do evento (ex: LO1234567890 ou NP1234567890)

        Returns:
            EventData completo do evento
        """
        await self.init_browser()

        # Determina tipo baseado no prefixo da referência
        # LO = Leilão Online (geralmente imóveis)
        # NP = Negociação Particular (pode ser móveis ou imóveis)
        # Para segurança, vamos tentar buscar a página e detectar o tipo
        tipo_evento = "imovel" if reference.startswith("LO") else "imovel"  # default imovel

        # Cria preview fake (valores virão da página individual)
        preview = {
            'reference': reference,
            'valores': ValoresLeilao()  # Vazio, será preenchido na página
        }

        try:
            return await self._scrape_event_details(preview, tipo_evento)
        except Exception as e:
            raise Exception(f"Erro ao fazer scrape do evento {reference}: {str(e)}")

    async def _scrape_event_details(self, preview: dict, tipo_evento: str) -> EventData:
        """
        FASE 2: Entra na página individual para extrair detalhes completos
        
        Args:
            preview: Dict com {reference, valores} da listagem
            tipo_evento: "imovel" ou "movel"
        """
        reference = preview['reference']
        valores_listagem = preview['valores']
        
        url = f"https://www.e-leiloes.pt/evento/{reference}"
        
        context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navega para página do evento
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await asyncio.sleep(1.5)

            # Extrai datas do evento
            data_inicio, data_fim = await self._extract_dates(page)

            # GPS (apenas para imóveis)
            gps = None
            if tipo_evento == "imovel":
                gps = await self._extract_gps(page)

            # Detalhes (diferente para imovel vs movel)
            if tipo_evento == "imovel":
                detalhes = await self._extract_imovel_details(page)
            else:
                detalhes = await self._extract_movel_details(page)

            # Confirma/atualiza valores na página individual (podem ser mais precisos)
            valores_pagina = await self._extract_valores_from_page(page)

            # Merge valores (prioridade: página individual > listagem)
            valores_final = ValoresLeilao(
                valorBase=valores_pagina.valorBase or valores_listagem.valorBase,
                valorAbertura=valores_pagina.valorAbertura or valores_listagem.valorAbertura,
                valorMinimo=valores_pagina.valorMinimo or valores_listagem.valorMinimo,
                lanceAtual=valores_pagina.lanceAtual or valores_listagem.lanceAtual
            )

            # Extrai novas informações
            imagens = await self._extract_gallery(page)
            descricao = await self._extract_descricao(page)
            observacoes = await self._extract_observacoes(page)
            descricao_predial = await self._extract_descricao_predial(page)
            cerimonia = await self._extract_cerimonia(page)
            agente = await self._extract_agente(page)
            dados_processo = await self._extract_dados_processo(page)

            return EventData(
                reference=reference,
                tipoEvento=tipo_evento,
                valores=valores_final,
                gps=gps,
                detalhes=detalhes,
                dataInicio=data_inicio,
                dataFim=data_fim,
                imagens=imagens,
                descricao=descricao,
                observacoes=observacoes,
                descricaoPredial=descricao_predial,
                cerimoniaEncerramento=cerimonia,
                agenteExecucao=agente,
                dadosProcesso=dados_processo,
                scraped_at=datetime.utcnow()
            )
            
        except Exception as e:
            raise Exception(f"Erro ao scrape {reference}: {str(e)}")
        
        finally:
            await page.close()
            await context.close()
    
    async def _extract_dates(self, page: Page) -> tuple[Optional[datetime], Optional[datetime]]:
        """Extrai datas de início e fim do evento do DOM da página"""
        try:
            data_inicio = None
            data_fim = None

            # Procura por divs que contenham as datas
            # Estrutura: <div><span>Início:</span><span class="font-semibold">DATA</span></div>
            divs = await page.query_selector_all('div.flex.justify-content-between')

            for div in divs:
                text = await div.text_content()
                if not text:
                    continue

                text = text.strip()

                # Verifica se é a div de Início
                if 'Início:' in text:
                    # Busca o span com font-semibold dentro desta div
                    date_span = await div.query_selector('span.font-semibold')
                    if date_span:
                        value = await date_span.text_content()
                        if value:
                            try:
                                # Parse data no formato DD/MM/YYYY HH:MM:SS
                                data_inicio = datetime.strptime(value.strip(), '%d/%m/%Y %H:%M:%S')
                            except ValueError as e:
                                print(f"⚠️ Erro ao parsear data de início '{value}': {e}")

                # Verifica se é a div de Fim
                elif 'Fim:' in text:
                    # Busca o span com font-semibold dentro desta div
                    date_span = await div.query_selector('span.font-semibold')
                    if date_span:
                        value = await date_span.text_content()
                        if value:
                            try:
                                # Parse data no formato DD/MM/YYYY HH:MM:SS
                                data_fim = datetime.strptime(value.strip(), '%d/%m/%Y %H:%M:%S')
                            except ValueError as e:
                                print(f"⚠️ Erro ao parsear data de fim '{value}': {e}")

            return data_inicio, data_fim

        except Exception as e:
            print(f"⚠️ Erro ao extrair datas: {e}")
            return None, None

    async def _extract_gps(self, page: Page) -> GPSCoordinates:
        """Extrai coordenadas GPS do DOM da página (apenas da seção Localização)"""
        try:
            latitude = None
            longitude = None

            # Primeiro, encontra a div com título "Localização"
            localizacao_section = None
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Localização' in text.strip():
                    # Pega o elemento pai (a seção completa de localização)
                    localizacao_section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    break

            if not localizacao_section:
                print("⚠️ Seção 'Localização' não encontrada")
                return GPSCoordinates(latitude=None, longitude=None)

            # Agora procura GPS apenas dentro desta seção
            spans = await localizacao_section.query_selector_all('.font-semibold')

            for span in spans:
                text = await span.text_content()
                if not text:
                    continue

                text = text.strip()

                if text == 'GPS Latitude:':
                    # Pega próximo elemento (o valor)
                    next_el = await span.evaluate_handle('el => el.nextElementSibling')
                    if next_el:
                        value = await next_el.text_content()
                        if value:
                            try:
                                latitude = float(value.strip())
                            except ValueError:
                                pass

                elif text == 'GPS Longitude:':
                    next_el = await span.evaluate_handle('el => el.nextElementSibling')
                    if next_el:
                        value = await next_el.text_content()
                        if value:
                            try:
                                longitude = float(value.strip())
                            except ValueError:
                                pass

            return GPSCoordinates(latitude=latitude, longitude=longitude)

        except Exception as e:
            print(f"⚠️ Erro ao extrair GPS: {e}")
            return GPSCoordinates(latitude=None, longitude=None)

    async def _extract_gallery(self, page: Page) -> List[str]:
        """Extrai todas as URLs das imagens da galeria"""
        try:
            images = []
            # Procura por todas as imagens na galeria
            # Estrutura: div.p-galleria-item > div com style="background-image: url(...)"
            gallery_items = await page.query_selector_all('.p-galleria-item .p-evento-image, .p-evento-image')

            for item in gallery_items:
                style = await item.get_attribute('style')
                if style and 'background-image: url(' in style:
                    # Extrai URL do background-image
                    import re
                    match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                    if match:
                        url = match.group(1).replace('&quot;', '')
                        if url and url not in images:
                            images.append(url)

            print(f"📷 Galeria: {len(images)} imagens encontradas")
            return images

        except Exception as e:
            print(f"⚠️ Erro ao extrair galeria: {e}")
            return []

    async def _extract_descricao(self, page: Page) -> Optional[str]:
        """Extrai a descrição completa do bem"""
        try:
            # Procura pela seção "Descrição"
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Descrição' in text.strip():
                    # Pega o elemento pai (a seção completa)
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if section:
                        # Pega o próximo div após o título (que contém a descrição)
                        desc_div = await section.query_selector('div:not(.flex.flex-column)')
                        if desc_div:
                            descricao = await desc_div.text_content()
                            return descricao.strip() if descricao else None

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair descrição: {e}")
            return None

    async def _extract_observacoes(self, page: Page) -> Optional[str]:
        """Extrai as observações sobre o evento"""
        try:
            # Procura pela seção "Observações"
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Observações' in text.strip() or 'Observacoes' in text.strip():
                    # Pega o elemento pai (a seção completa)
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if section:
                        # Pega o próximo div após o título (que contém as observações)
                        obs_div = await section.query_selector('div:not(.flex.flex-column)')
                        if obs_div:
                            observacoes = await obs_div.text_content()
                            return observacoes.strip() if observacoes else None

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair observações: {e}")
            return None

    async def _extract_descricao_predial(self, page: Page):
        """Extrai informação da descrição predial"""
        try:
            from models import DescricaoPredial

            # Procura pela seção "Descrição Predial"
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Descrição Predial' in text.strip():
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if not section:
                        continue

                    # Extrai campos
                    numero_desc = None
                    fracao = None
                    distrito_code = None
                    concelho_code = None
                    freguesia_code = None
                    artigos = []

                    spans = await section.query_selector_all('.font-semibold')
                    for span in spans:
                        label = await span.text_content()
                        if not label:
                            continue

                        label = label.strip()

                        # Pega o próximo elemento (o valor)
                        next_el = await span.evaluate_handle('el => el.nextElementSibling')
                        if next_el:
                            value = await next_el.text_content()
                            if value:
                                value = value.strip()

                                if 'N.º da Descrição:' in label:
                                    numero_desc = value
                                elif 'Fração:' in label:
                                    fracao = value if value else None
                                elif 'Distrito:' in label:
                                    distrito_code = value
                                elif 'Concelho:' in label:
                                    concelho_code = value
                                elif 'Freguesia:' in label:
                                    freguesia_code = value

                    return DescricaoPredial(
                        numeroDescricao=numero_desc,
                        fracao=fracao,
                        distritoCode=distrito_code,
                        concelhoCode=concelho_code,
                        freguesiaCode=freguesia_code,
                        artigos=artigos
                    )

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair descrição predial: {e}")
            return None

    async def _extract_cerimonia(self, page: Page):
        """Extrai dados da cerimónia de encerramento"""
        try:
            from models import CerimoniaEncerramento

            # Procura pela seção "Cerimonia de Encerramento"
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Cerimonia' in text.strip() or 'Cerimónia' in text.strip():
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if not section:
                        continue

                    data = None
                    local = None
                    morada = None

                    spans = await section.query_selector_all('.font-semibold')
                    for span in spans:
                        label = await span.text_content()
                        if not label:
                            continue

                        label = label.strip()

                        next_el = await span.evaluate_handle('el => el.nextElementSibling')
                        if next_el:
                            value = await next_el.text_content()
                            if value:
                                value = value.strip()

                                if 'Data:' in label:
                                    try:
                                        # Parse ISO datetime
                                        data = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    except:
                                        pass
                                elif 'Local:' in label:
                                    local = value
                                elif 'Morada:' in label:
                                    morada = value

                    return CerimoniaEncerramento(
                        data=data,
                        local=local,
                        morada=morada
                    )

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair cerimónia: {e}")
            return None

    async def _extract_agente(self, page: Page):
        """Extrai dados do agente de execução"""
        try:
            from models import AgenteExecucao

            # Procura pela seção "Agente de Execução"
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Agente de Execução' in text.strip() or 'Agente de Execucao' in text.strip():
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if not section:
                        continue

                    # Pega todos os spans dentro da seção
                    all_spans = await section.query_selector_all('span')
                    nome = None
                    email = None
                    telefone = None

                    for span in all_spans:
                        value = await span.text_content()
                        if not value:
                            continue

                        value = value.strip()

                        # Detecta email
                        if '@' in value:
                            email = value
                        # Detecta telefone (simples)
                        elif value.replace(' ', '').isdigit() and len(value.replace(' ', '')) >= 9:
                            telefone = value
                        # Primeiro span não vazio é o nome
                        elif not nome and len(value) > 3:
                            nome = value

                    return AgenteExecucao(
                        nome=nome,
                        email=email,
                        telefone=telefone
                    )

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair agente: {e}")
            return None

    async def _extract_dados_processo(self, page: Page):
        """Extrai dados do processo judicial"""
        try:
            from models import DadosProcesso

            # Procura pela seção "Dados do Processo"
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Dados do Processo' in text.strip():
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if not section:
                        continue

                    processo = None
                    tribunal = None
                    unidade_organica = None
                    requerentes = []

                    spans = await section.query_selector_all('.font-semibold')
                    for span in spans:
                        label = await span.text_content()
                        if not label:
                            continue

                        label = label.strip()

                        next_el = await span.evaluate_handle('el => el.nextElementSibling')
                        if next_el:
                            value = await next_el.text_content()
                            if value:
                                value = value.strip()

                                if 'Processo:' in label:
                                    processo = value
                                elif 'Tribunal:' in label:
                                    tribunal = value
                                elif 'Unidade Orgânica:' in label or 'Unidade Organica:' in label:
                                    unidade_organica = value
                                elif 'Requerentes' in label or 'Requeridos' in label or 'Interessados' in label:
                                    # Pega todos os próximos spans com nomes
                                    parent = await next_el.evaluate_handle('el => el.parentElement')
                                    if parent:
                                        name_spans = await parent.query_selector_all('span:not(.font-semibold)')
                                        for name_span in name_spans:
                                            name = await name_span.text_content()
                                            if name and name.strip() and len(name.strip()) > 3:
                                                requerentes.append(name.strip())

                    return DadosProcesso(
                        processo=processo,
                        tribunal=tribunal,
                        unidadeOrganica=unidade_organica,
                        requerentes=requerentes
                    )

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair dados do processo: {e}")
            return None

    async def _extract_valores_from_page(self, page: Page) -> ValoresLeilao:
        """Extrai valores da página individual do evento"""
        valores = ValoresLeilao()
        
        try:
            # Procura por elementos com valores
            body_text = await page.text_content('body')
            
            # Regex para valores monetários
            value_patterns = {
                'valorBase': r'(?:valor\s+base|base)[:\s]*€?\s*([\d\s.]+,\d{2})',
                'valorAbertura': r'(?:valor\s+abertura|abertura)[:\s]*€?\s*([\d\s.]+,\d{2})',
                'valorMinimo': r'(?:valor\s+m[ií]nimo|m[ií]nimo)[:\s]*€?\s*([\d\s.]+,\d{2})',
                'lanceAtual': r'(?:lance\s+atual|atual)[:\s]*€?\s*([\d\s.]+,\d{2})'
            }
            
            for field, pattern in value_patterns.items():
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    value_str = match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                    setattr(valores, field, float(value_str))
                    
        except Exception as e:
            print(f"⚠️ Erro ao extrair valores da página: {e}")
        
        return valores
    
    async def _extract_imovel_details(self, page: Page) -> EventDetails:
        """Extrai detalhes COMPLETOS do IMÓVEL via DOM"""
        
        async def extract_detail(label: str) -> str:
            """Extrai valor de um campo específico"""
            try:
                # Procura por span.font-semibold com o label
                spans = await page.query_selector_all('.flex.w-full .font-semibold')
                
                for span in spans:
                    text = await span.text_content()
                    if text and text.strip() == label:
                        # Pega próximo elemento
                        next_el = await span.evaluate_handle('el => el.nextElementSibling')
                        if next_el:
                            value = await next_el.text_content()
                            return value.strip() if value else "N/A"
                
                return "N/A"
            except:
                return "N/A"
        
        async def extract_area(label: str) -> Optional[float]:
            """Extrai área em m²"""
            try:
                spans = await page.query_selector_all('.flex.w-full .font-semibold')
                
                for span in spans:
                    text = await span.text_content()
                    if text and text.strip() == label:
                        # Procura por span.mr-1 no wrapper
                        wrapper = await span.evaluate_handle('el => el.closest(".flex.w-full")')
                        if wrapper:
                            number_span = await wrapper.query_selector('span.mr-1')
                            if number_span:
                                value = await number_span.text_content()
                                # Remove espaços e converte para float
                                return float(value.replace(',', '.').strip())
                
                return None
            except:
                return None
        
        # Extrai todos os campos
        tipo = await extract_detail('Tipo:')
        subtipo = await extract_detail('Subtipo:')
        tipologia = await extract_detail('Tipologia:')
        distrito = await extract_detail('Distrito:')
        concelho = await extract_detail('Concelho:')
        freguesia = await extract_detail('Freguesia:')
        
        area_priv = await extract_area('Área Privativa:')
        area_dep = await extract_area('Área Dependente:')
        area_total = await extract_area('Área Total:')
        
        return EventDetails(
            tipo=tipo,
            subtipo=subtipo,
            tipologia=tipologia,
            areaPrivativa=area_priv,
            areaDependente=area_dep,
            areaTotal=area_total,
            distrito=distrito,
            concelho=concelho,
            freguesia=freguesia
        )
    
    async def _extract_movel_details(self, page: Page) -> EventDetails:
        """Extrai detalhes SIMPLIFICADOS do MÓVEL (automóvel) via DOM"""
        
        async def extract_detail(label: str) -> str:
            """Extrai valor de um campo específico"""
            try:
                spans = await page.query_selector_all('.flex.w-full .font-semibold')
                
                for span in spans:
                    text = await span.text_content()
                    if text and text.strip() == label:
                        next_el = await span.evaluate_handle('el => el.nextElementSibling')
                        if next_el:
                            value = await next_el.text_content()
                            return value.strip() if value else "N/A"
                
                return "N/A"
            except:
                return "N/A"
        
        # Extrai apenas os 3 campos necessários para móveis
        tipo = await extract_detail('Tipo:')
        subtipo = await extract_detail('Subtipo:')
        matricula = await extract_detail('Matrícula:')
        
        return EventDetails(
            tipo=tipo,
            subtipo=subtipo,
            matricula=matricula
        )
    
    async def scrape_all_events(self, max_pages: Optional[int] = None) -> List[EventData]:
        """
        Scrape TODOS os eventos (IMOVEIS + MOVEIS) do site
        
        Args:
            max_pages: Máximo de páginas para processar POR TIPO (None = todas)
            
        Returns:
            Lista com todos os eventos
        """
        self.is_running = True
        self.started_at = datetime.utcnow()
        self.events_processed = 0
        self.events_failed = 0
        
        all_events = []
        
        await self.init_browser()
        
        try:
            # 1. SCRAPE IMOVEIS (tipo=1)
            print("🏠 Iniciando scraping de IMÓVEIS...")
            imoveis = await self._scrape_by_type(tipo=1, max_pages=max_pages)
            all_events.extend(imoveis)
            print(f"✅ Imóveis recolhidos: {len(imoveis)}")
            
            # 2. SCRAPE MOVEIS (tipo=2)
            print("🚗 Iniciando scraping de MÓVEIS...")
            moveis = await self._scrape_by_type(tipo=2, max_pages=max_pages)
            all_events.extend(moveis)
            print(f"✅ Móveis recolhidos: {len(moveis)}")
            
            print(f"🎉 Total de eventos: {len(all_events)}")
            
            return all_events
            
        finally:
            self.is_running = False
    
    async def _scrape_by_type(self, tipo: int, max_pages: Optional[int] = None) -> List[EventData]:
        """
        Scrape eventos de um tipo específico (1=imovel, 2=movel)
        
        FASE 1: Extrai referências + valores da listagem
        FASE 2: Entra em cada evento para detalhes + GPS
        """
        tipo_nome = "imovel" if tipo == 1 else "movel"
        
        # FASE 1: Página de listagem
        events_preview = await self._extract_from_listing(tipo, max_pages)
        print(f"📋 {len(events_preview)} eventos {tipo_nome} encontrados na listagem")
        
        # FASE 2: Página individual (paralelo)
        all_events = []
        
        for i in range(0, len(events_preview), self.concurrent):
            batch = events_preview[i:i + self.concurrent]
            
            tasks = [
                self._scrape_event_details(preview, tipo_nome) 
                for preview in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, EventData):
                    all_events.append(result)
                    self.events_processed += 1
                else:
                    self.events_failed += 1
                    print(f"⚠️ Erro: {result}")
            
            print(f"📊 Processados: {self.events_processed} eventos {tipo_nome}")
            await asyncio.sleep(self.delay)
        
        return all_events
    
    async def _extract_from_listing(self, tipo: int, max_pages: Optional[int]) -> List[dict]:
        """
        FASE 1: Extrai referências + valores da página de listagem
        
        Usa paginação com first=0, first=12, first=24, etc. (12 eventos por página)
        
        Returns:
            Lista de dicts com {reference, valores}
        """
        context = await self.browser.new_context(user_agent=self.user_agent)
        page = await context.new_page()
        
        events_preview = []
        
        try:
            page_num = 0  # Começa em 0
            first_offset = 0  # Offset inicial
            
            while True:
                self.current_page = page_num + 1  # Para display (página 1, 2, 3...)
                
                # Navega para página de listagem com offset correto
                # https://www.e-leiloes.pt/eventos?layout=grid&first=0&sort=dataFimAsc&tipo=1
                url = f"https://www.e-leiloes.pt/eventos?layout=grid&first={first_offset}&sort=dataFimAsc&tipo={tipo}"
                print(f"🌐 Navegando para página {page_num + 1} (first={first_offset})...")
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(1.5)
                
                # Extrai cards
                cards = await page.query_selector_all('.p-evento')
                
                if not cards:
                    print(f"📄 Página {page_num} vazia - fim")
                    break
                
                count_before = len(events_preview)
                
                for card in cards:
                    try:
                        # Referência
                        ref_el = await card.query_selector('.pi-tag + span')
                        if not ref_el:
                            continue
                        
                        reference = (await ref_el.text_content()).strip()
                        
                        # Verifica duplicado
                        if any(e['reference'] == reference for e in events_preview):
                            continue
                        
                        # Extrai valores
                        valores = await self._extract_valores_from_card(card)
                        
                        events_preview.append({
                            'reference': reference,
                            'valores': valores
                        })
                        
                    except Exception as e:
                        print(f"⚠️ Erro ao extrair card: {e}")
                        continue
                
                count_new = len(events_preview) - count_before
                print(f"📄 Página {page_num + 1}: +{count_new} eventos (total: {len(events_preview)})")
                
                if count_new == 0:
                    break
                
                if max_pages and (page_num + 1) >= max_pages:
                    print(f"📄 Limite de {max_pages} páginas atingido")
                    break
                
                # Incrementa offset de 12 em 12
                page_num += 1
                first_offset += 12
            
            return events_preview
            
        finally:
            await page.close()
            await context.close()
    
    async def _extract_valores_from_card(self, card) -> ValoresLeilao:
        """Extrai valores (Base, Abertura, Mínimo, Lance Atual) de um card"""
        valores = ValoresLeilao()
        
        try:
            # Procura por spans com classes específicas de valores
            value_spans = await card.query_selector_all('span')
            
            for span in value_spans:
                text = await span.text_content()
                if not text:
                    continue
                
                text = text.strip().lower()
                
                # Extrai número (formato: "1.234,56 €" ou "1 234,56 €")
                match = re.search(r'([\d\s.]+,\d{2})\s*€', text)
                if not match:
                    continue
                
                value_str = match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                value = float(value_str)
                
                # Identifica tipo de valor pelo contexto
                parent_text = await card.evaluate('el => el.textContent')
                parent_lower = parent_text.lower()
                
                if 'base' in text or 'base' in parent_lower:
                    valores.valorBase = value
                elif 'abertura' in text or 'abertura' in parent_lower:
                    valores.valorAbertura = value
                elif 'mínimo' in text or 'minimo' in parent_lower:
                    valores.valorMinimo = value
                elif 'lance' in text or 'atual' in text or 'lance' in parent_lower:
                    valores.lanceAtual = value
                    
        except Exception as e:
            print(f"⚠️ Erro ao extrair valores: {e}")
        
        return valores
    
    async def _get_all_references(self, max_pages: Optional[int]) -> List[str]:
        """Obtém lista de todas as referências de eventos"""
        context = await self.browser.new_context(user_agent=self.user_agent)
        page = await context.new_page()
        
        references = []
        
        try:
            # Navega para primeira página
            print("🌐 Navegando para e-leiloes.pt...")
            await page.goto("https://www.e-leiloes.pt/", wait_until="networkidle")
            await asyncio.sleep(2)  # Espera mais tempo para JS carregar
            
            # Extrai total de páginas - MÚLTIPLOS SELETORES
            total_pages = 1  # Default se não encontrar paginador
            
            # Tenta diferentes seletores para o paginador
            paginator_selectors = [
                '.p-paginator-current',
                '.p-paginator .p-paginator-current',
                '[class*="paginator-current"]',
                'span.p-paginator-current',
                '.paginator-text'
            ]
            
            paginator = None
            for selector in paginator_selectors:
                paginator = await page.query_selector(selector)
                if paginator:
                    print(f"✅ Paginador encontrado com seletor: {selector}")
                    break
            
            if paginator:
                text = await paginator.text_content()
                print(f"📋 Texto do paginador: '{text}'")
                
                # Tenta extrair número total de eventos
                match = re.search(r'(\d+)', text.replace(' ', ''))
                if match:
                    # Assume que o último número é o total
                    numbers = re.findall(r'\d+', text.replace(' ', ''))
                    total_events = int(numbers[-1]) if numbers else 0
                    total_pages = (total_events + 11) // 12  # 12 por página
                    
                    if max_pages:
                        total_pages = min(total_pages, max_pages)
                    
                    print(f"📄 Total de eventos: {total_events}")
                    print(f"📄 Total de páginas calculadas: {total_pages}")
                else:
                    print("⚠️ Não consegui extrair números do paginador")
            else:
                print("⚠️ Paginador não encontrado com nenhum seletor")
                
                # Conta eventos na página atual
                cards = await page.query_selector_all('.p-evento')
                print(f"📦 Encontrados {len(cards)} cards na página atual")
            
            # Se não encontrou paginador, tenta descobrir dinamicamente
            if total_pages == 1:
                print("🔍 Modo descoberta: tentando encontrar todas as páginas...")
                
                page_num = 1
                while True:
                    self.current_page = page_num
                    
                    # Navega para página específica
                    url = f"https://www.e-leiloes.pt/?page={page_num}"
                    await page.goto(url, wait_until="networkidle")
                    await asyncio.sleep(1.5)
                    
                    # Extrai referências desta página
                    cards = await page.query_selector_all('.p-evento')
                    
                    if not cards:
                        print(f"📄 Página {page_num} vazia - fim da paginação")
                        break
                    
                    count_before = len(references)
                    
                    for card in cards:
                        ref_element = await card.query_selector('.pi-tag + span')
                        if ref_element:
                            ref = await ref_element.text_content()
                            ref_clean = ref.strip()
                            if ref_clean not in references:  # Evita duplicados
                                references.append(ref_clean)
                    
                    count_new = len(references) - count_before
                    print(f"📄 Página {page_num}: +{count_new} eventos (total: {len(references)})")
                    
                    if count_new == 0:
                        print(f"📄 Nenhum evento novo na página {page_num} - fim")
                        break
                    
                    if max_pages and page_num >= max_pages:
                        print(f"📄 Atingido limite de {max_pages} páginas")
                        break
                    
                    page_num += 1
                    
            else:
                # Percorre páginas conhecidas
                for page_num in range(1, total_pages + 1):
                    self.current_page = page_num
                    
                    # Navega para página específica
                    url = f"https://www.e-leiloes.pt/?page={page_num}"
                    await page.goto(url, wait_until="networkidle")
                    await asyncio.sleep(1.5)
                    
                    # Extrai referências desta página
                    cards = await page.query_selector_all('.p-evento')
                    
                    for card in cards:
                        ref_element = await card.query_selector('.pi-tag + span')
                        if ref_element:
                            ref = await ref_element.text_content()
                            references.append(ref.strip())
                    
                    print(f"📄 Página {page_num}/{total_pages}: {len(references)} eventos")
            
            return references
            
        finally:
            await page.close()
            await context.close()
    
    def get_status(self) -> ScraperStatus:
        """Retorna status atual"""
        return ScraperStatus(
            is_running=self.is_running,
            events_processed=self.events_processed,
            events_failed=self.events_failed,
            current_page=self.current_page,
            started_at=self.started_at,
            last_update=self.last_update
        )
