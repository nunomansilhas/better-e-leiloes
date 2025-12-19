"""
Web Scraper para E-Leiloes.pt usando Playwright
"""

import sys
import asyncio

# Fix para Windows - asyncio subprocess com Playwright
# CRÍTICO: WindowsProactorEventLoopPolicy suporta subprocessos
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from typing import List, Optional, Callable, Awaitable
from datetime import datetime
import re
from playwright.async_api import async_playwright, Page, Browser
import os

from models import EventData, GPSCoordinates, EventDetails, ValoresLeilao, ScraperStatus, TIPO_EVENTO_MAP, TIPO_EVENTO_NAMES, TIPO_TO_WEBSITE


class EventScraper:
    """Scraper assíncrono para e-leiloes.pt"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        
        # Status tracking
        self.is_running = False
        self.stop_requested = False
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

    def stop(self):
        """Solicita parada do scraping"""
        print("🛑 Paragem do scraper solicitada...")
        self.stop_requested = True

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

            # Extrai localização UMA VEZ (GPS + Distrito/Concelho/Freguesia)
            gps, distrito, concelho, freguesia = await self._extract_localizacao(page)

            # Detalhes - extrai AMBOS os tipos para deteção automática
            detalhes_imovel = await self._extract_imovel_details(page, distrito, concelho, freguesia)
            detalhes_movel = await self._extract_movel_details(page, distrito, concelho, freguesia)

            # DETECÇÃO AUTOMÁTICA: Se tem matrícula, marca, modelo, etc → é móvel
            is_movel = (
                detalhes_movel.matricula is not None or
                "veículo" in (detalhes_movel.tipo or "").lower() or
                "veiculo" in (detalhes_movel.tipo or "").lower() or
                "ligeiro" in (detalhes_movel.tipo or "").lower() or
                "pesado" in (detalhes_movel.tipo or "").lower() or
                "motociclo" in (detalhes_movel.tipo or "").lower()
            )

            # Define o tipo correto
            if is_movel:
                tipo_evento = "movel"
                detalhes = detalhes_movel
                gps = None  # Móveis não têm GPS (só têm distrito/concelho/freguesia)
            else:
                tipo_evento = "imovel"
                detalhes = detalhes_imovel
                # GPS já foi extraído acima

            # Confirma/atualiza valores na página individual (podem ser mais precisos)
            valores_pagina = await self._extract_valores_from_page(page)

            # Merge valores (prioridade: página individual > listagem)
            valores_final = ValoresLeilao(
                valorBase=valores_pagina.valorBase or valores_listagem.valorBase,
                valorAbertura=valores_pagina.valorAbertura or valores_listagem.valorAbertura,
                valorMinimo=valores_pagina.valorMinimo or valores_listagem.valorMinimo,
                lanceAtual=valores_pagina.lanceAtual or valores_listagem.lanceAtual
            )

            # Extrai todas as secções (HTML completo) - com safeguard para None
            imagens = await self._extract_gallery(page)
            descricao = await self._extract_descricao(page)
            observacoes = await self._extract_observacoes(page)
            onuselimitacoes = await self._extract_onus_limitacoes(page)
            descricao_predial = await self._extract_descricao_predial(page)
            cerimonia = await self._extract_cerimonia(page)
            agente = await self._extract_agente(page)
            dados_processo = await self._extract_dados_processo(page)

            # SAFEGUARD: Garante que tudo é None se vazio
            try:
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
                    onuselimitacoes=onuselimitacoes,
                    descricaoPredial=descricao_predial,
                    cerimoniaEncerramento=cerimonia,
                    agenteExecucao=agente,
                    dadosProcesso=dados_processo,
                    scraped_at=datetime.utcnow()
                )
            except Exception as e:
                print(f"❌ Erro validação EventData para {reference}: {e}")
                raise
            
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

    async def _extract_localizacao(self, page: Page) -> tuple[GPSCoordinates, Optional[str], Optional[str], Optional[str]]:
        """
        Extrai dados da secção Localização: GPS, Distrito, Concelho, Freguesia.
        Funciona para móveis e imóveis.

        Returns:
            (gps, distrito, concelho, freguesia)
        """
        try:
            latitude = None
            longitude = None
            distrito = None
            concelho = None
            freguesia = None

            # Primeiro, encontra a div com título "Localização"
            localizacao_section = None
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and 'Localização' in text.strip():
                    # Pega o elemento pai mais próximo (bg-white shadow-1)
                    localizacao_section = await title_div.evaluate_handle(
                        'el => el.closest(".bg-white.shadow-1") || el.closest(".flex.flex-column.w-full")'
                    )
                    break

            if not localizacao_section:
                print("⚠️ Seção 'Localização' não encontrada")
                return GPSCoordinates(latitude=None, longitude=None), None, None, None

            # Procura por todos os containers .flex.flex-wrap.gap-1
            field_containers = await localizacao_section.query_selector_all('.flex.flex-wrap.gap-1')

            for container in field_containers:
                # Dentro de cada container, procura label e valor
                spans = await container.query_selector_all('span')
                if len(spans) >= 2:
                    label_span = spans[0]
                    value_span = spans[1]

                    label = await label_span.text_content()
                    value = await value_span.text_content()

                    if not label or not value:
                        continue

                    label = label.strip()
                    value = value.strip()

                    # GPS
                    if 'GPS Latitude' in label:
                        try:
                            latitude = float(value)
                            print(f"  ✓ GPS Lat: {latitude}")
                        except ValueError:
                            pass

                    elif 'GPS Longitude' in label:
                        try:
                            longitude = float(value)
                            print(f"  ✓ GPS Lon: {longitude}")
                        except ValueError:
                            pass

                    # Distrito / Concelho / Freguesia
                    elif 'Distrito' in label:
                        distrito = value
                        print(f"  ✓ Distrito: {distrito}")

                    elif 'Concelho' in label:
                        concelho = value
                        print(f"  ✓ Concelho: {concelho}")

                    elif 'Freguesia' in label:
                        freguesia = value
                        print(f"  ✓ Freguesia: {freguesia}")

            gps = GPSCoordinates(latitude=latitude, longitude=longitude)
            return gps, distrito, concelho, freguesia

        except Exception as e:
            print(f"⚠️ Erro ao extrair Localização: {e}")
            import traceback
            traceback.print_exc()
            return GPSCoordinates(latitude=None, longitude=None), None, None, None

    async def _extract_gps(self, page: Page) -> GPSCoordinates:
        """Extrai coordenadas GPS (wrapper para compatibilidade)"""
        gps, _, _, _ = await self._extract_localizacao(page)
        return gps

    async def _extract_gallery(self, page: Page) -> List[str]:
        """Extrai TODAS as imagens iterando pelos IDs pv_id_X_item_Y"""
        try:
            import re

            # Aguarda a galeria carregar
            try:
                await page.wait_for_selector('.p-galleria', timeout=3000)
            except:
                print("⚠️ Galeria não encontrada")
                return []

            # ===== NOVO: Aguarda pelo contador de imagens e calcula tempo de espera =====
            try:
                # Tenta encontrar o contador de imagens (ex: "1/7")
                footer_selector = '.custom-galleria-footer, .p-galleria-footer, .better-image-badge'
                await page.wait_for_selector(footer_selector, timeout=2000)

                footer = await page.query_selector(footer_selector)
                if footer:
                    footer_text = await footer.inner_text()
                    print(f"📊 Contador de imagens: {footer_text}")

                    # Parse "X/Y" ou "📷 Y" para obter total de imagens
                    match = re.search(r'(\d+)/(\d+)|📷\s*(\d+)', footer_text)
                    if match:
                        total_images = int(match.group(2) if match.group(2) else match.group(3))
                        print(f"🖼️ Total de imagens detectadas: {total_images}")

                        # Calcula tempo de espera: 2.5s por imagem + 1s buffer
                        wait_time = (total_images * 2.5) + 1
                        print(f"⏳ Aguardando {wait_time:.1f}s para todas as imagens carregarem...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Fallback: se não conseguiu parsear, espera 3s
                        print("⚠️ Não conseguiu parsear contador, aguardando 3s...")
                        await asyncio.sleep(3)
                else:
                    # Se não encontrou footer, espera tempo padrão
                    print("⚠️ Footer não encontrado, aguardando 2s...")
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️ Erro ao detectar contador: {e}, aguardando 2s...")
                await asyncio.sleep(2)

            images = []

            # Método 1: Itera pelos items da galeria (pv_id_X_item_0, item_1, item_2...)
            try:
                # Encontra o primeiro item para obter o prefixo do ID
                first_item = await page.query_selector('.p-galleria-item[id]')
                if first_item:
                    first_id = await first_item.get_attribute('id')
                    if first_id:
                        # Extrai prefixo (ex: "pv_id_7" de "pv_id_7_item_0")
                        id_match = re.match(r'(pv_id_\d+)_item_\d+', first_id)
                        if id_match:
                            id_prefix = id_match.group(1)
                            print(f"🔍 Galeria ID: {id_prefix}")

                            # Itera de item_0 até não encontrar mais
                            item_num = 0
                            consecutive_misses = 0
                            max_misses = 3  # Para se houver gaps

                            while consecutive_misses < max_misses and item_num < 100:
                                item_id = f"{id_prefix}_item_{item_num}"
                                item = await page.query_selector(f'#{item_id} .p-evento-image')

                                if item:
                                    style = await item.get_attribute('style')
                                    if style and 'background-image: url(' in style:
                                        match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                                        if match:
                                            url = match.group(1).replace('&quot;', '')
                                            if url and url not in images:
                                                images.append(url)
                                                print(f"  ✓ Imagem {item_num}: {url.split('/')[-1]}")
                                    consecutive_misses = 0
                                else:
                                    consecutive_misses += 1

                                item_num += 1

                            print(f"📷 Total: {len(images)} imagens extraídas")
            except Exception as e:
                print(f"⚠️ Erro ao iterar items: {e}")

            # Fallback: Se não encontrou nada, tenta buscar todos os items visíveis
            if not images:
                try:
                    gallery_items = await page.query_selector_all('.p-galleria-item .p-evento-image')
                    for item in gallery_items:
                        style = await item.get_attribute('style')
                        if style and 'background-image: url(' in style:
                            match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                            if match:
                                url = match.group(1).replace('&quot;', '')
                                if url and url not in images:
                                    images.append(url)
                    print(f"📷 Fallback: {len(images)} imagens")
                except Exception as e:
                    print(f"⚠️ Erro no fallback: {e}")

            return images

        except Exception as e:
            print(f"⚠️ Erro ao extrair galeria: {e}")
            return []

    async def _extract_section_html(self, page: Page, section_title: str) -> Optional[str]:
        """
        Método genérico para extrair HTML completo de uma secção.

        Args:
            page: Página do Playwright
            section_title: Título da secção (ex: "Descrição", "Observações", etc.)

        Returns:
            HTML completo da secção ou None se não encontrada ou vazia
        """
        try:
            title_divs = await page.query_selector_all('.font-semibold.text-xl')

            for title_div in title_divs:
                text = await title_div.text_content()
                if text and section_title.lower() in text.strip().lower():
                    # Pega o elemento pai (a seção completa)
                    section = await title_div.evaluate_handle(
                        'el => el.closest(".flex.flex-column.w-full")'
                    )
                    if section:
                        # Retorna o HTML completo da secção
                        html = await section.evaluate('el => el.innerHTML')
                        # SAFEGUARD: Retorna None se vazio ou só whitespace
                        if html and html.strip():
                            return html.strip()
                        return None

            return None

        except Exception as e:
            print(f"⚠️ Erro ao extrair secção '{section_title}': {e}")
            return None

    async def _extract_descricao(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Descrição"""
        return await self._extract_section_html(page, "Descrição")

    async def _extract_observacoes(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Observações"""
        return await self._extract_section_html(page, "Observações")

    async def _extract_onus_limitacoes(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Ónus e Limitações"""
        return await self._extract_section_html(page, "Ónus")

    async def _extract_descricao_predial(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Descrição Predial"""
        return await self._extract_section_html(page, "Descrição Predial")

    async def _extract_cerimonia(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Cerimónia de Encerramento"""
        return await self._extract_section_html(page, "Cerimónia")

    async def _extract_agente(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Agente de Execução"""
        return await self._extract_section_html(page, "Agente")

    async def _extract_dados_processo(self, page: Page) -> Optional[str]:
        """Extrai HTML completo da secção Dados do Processo"""
        return await self._extract_section_html(page, "Dados do Processo")

    async def _extract_descricao_predial_OLD(self, page: Page):
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
    
    async def _extract_imovel_details(
        self,
        page: Page,
        distrito: Optional[str] = None,
        concelho: Optional[str] = None,
        freguesia: Optional[str] = None
    ) -> EventDetails:
        """Extrai detalhes COMPLETOS do IMÓVEL via DOM"""

        async def extract_detail(label: str) -> Optional[str]:
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
                            return value.strip() if value else None

                return None
            except:
                return None

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

        # Extrai campos básicos
        tipo = await extract_detail('Tipo:')
        subtipo = await extract_detail('Subtipo:')
        tipologia = await extract_detail('Tipologia:')

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
    
    async def _extract_movel_details(
        self,
        page: Page,
        distrito: Optional[str] = None,
        concelho: Optional[str] = None,
        freguesia: Optional[str] = None
    ) -> EventDetails:
        """Extrai detalhes do MÓVEL (automóvel) via DOM"""

        async def extract_detail(label: str) -> Optional[str]:
            """Extrai valor de um campo específico"""
            try:
                spans = await page.query_selector_all('.flex.w-full .font-semibold')

                for span in spans:
                    text = await span.text_content()
                    if text and text.strip() == label:
                        next_el = await span.evaluate_handle('el => el.nextElementSibling')
                        if next_el:
                            value = await next_el.text_content()
                            return value.strip() if value else None

                return None
            except:
                return None

        # Extrai campos básicos
        tipo = await extract_detail('Tipo:')
        subtipo = await extract_detail('Subtipo:')
        matricula = await extract_detail('Matrícula:')

        return EventDetails(
            tipo=tipo,
            subtipo=subtipo,
            matricula=matricula,
            distrito=distrito,
            concelho=concelho,
            freguesia=freguesia
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
        self.stop_requested = False
        self.started_at = datetime.utcnow()
        self.events_processed = 0
        self.events_failed = 0

        all_events = []

        await self.init_browser()

        try:
            # 1. SCRAPE IMOVEIS (tipo=1)
            if not self.stop_requested:
                print("🏠 Iniciando scraping de IMÓVEIS...")
                imoveis = await self._scrape_by_type(tipo=1, max_pages=max_pages)
                all_events.extend(imoveis)
                print(f"✅ Imóveis recolhidos: {len(imoveis)}")

            # 2. SCRAPE MOVEIS (tipo=2)
            if not self.stop_requested:
                print("🚗 Iniciando scraping de MÓVEIS...")
                moveis = await self._scrape_by_type(tipo=2, max_pages=max_pages)
                all_events.extend(moveis)
                print(f"✅ Móveis recolhidos: {len(moveis)}")

            if self.stop_requested:
                print(f"⚠️ Scraping interrompido pelo utilizador. Total processado: {len(all_events)}")
            else:
                print(f"🎉 Total de eventos: {len(all_events)}")

            return all_events

        finally:
            self.is_running = False
            self.stop_requested = False
    
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
            # Verifica se foi solicitada paragem
            if self.stop_requested:
                print(f"🛑 Scraping interrompido na página {self.current_page}")
                break

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
                    self.last_update = datetime.utcnow()
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
                # Verifica se foi solicitada paragem
                if self.stop_requested:
                    print(f"🛑 Scraping da listagem interrompido")
                    break

                self.current_page = page_num + 1  # Para display (página 1, 2, 3...)

                # Navega para página de listagem com offset correto
                # Converte tipo interno para tipo do website
                website_tipo = TIPO_TO_WEBSITE.get(tipo, tipo)
                url = f"https://www.e-leiloes.pt/eventos?layout=grid&first={first_offset}&sort=dataFimAsc&tipo={website_tipo}"
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

    # ============== MULTI-STAGE SCRAPING ==============
    # Stage 1: Scrape apenas IDs
    # Stage 2: Scrape detalhes por ID
    # Stage 3: Scrape imagens por ID

    async def scrape_ids_only(self, tipo: Optional[int] = None, max_pages: Optional[int] = None) -> List[dict]:
        """
        STAGE 1: Scrape apenas referências e valores básicos da listagem (rápido).

        Args:
            tipo: 1-6 para tipo específico, None=todos os tipos
                  1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas
            max_pages: Máximo de páginas por tipo

        Returns:
            Lista de dicts: [{reference, tipo_evento, valores}, ...]
        """
        await self.init_browser()

        all_ids = []

        try:
            if tipo is None:
                # Scrape TODOS os 6 tipos
                for tipo_code, tipo_str in TIPO_EVENTO_MAP.items():
                    tipo_nome = TIPO_EVENTO_NAMES[tipo_code]
                    print(f"🆔 Stage 1: Scraping IDs de {tipo_nome} (tipo={tipo_code})...")
                    ids = await self._extract_from_listing(tipo=tipo_code, max_pages=max_pages)
                    for item in ids:
                        item['tipo_evento'] = tipo_str
                        item['tipo'] = tipo_str  # Alias para compatibilidade
                    all_ids.extend(ids)
                    print(f"  ✓ {len(ids)} {tipo_nome} encontrados")
            else:
                # Scrape tipo específico
                if tipo not in TIPO_EVENTO_MAP:
                    raise ValueError(f"Tipo inválido: {tipo}. Use 1-6.")
                tipo_str = TIPO_EVENTO_MAP[tipo]
                tipo_nome = TIPO_EVENTO_NAMES[tipo]
                print(f"🆔 Stage 1: Scraping IDs de {tipo_nome} (tipo={tipo})...")
                ids = await self._extract_from_listing(tipo=tipo, max_pages=max_pages)
                for item in ids:
                    item['tipo_evento'] = tipo_str
                    item['tipo'] = tipo_str
                all_ids.extend(ids)

            print(f"✅ Stage 1 completo: {len(all_ids)} IDs recolhidos")
            return all_ids

        except Exception as e:
            print(f"❌ Erro no Stage 1: {e}")
            raise

    async def scrape_details_by_ids(
        self,
        references: List[str],
        on_event_scraped: Optional[Callable[[EventData], Awaitable[None]]] = None
    ) -> List[EventData]:
        """
        STAGE 2: Scrape detalhes completos (SEM imagens) para lista de referências.

        Args:
            references: Lista de referências (ex: ["LO-2024-001", "NP-2024-002"])
            on_event_scraped: Callback async chamado para cada evento scraped (inserção em tempo real)

        Returns:
            Lista de EventData (sem imagens)
        """
        await self.init_browser()

        events = []
        failed = []

        print(f"📋 Stage 2: Scraping detalhes de {len(references)} eventos...")

        # Processa em batches paralelos
        for i in range(0, len(references), self.concurrent):
            batch = references[i:i + self.concurrent]

            tasks = []
            for ref in batch:
                # Determina tipo baseado no prefixo
                tipo_evento = "imovel" if ref.startswith("LO") or ref.startswith("NP") else "imovel"

                # Cria preview fake (valores virão da página)
                preview = {
                    'reference': ref,
                    'valores': ValoresLeilao()
                }

                tasks.append(self._scrape_event_details_no_images(preview, tipo_evento))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                if isinstance(result, EventData):
                    events.append(result)
                    print(f"  ✓ {batch[idx]}")

                    # 🔥 INSERÇÃO EM TEMPO REAL via callback
                    if on_event_scraped:
                        try:
                            await on_event_scraped(result)
                        except Exception as e:
                            print(f"  ⚠️ Erro ao salvar {batch[idx]}: {e}")
                else:
                    failed.append(batch[idx])
                    print(f"  ✗ {batch[idx]}: {str(result)[:50]}")

            await asyncio.sleep(self.delay)

        print(f"✅ Stage 2 completo: {len(events)} eventos / {len(failed)} falhas")
        return events

    async def _scrape_event_details_no_images(self, preview: dict, tipo_evento: str) -> EventData:
        """
        Scrape detalhes de um evento SEM extrair imagens (mais rápido).
        Similar a _scrape_event_details mas pula a galeria.
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
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await asyncio.sleep(1.5)

            # Extrai datas
            data_inicio, data_fim = await self._extract_dates(page)

            # Extrai localização UMA VEZ (GPS + Distrito/Concelho/Freguesia)
            gps, distrito, concelho, freguesia = await self._extract_localizacao(page)

            # Detalhes - extrai AMBOS os tipos para detetar automaticamente
            detalhes_imovel = await self._extract_imovel_details(page, distrito, concelho, freguesia)
            detalhes_movel = await self._extract_movel_details(page, distrito, concelho, freguesia)

            # DETECÇÃO AUTOMÁTICA: Se tem matrícula, marca, modelo, etc → é móvel
            # Se tem tipologia, área, distrito, etc → é imóvel
            is_movel = (
                detalhes_movel.matricula is not None or
                "veículo" in (detalhes_movel.tipo or "").lower() or
                "veiculo" in (detalhes_movel.tipo or "").lower() or
                "ligeiro" in (detalhes_movel.tipo or "").lower() or
                "pesado" in (detalhes_movel.tipo or "").lower() or
                "motociclo" in (detalhes_movel.tipo or "").lower()
            )

            # Define o tipo correto
            if is_movel:
                tipo_evento = "movel"
                detalhes = detalhes_movel
                gps = None  # Móveis não têm GPS (só têm distrito/concelho/freguesia)
            else:
                tipo_evento = "imovel"
                detalhes = detalhes_imovel
                # GPS já foi extraído acima

            # Valores
            valores_pagina = await self._extract_valores_from_page(page)
            valores_final = ValoresLeilao(
                valorBase=valores_pagina.valorBase or valores_listagem.valorBase,
                valorAbertura=valores_pagina.valorAbertura or valores_listagem.valorAbertura,
                valorMinimo=valores_pagina.valorMinimo or valores_listagem.valorMinimo,
                lanceAtual=valores_pagina.lanceAtual or valores_listagem.lanceAtual
            )

            # Textos e informações (SEM IMAGENS) - com safeguard para None
            descricao = await self._extract_descricao(page)
            observacoes = await self._extract_observacoes(page)
            onuselimitacoes = await self._extract_onus_limitacoes(page)
            descricao_predial = await self._extract_descricao_predial(page)
            cerimonia = await self._extract_cerimonia(page)
            agente = await self._extract_agente(page)
            dados_processo = await self._extract_dados_processo(page)

            # SAFEGUARD: Garante que tudo é None se vazio
            try:
                return EventData(
                    reference=reference,
                    tipoEvento=tipo_evento,
                    valores=valores_final,
                    gps=gps,
                    detalhes=detalhes,
                    dataInicio=data_inicio,
                    dataFim=data_fim,
                    imagens=[],  # VAZIO - Stage 3 preenche isto
                    descricao=descricao,
                    observacoes=observacoes,
                    onuselimitacoes=onuselimitacoes,
                    descricaoPredial=descricao_predial,
                    cerimoniaEncerramento=cerimonia,
                    agenteExecucao=agente,
                    dadosProcesso=dados_processo,
                    scraped_at=datetime.utcnow()
                )
            except Exception as e:
                print(f"❌ Erro validação EventData para {reference}: {e}")
                raise

        finally:
            await page.close()
            await context.close()

    async def scrape_images_by_ids(
        self,
        references: List[str],
        on_images_scraped: Optional[Callable[[str, List[str]], Awaitable[None]]] = None
    ) -> dict:
        """
        STAGE 3: Scrape apenas imagens para lista de referências.

        Args:
            references: Lista de referências
            on_images_scraped: Callback async chamado para cada ref com imagens (inserção em tempo real)

        Returns:
            Dict: {reference: [image_urls], ...}
        """
        await self.init_browser()

        images_map = {}
        failed = []

        print(f"🖼️ Stage 3: Scraping imagens de {len(references)} eventos...")

        # Processa em batches paralelos
        for i in range(0, len(references), self.concurrent):
            batch = references[i:i + self.concurrent]

            tasks = [self._scrape_images_only(ref) for ref in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(results):
                ref = batch[idx]
                if isinstance(result, list):
                    images_map[ref] = result
                    print(f"  ✓ {ref}: {len(result)} imagens")

                    # 🔥 INSERÇÃO EM TEMPO REAL via callback
                    if on_images_scraped:
                        try:
                            await on_images_scraped(ref, result)
                        except Exception as e:
                            print(f"  ⚠️ Erro ao atualizar imagens {ref}: {e}")
                else:
                    images_map[ref] = []
                    failed.append(ref)
                    print(f"  ✗ {ref}: {str(result)[:50]}")

            await asyncio.sleep(self.delay)

        print(f"✅ Stage 3 completo: {len(images_map)} eventos / {len(failed)} falhas")
        return images_map

    async def scrape_volatile_by_ids(
        self,
        references: List[str],
    ) -> List[dict]:
        """
        LIGHTWEIGHT SCRAPER: Only extracts volatile data (price + end time).
        Used by Pipeline X variants for fast price/time updates.

        Args:
            references: Lista de referências (ex: ["LO-2024-001", "NP-2024-002"])

        Returns:
            Lista de dicts: [{reference, lanceAtual, dataFim}, ...]
        """
        await self.init_browser()

        results = []
        failed = []

        print(f"⚡ Volatile scrape: {len(references)} events (price + time only)...")

        # Process in batches
        for i in range(0, len(references), self.concurrent):
            batch = references[i:i + self.concurrent]

            tasks = [self._scrape_volatile_only(ref) for ref in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(batch_results):
                if isinstance(result, dict):
                    results.append(result)
                    # Show extracted values
                    price = result.get('lanceAtual')
                    end_time = result.get('dataFim')
                    price_str = f"{price}€" if price is not None else "N/A"
                    time_str = end_time.strftime('%d/%m/%Y %H:%M:%S') if end_time else "N/A"
                    print(f"  ✓ {result['reference']}: PMA={price_str} | Fim={time_str}")
                else:
                    failed.append(batch[idx])
                    print(f"  ✗ {batch[idx]}: {str(result)[:50]}")

            await asyncio.sleep(self.delay * 0.5)  # Faster delay for lightweight scrape

        print(f"⚡ Volatile scrape complete: {len(results)} OK / {len(failed)} failed")
        return results

    async def _scrape_volatile_only(self, reference: str) -> dict:
        """
        Scrape ONLY volatile data from an event page (price + end time).
        Much faster than full scrape - skips GPS, location, descriptions, etc.
        """
        url = f"https://www.e-leiloes.pt/evento/{reference}"

        context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()

        try:
            # Use domcontentloaded instead of networkidle for faster load
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(0.5)  # Minimal wait

            # Extract only dataFim
            data_fim = None
            try:
                divs = await page.query_selector_all('div.flex.justify-content-between')
                for div in divs:
                    text = await div.text_content()
                    if text and 'Fim:' in text:
                        date_span = await div.query_selector('span.font-semibold')
                        if date_span:
                            value = await date_span.text_content()
                            if value:
                                data_fim = datetime.strptime(value.strip(), '%d/%m/%Y %H:%M:%S')
                        break
            except Exception as e:
                print(f"  ⚠️ Error extracting dataFim for {reference}: {e}")

            # Extract only lanceAtual (P. Mais Alta / Lance Atual) via DOM
            lance_atual = None
            try:
                # Look for the price label spans - try multiple approaches
                price_labels = ['Lance Atual:', 'P. Mais Alta:']

                # Approach 1: Look for label span with specific classes
                spans = await page.query_selector_all('span.text-xl.text-primary-800.font-semibold')
                print(f"  🔍 {reference}: Found {len(spans)} spans with text-xl.text-primary-800.font-semibold")

                for span in spans:
                    text = await span.text_content()
                    print(f"    → Span text: '{text}'")
                    if text and any(label in text for label in price_labels):
                        # Found the label, now get the sibling with the value
                        parent = await span.evaluate_handle('el => el.parentElement')
                        if parent:
                            value_span = await parent.query_selector('span.text-right')
                            if value_span:
                                value_text = await value_span.text_content()
                                print(f"    → Value span text: '{value_text}'")
                                if value_text:
                                    # Parse "83 299,99 €" or "92 541,54 €"
                                    value_str = value_text.strip().replace('€', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
                                    lance_atual = float(value_str)
                                    print(f"  📊 {reference}: Found price = {lance_atual}€ (label: {text.strip()})")
                                    break
                            else:
                                print(f"    → No span.text-right found in parent")
                        else:
                            print(f"    → Could not get parent element")

                # Approach 2: Try alternative - look for any element containing € followed by numbers
                if lance_atual is None:
                    print(f"  🔄 {reference}: Trying alternative approach...")
                    # Get page HTML and search for price pattern
                    html = await page.content()
                    import re
                    # Pattern for Portuguese price format: "123 456,78 €" or "123 456€"
                    price_match = re.search(r'(?:Lance Atual:|P\. Mais Alta:)\s*</span>.*?>([\d\s.,]+)\s*€', html, re.DOTALL)
                    if price_match:
                        value_str = price_match.group(1).strip().replace(' ', '').replace('.', '').replace(',', '.')
                        lance_atual = float(value_str)
                        print(f"  📊 {reference}: Found price via regex = {lance_atual}€")

                if lance_atual is None:
                    print(f"  ⚠️ {reference}: Could not find price via DOM or regex")
            except Exception as e:
                print(f"  ⚠️ Error extracting lanceAtual for {reference}: {e}")

            return {
                'reference': reference,
                'lanceAtual': lance_atual,
                'dataFim': data_fim
            }

        except Exception as e:
            raise Exception(f"Volatile scrape failed for {reference}: {str(e)}")

        finally:
            await page.close()
            await context.close()

    async def _scrape_images_only(self, reference: str) -> List[str]:
        """Scrape apenas as imagens de um evento usando interceptação de requests"""
        url = f"https://www.e-leiloes.pt/evento/{reference}"

        # Lista para coletar URLs de imagens interceptadas
        intercepted_images = []
        verba_folder = None  # 🔥 Vamos determinar o folder correto

        context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()

        # 🔥 INTERCEPTA requests de imagens da API
        async def handle_route(route):
            nonlocal verba_folder
            request = route.request
            img_url = request.url

            # Intercepta chamadas para Verbas_Fotos/verba_X/
            if 'Verbas_Fotos/verba_' in img_url and img_url.endswith(('.jpg', '.jpeg', '.png', '.webp')):

                # Extrai o folder verba (ex: "verba_121561")
                match = re.search(r'(verba_\d+)', img_url)
                if match:
                    folder = match.group(1)

                    # 🎯 Se ainda não determinamos o folder, usa o primeiro
                    if verba_folder is None:
                        verba_folder = folder
                        print(f"    🎯 Folder detectado: {verba_folder}")

                    # ✅ SÓ adiciona imagens do folder CORRETO
                    if folder == verba_folder:
                        if img_url not in intercepted_images:
                            intercepted_images.append(img_url)
                            print(f"    📸 {len(intercepted_images)}: {img_url.split('/')[-1]}")
                    else:
                        # ❌ Ignora imagens de outros folders
                        print(f"    ⏭️  Ignorado (folder diferente): {folder}")

            # Continua com o request normal
            await route.continue_()

        # Ativa a interceptação
        await page.route("**/*", handle_route)

        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)

            # ===== AGUARDA dinamicamente baseado no contador de imagens =====
            try:
                footer_selector = '.custom-galleria-footer, .p-galleria-footer, .better-image-badge'
                await page.wait_for_selector(footer_selector, timeout=2000)

                footer = await page.query_selector(footer_selector)
                if footer:
                    footer_text = await footer.inner_text()
                    print(f"    📊 Contador: {footer_text}")

                    # Parse "X/Y" ou "📷 Y"
                    match = re.search(r'(\d+)/(\d+)|📷\s*(\d+)', footer_text)
                    if match:
                        total_images = int(match.group(2) if match.group(2) else match.group(3))
                        wait_time = (total_images * 2.5) + 1
                        print(f"    ⏳ Aguardando {wait_time:.1f}s para {total_images} imagens...")
                        await asyncio.sleep(wait_time)
                    else:
                        await asyncio.sleep(3)
                else:
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"    ⚠️ Erro ao detectar contador: {e}")
                await asyncio.sleep(2)

            # Se interceptamos imagens, retorna essas
            if intercepted_images:
                print(f"    ✅ {len(intercepted_images)} imagens de {verba_folder}")
                return intercepted_images

            # Fallback: usa método DOM (caso a interceptação falhe)
            print(f"    ⚠️ Nenhuma imagem interceptada, tentando fallback DOM...")
            images = await self._extract_gallery(page)
            return images

        finally:
            await page.close()
            await context.close()
