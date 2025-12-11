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

            return EventData(
                reference=reference,
                tipoEvento=tipo_evento,
                valores=valores_final,
                gps=gps,
                detalhes=detalhes,
                dataInicio=data_inicio,
                dataFim=data_fim,
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

            # Procura por spans com texto "Início:" e "Fim:"
            # As datas aparecem em formato DD/MM/YYYY HH:MM:SS
            spans = await page.query_selector_all('span.text-xs')

            for span in spans:
                text = await span.text_content()
                if not text:
                    continue

                text = text.strip()

                if text == 'Início:' or 'Início' in text:
                    # Procura pelo próximo span com classe font-semibold que contém a data
                    parent = await span.evaluate_handle('el => el.parentElement')
                    if parent:
                        date_span = await parent.query_selector('span.font-semibold')
                        if date_span:
                            value = await date_span.text_content()
                            if value:
                                try:
                                    # Parse data no formato DD/MM/YYYY HH:MM:SS
                                    data_inicio = datetime.strptime(value.strip(), '%d/%m/%Y %H:%M:%S')
                                except ValueError as e:
                                    print(f"⚠️ Erro ao parsear data de início '{value}': {e}")

                elif text == 'Fim:' or 'Fim' in text:
                    parent = await span.evaluate_handle('el => el.parentElement')
                    if parent:
                        date_span = await parent.query_selector('span.font-semibold')
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
        """Extrai coordenadas GPS do DOM da página"""
        try:
            latitude = None
            longitude = None

            # Procura por spans com "GPS Latitude:" e "GPS Longitude:"
            spans = await page.query_selector_all('.flex.w-full .font-semibold')

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
