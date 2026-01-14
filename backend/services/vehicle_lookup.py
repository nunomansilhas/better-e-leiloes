"""
Vehicle Lookup Service
Provides license plate decoding and market price lookup for Portuguese vehicles.

Features:
- Decode plate format to estimate year
- Lookup vehicle info from InfoMatricula.pt (free)
- Search Standvirtual for market prices
"""

import re
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PlateInfo:
    """Decoded Portuguese license plate information"""
    plate: str
    format: str
    era: str
    year_min: int
    year_max: int
    notes: str


@dataclass
class VehicleMarketData:
    """Market data for a vehicle"""
    marca: str
    modelo: str
    ano: int
    num_resultados: int
    preco_min: float
    preco_max: float
    preco_medio: float
    preco_mediana: float
    fonte: str
    data_consulta: str
    listings: List[Dict[str, Any]]


def decode_portuguese_plate(plate: str) -> PlateInfo:
    """
    Decode a Portuguese license plate to estimate vehicle year.

    Portuguese plate formats:
    - Pre-1992: XX-00-00 (letters-numbers-numbers)
    - 1992-2005: 00-00-XX (numbers-numbers-letters)
    - 2005-2020: 00-XX-00 (numbers-letters-numbers)
    - 2020+: XX-00-XX (letters-numbers-letters)
    """
    clean = plate.replace("-", "").replace(" ", "").upper()

    # Pattern: XX-00-XX (2020+)
    if re.match(r'^[A-Z]{2}\d{2}[A-Z]{2}$', clean):
        return PlateInfo(
            plate=plate,
            format="XX-00-XX",
            era="2020+",
            year_min=2020,
            year_max=datetime.now().year,
            notes="Novo formato introduzido em Março 2020"
        )

    # Pattern: 00-XX-00 (2005-2020)
    if re.match(r'^\d{2}[A-Z]{2}\d{2}$', clean):
        return PlateInfo(
            plate=plate,
            format="00-XX-00",
            era="2005-2020",
            year_min=2005,
            year_max=2020,
            notes="Formato de 2005"
        )

    # Pattern: 00-00-XX (1992-2005)
    if re.match(r'^\d{4}[A-Z]{2}$', clean):
        return PlateInfo(
            plate=plate,
            format="00-00-XX",
            era="1992-2005",
            year_min=1992,
            year_max=2005,
            notes="Formato de 1992"
        )

    # Pattern: XX-00-00 (pre-1992)
    if re.match(r'^[A-Z]{2}\d{4}$', clean):
        return PlateInfo(
            plate=plate,
            format="XX-00-00",
            era="pre-1992",
            year_min=1970,
            year_max=1992,
            notes="Formato antigo, anterior a 1992"
        )

    # Unknown format
    return PlateInfo(
        plate=plate,
        format="unknown",
        era="unknown",
        year_min=1990,
        year_max=datetime.now().year,
        notes="Formato de matrícula não reconhecido"
    )


def extract_vehicle_from_title(title: str) -> Dict[str, Optional[str]]:
    """
    Extract vehicle make and model from auction title.

    Examples:
    - "BMW 320d de 2015" -> {"marca": "BMW", "modelo": "320d", "ano": 2015}
    - "VOLKSWAGEN GOLF 1.6 TDI" -> {"marca": "VOLKSWAGEN", "modelo": "GOLF 1.6 TDI", "ano": None}
    """
    # Common car brands in Portugal (longer names first to match correctly)
    brands = [
        "MERCEDES-BENZ", "ALFA ROMEO", "LAND ROVER",  # Multi-word brands first
        "ABARTH", "AUDI", "BMW", "CHEVROLET", "CHRYSLER", "CITROEN",
        "DACIA", "FIAT", "FORD", "HONDA", "HYUNDAI", "JAGUAR", "JEEP", "KIA",
        "LEXUS", "MAZDA", "MERCEDES", "MINI", "MITSUBISHI", "NISSAN", "OPEL",
        "PEUGEOT", "PORSCHE", "RENAULT", "SEAT", "SKODA", "SMART", "SUZUKI",
        "TESLA", "TOYOTA", "VOLKSWAGEN", "VOLVO"
    ]

    title_upper = title.upper()

    # Find brand (check longer names first)
    found_brand = None
    for brand in brands:
        if brand in title_upper:
            found_brand = brand
            break

    # Extract year (look for 4-digit numbers between 1990-2030)
    year_match = re.search(r'\b(19[9]\d|20[0-3]\d)\b', title)
    year = int(year_match.group(1)) if year_match else None

    # Extract model (text after brand, before year or "de")
    model = None
    if found_brand:
        brand_idx = title_upper.index(found_brand)
        after_brand = title[brand_idx + len(found_brand):].strip()
        # Remove common words
        after_brand = re.sub(r'\b(de|do|da|ano|com|km)\b', '', after_brand, flags=re.IGNORECASE)
        after_brand = re.sub(r'\b\d{4}\b', '', after_brand)  # Remove year
        model = after_brand.strip().strip('-').strip()
        if len(model) < 2:
            model = None

    return {
        "marca": found_brand,
        "modelo": model,
        "ano": year
    }


async def search_standvirtual(marca: str, modelo: str = None, ano: int = None, debug: bool = False) -> Optional[VehicleMarketData]:
    """
    Search Standvirtual for similar vehicles.

    Note: This uses Playwright and should be run locally, not on cloud servers
    which typically get blocked.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install")
        return None

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Build search URL
            marca_slug = marca.lower().replace(" ", "-").replace("_", "-")
            url = f"https://www.standvirtual.com/carros/{marca_slug}"

            if modelo:
                # Clean modelo slug
                modelo_slug = modelo.lower()
                modelo_slug = re.sub(r'[^\w\s-]', '', modelo_slug)  # Remove special chars except -
                modelo_slug = modelo_slug.replace(" ", "-").replace(".", "-")
                # Take only the first part for common model names
                modelo_first = modelo_slug.split('-')[0] if '-' in modelo_slug else modelo_slug
                url = f"{url}?search[filter_enum_model]={modelo_first}"

            # Add year filter
            if ano:
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}search[filter_float_year:from]={ano-2}&search[filter_float_year:to]={ano+2}"

            if debug:
                print(f"  [DEBUG] URL: {url}")

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            # Accept cookies
            await _accept_cookies(page)
            await page.wait_for_timeout(1000)

            # Get page content for debugging
            content = await page.content()

            if debug:
                with open('debug_standvirtual.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                print("  [DEBUG] HTML guardado em debug_standvirtual.html")

            # Try multiple listing selectors (site structure changes frequently)
            listing_selectors = [
                'article[data-testid="listing-ad"]',
                'article[data-id]',
                '[data-testid="search-results"] article',
                '.ooa-1t80gpj',  # StandVirtual class pattern
                'main article',
                '.listing-item',
                '[class*="offer"]',
            ]

            listings = []
            for selector in listing_selectors:
                listings = await page.query_selector_all(selector)
                if listings:
                    if debug:
                        print(f"  [DEBUG] Encontrados {len(listings)} listings com: {selector}")
                    break

            if not listings:
                # Try to find any article with price
                all_articles = await page.query_selector_all('article')
                if debug:
                    print(f"  [DEBUG] Total de articles na página: {len(all_articles)}")

                # Also check for "no results" message
                no_results_indicators = [
                    'não encontrámos',
                    'sem resultados',
                    'nenhum resultado',
                    '0 anúncios',
                ]
                content_lower = content.lower()
                for indicator in no_results_indicators:
                    if indicator in content_lower:
                        if debug:
                            print(f"  [DEBUG] Página indica: {indicator}")
                        return None

            for listing in listings[:20]:  # Max 20 results
                try:
                    # Try multiple price selectors
                    price_selectors = [
                        '[data-testid="ad-price"]',
                        '.ooa-1bmnxg7',  # Price class
                        '[class*="price"]',
                        'span:has-text("EUR")',
                        'h3',
                    ]

                    price = 0
                    for ps in price_selectors:
                        price_el = await listing.query_selector(ps)
                        if price_el:
                            price_text = await price_el.inner_text()
                            # Extract number from price (remove EUR, spaces, etc)
                            price_match = re.search(r'[\d\s]+', price_text.replace(' ', ''))
                            if price_match:
                                price_clean = price_match.group().replace(' ', '')
                                if price_clean.isdigit():
                                    price = int(price_clean)
                                    if price > 0:
                                        break

                    # Try multiple title selectors
                    title_selectors = [
                        'h2',
                        'h1',
                        '[data-testid="ad-title"]',
                        'a[href*="/anuncio/"]',
                        '[class*="title"]',
                    ]

                    title = ""
                    for ts in title_selectors:
                        title_el = await listing.query_selector(ts)
                        if title_el:
                            title = await title_el.inner_text()
                            if title and len(title) > 3:
                                break

                    # Get params (year, km, fuel)
                    params_text = ""
                    params_selectors = [
                        '[data-testid="ad-parameters"]',
                        'ul li',
                        '[class*="parameter"]',
                    ]
                    for psel in params_selectors:
                        params_el = await listing.query_selector(psel)
                        if params_el:
                            params_text = await params_el.inner_text()
                            break

                    if price > 500:  # Minimum reasonable price
                        results.append({
                            "titulo": title.strip()[:100],
                            "preco": price,
                            "params": params_text.strip()[:100] if params_text else ""
                        })
                        if debug:
                            print(f"  [DEBUG] Anúncio: {title[:40]}... - {price} EUR")

                except Exception as e:
                    if debug:
                        print(f"  [DEBUG] Erro ao processar listing: {e}")
                    continue

        except Exception as e:
            print(f"Error searching: {e}")
        finally:
            await browser.close()

    if not results:
        return None

    prices = [r["preco"] for r in results]

    return VehicleMarketData(
        marca=marca,
        modelo=modelo or "?",
        ano=ano or 0,
        num_resultados=len(results),
        preco_min=min(prices),
        preco_max=max(prices),
        preco_medio=sum(prices) / len(prices),
        preco_mediana=sorted(prices)[len(prices) // 2],
        fonte="standvirtual",
        data_consulta=datetime.now().isoformat(),
        listings=results
    )


@dataclass
class VehicleFullInfo:
    """Complete vehicle information from multiple sources"""
    plate: str
    plate_info: PlateInfo

    # From InfoMatricula or similar
    marca: Optional[str] = None
    modelo: Optional[str] = None
    versao: Optional[str] = None
    ano: Optional[int] = None
    combustivel: Optional[str] = None
    cilindrada: Optional[int] = None
    potencia: Optional[int] = None
    cor: Optional[str] = None

    # From ASF (insurance)
    tem_seguro: Optional[bool] = None
    seguradora: Optional[str] = None

    # From Standvirtual
    market_data: Optional[VehicleMarketData] = None

    # Metadata
    sources: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


async def lookup_plate_infomatricula_api(plate: str, debug: bool = False) -> Dict[str, Any]:
    """
    Lookup vehicle info from InfoMatricula.pt using their API directly.
    Uses Firebase anonymous authentication.

    This is more reliable than scraping!
    """
    result = {}
    clean_plate = plate.replace("-", "").replace(" ", "").upper()

    # Format with hyphens (XX-XX-XX)
    if len(clean_plate) == 6:
        formatted_plate = f"{clean_plate[:2]}-{clean_plate[2:4]}-{clean_plate[4:6]}"
    else:
        formatted_plate = plate

    try:
        # Step 1: Get Firebase anonymous token
        # Firebase API key for infomatricula-login project (public, embedded in their site)
        firebase_api_key = "AIzaSyC0ToM3KDiIgN_cvvRQNmS_0v9a3_oZM9Q"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if debug:
                print("  [DEBUG] Obtendo token Firebase...")

            # Anonymous sign-in to Firebase
            firebase_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={firebase_api_key}"
            firebase_response = await client.post(
                firebase_url,
                json={"returnSecureToken": True}
            )

            if firebase_response.status_code != 200:
                if debug:
                    print(f"  [DEBUG] Erro Firebase: {firebase_response.status_code}")
                return {"error": f"Firebase auth failed: {firebase_response.status_code}"}

            firebase_data = firebase_response.json()
            id_token = firebase_data.get("idToken")

            if not id_token:
                return {"error": "No Firebase token received"}

            if debug:
                print("  [DEBUG] Token obtido, consultando API...")

            # Step 2: Call InfoMatricula API
            api_url = f"https://api.infomatricula.pt/informacao/fetch?plate={formatted_plate}"
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Accept": "application/json",
                "Origin": "https://infomatricula.pt",
                "Referer": "https://infomatricula.pt/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            api_response = await client.get(api_url, headers=headers)

            if debug:
                print(f"  [DEBUG] API response status: {api_response.status_code}")

            if api_response.status_code == 200:
                data = api_response.json()

                if debug:
                    print(f"  [DEBUG] API data: {data}")

                # Map API response to our format
                # API uses English field names: make, model, version, plateDate, etc.
                if data:
                    # Brand/Make
                    result['marca'] = data.get('make') or data.get('marca') or data.get('Marca')

                    # Model
                    result['modelo'] = data.get('model') or data.get('modelo') or data.get('Modelo')

                    # Version
                    result['versao'] = data.get('version') or data.get('versao') or data.get('Versao')

                    # Year - parse from plateDate (format: "3/2023" or "03/2023")
                    plate_date = data.get('plateDate') or data.get('anoMatricula')
                    if plate_date:
                        try:
                            # Extract year from "3/2023" or "2023"
                            if '/' in str(plate_date):
                                result['ano'] = int(str(plate_date).split('/')[-1])
                            else:
                                result['ano'] = int(plate_date)
                        except:
                            pass

                    # Also check markFrom for manufacturing year
                    if 'ano' not in result:
                        mark_from = data.get('markFrom')
                        if mark_from:
                            try:
                                result['ano_fabrico'] = int(mark_from)
                            except:
                                pass

                    # Fuel type
                    result['combustivel'] = data.get('fuelType') or data.get('combustivel') or data.get('tipoCombustivel')

                    # Power (CV and kW)
                    powercv = data.get('powercv') or data.get('potencia')
                    if powercv:
                        try:
                            result['potencia_cv'] = int(str(powercv).replace('cv', '').replace('CV', '').strip())
                        except:
                            pass

                    powerkw = data.get('powerkw')
                    if powerkw:
                        try:
                            result['potencia_kw'] = int(str(powerkw).replace('kw', '').replace('kW', '').strip())
                        except:
                            pass

                    # Color
                    result['cor'] = data.get('color') or data.get('cor') or data.get('Cor')

                    # Category/Body type
                    result['categoria'] = data.get('categoryType') or data.get('bodyType') or data.get('tipoVeiculo')

                    # VIN (chassis number)
                    if data.get('vin'):
                        result['vin'] = data.get('vin')

                    # Owner info
                    if data.get('ownerCategory'):
                        result['tipo_proprietario'] = data.get('ownerCategory')

                    # Import status
                    if data.get('isImported'):
                        result['origem'] = data.get('isImported')

                    # Clean None values
                    result = {k: v for k, v in result.items() if v is not None}

                    if result:
                        result['source'] = 'infomatricula.pt (API)'
                    else:
                        result['error'] = 'Matrícula não encontrada'
                else:
                    result['error'] = 'Resposta vazia da API'

            elif api_response.status_code == 404:
                result['error'] = 'Matrícula não encontrada'
            else:
                result['error'] = f'API error: {api_response.status_code}'

    except Exception as e:
        result['error'] = str(e)

    return result


async def check_insurance_api(plate: str, debug: bool = False) -> Dict[str, Any]:
    """
    Check vehicle insurance status from InfoMatricula API.
    Uses the same Firebase authentication as vehicle lookup.

    Returns: tem_seguro, seguradora, data_inicio, data_fim, etc.
    """
    result = {}
    clean_plate = plate.replace("-", "").replace(" ", "").upper()

    # Format with hyphens (XX-XX-XX)
    if len(clean_plate) == 6:
        formatted_plate = f"{clean_plate[:2]}-{clean_plate[2:4]}-{clean_plate[4:6]}"
    else:
        formatted_plate = plate

    try:
        # Firebase API key (same as vehicle lookup)
        firebase_api_key = "AIzaSyC0ToM3KDiIgN_cvvRQNmS_0v9a3_oZM9Q"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if debug:
                print("  [DEBUG] Obtendo token Firebase...")

            # Anonymous sign-in to Firebase
            firebase_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={firebase_api_key}"
            firebase_response = await client.post(
                firebase_url,
                json={"returnSecureToken": True}
            )

            if firebase_response.status_code != 200:
                if debug:
                    print(f"  [DEBUG] Erro Firebase: {firebase_response.status_code}")
                return {"error": f"Firebase auth failed: {firebase_response.status_code}"}

            firebase_data = firebase_response.json()
            id_token = firebase_data.get("idToken")

            if not id_token:
                return {"error": "No Firebase token received"}

            if debug:
                print("  [DEBUG] Token obtido, consultando API de seguro...")

            # Call Insurance API
            api_url = f"https://api.infomatricula.pt/seguro/fetch?plate={formatted_plate}"
            headers = {
                "Authorization": f"Bearer {id_token}",
                "Accept": "application/json",
                "Origin": "https://infomatricula.pt",
                "Referer": "https://infomatricula.pt/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            api_response = await client.get(api_url, headers=headers)

            if debug:
                print(f"  [DEBUG] API response status: {api_response.status_code}")

            if api_response.status_code == 200:
                data = api_response.json()

                if debug:
                    print(f"  [DEBUG] API data: {data}")

                if data:
                    # Map API response
                    # API returns: entity, startDate, endDate, policy, license, logo

                    # Insurer name (entity is the field name)
                    result['seguradora'] = data.get('entity') or data.get('insurerName') or data.get('seguradora') or data.get('company')

                    # Policy number
                    result['apolice'] = data.get('policy') or data.get('policyNumber') or data.get('apolice')

                    # Dates
                    result['data_inicio'] = data.get('startDate') or data.get('dataInicio')
                    result['data_fim'] = data.get('endDate') or data.get('dataFim')

                    # If we have entity or policy, then vehicle has valid insurance
                    if result.get('seguradora') or result.get('apolice'):
                        result['tem_seguro'] = True
                    else:
                        # Check for explicit status flags
                        has_insurance = data.get('hasInsurance') or data.get('temSeguro') or data.get('insured')
                        if has_insurance is not None:
                            result['tem_seguro'] = bool(has_insurance)
                        elif 'status' in data:
                            result['tem_seguro'] = data['status'].lower() in ['valid', 'active', 'válido', 'ativo']

                    # Clean None values
                    result = {k: v for k, v in result.items() if v is not None}

                    if result:
                        result['source'] = 'infomatricula.pt (API)'
                    else:
                        # If we got data but couldn't parse it, include raw
                        result['raw_data'] = data
                        result['source'] = 'infomatricula.pt (API)'
                else:
                    result['error'] = 'Resposta vazia da API'

            elif api_response.status_code == 404:
                result['error'] = 'Seguro não encontrado'
            else:
                result['error'] = f'API error: {api_response.status_code}'

    except Exception as e:
        result['error'] = str(e)

    return result


async def _accept_cookies(page, timeout: int = 2000):
    """Try to accept cookie consent dialogs on Portuguese sites."""
    cookie_selectors = [
        # Common cookie button selectors
        'button:has-text("Aceitar")',
        'button:has-text("Aceito")',
        'button:has-text("Concordo")',
        'button:has-text("Accept")',
        'button:has-text("OK")',
        '[id*="cookie"] button',
        '[class*="cookie"] button',
        '[id*="consent"] button',
        '[class*="consent"] button',
        '.accept-cookies',
        '#accept-cookies',
        'a:has-text("Aceitar")',
        '[data-testid="cookie-accept"]',
    ]

    for selector in cookie_selectors:
        try:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                await page.wait_for_timeout(500)
                return True
        except:
            continue

    return False


async def lookup_plate_infomatricula(plate: str, debug: bool = False) -> Dict[str, Any]:
    """
    Lookup vehicle info from InfoMatricula.pt
    Requires Playwright - run locally on Windows!

    Returns vehicle details: marca, modelo, ano, combustivel, etc.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "Playwright not installed"}

    result = {}
    clean_plate = plate.replace("-", "").replace(" ", "").upper()

    # Format with hyphens
    if len(clean_plate) == 6:
        formatted_plate = f"{clean_plate[:2]}-{clean_plate[2:4]}-{clean_plate[4:6]}"
    else:
        formatted_plate = plate

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Go to InfoMatricula
            if debug:
                print("  [DEBUG] Navegando para infomatricula.pt...")
            await page.goto('https://infomatricula.pt/', timeout=30000)
            await page.wait_for_timeout(2000)

            # Accept cookies if present
            await _accept_cookies(page)

            # Try different search input selectors
            search_selectors = [
                'input[name="matricula"]',
                'input[placeholder*="matrícula"]',
                'input[placeholder*="matricula"]',
                'input#matricula',
                'input.matricula',
                'input[type="text"]',
            ]

            search_input = None
            for selector in search_selectors:
                search_input = await page.query_selector(selector)
                if search_input:
                    if debug:
                        print(f"  [DEBUG] Input encontrado: {selector}")
                    break

            if search_input:
                await search_input.fill(formatted_plate)
                await page.wait_for_timeout(500)

                # Try different button selectors
                btn_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Pesquisar")',
                    'button:has-text("Consultar")',
                    'input[type="submit"]',
                    'form button',
                    '.search-btn',
                    '#search-btn',
                ]

                for selector in btn_selectors:
                    search_btn = await page.query_selector(selector)
                    if search_btn:
                        if debug:
                            print(f"  [DEBUG] Botão encontrado: {selector}")
                        await search_btn.click()
                        break

                await page.wait_for_timeout(4000)

                # Get page content
                content = await page.content()

                if debug:
                    # Save HTML for debugging
                    with open('debug_infomatricula.html', 'w', encoding='utf-8') as f:
                        f.write(content)
                    print("  [DEBUG] HTML guardado em debug_infomatricula.html")

                # Try to extract data from table rows or definition lists
                # Look for structured data patterns

                # Pattern 1: Table with "Marca", "Modelo", etc.
                rows = await page.query_selector_all('tr, .row, .info-row')
                for row in rows:
                    text = await row.inner_text()
                    text_lower = text.lower()

                    if 'marca' in text_lower:
                        parts = text.split('\n') if '\n' in text else text.split(':')
                        if len(parts) >= 2:
                            result['marca'] = parts[-1].strip()
                    elif 'modelo' in text_lower:
                        parts = text.split('\n') if '\n' in text else text.split(':')
                        if len(parts) >= 2:
                            result['modelo'] = parts[-1].strip()
                    elif 'ano' in text_lower and 'fabricação' not in text_lower:
                        year_match = re.search(r'(19\d{2}|20\d{2})', text)
                        if year_match:
                            result['ano'] = int(year_match.group(1))
                    elif 'combustível' in text_lower or 'combustivel' in text_lower:
                        if 'diesel' in text_lower:
                            result['combustivel'] = 'Diesel'
                        elif 'gasolina' in text_lower:
                            result['combustivel'] = 'Gasolina'

                # Pattern 2: Regex fallback on full content
                if 'marca' not in result:
                    marca_patterns = [
                        r'[Mm]arca[:\s]+([A-Z][A-Z\s\-]+?)(?:\s*[<\n]|\s+[Mm]odelo)',
                        r'<td[^>]*>[Mm]arca</td>\s*<td[^>]*>([^<]+)</td>',
                        r'"marca"[:\s]*"([^"]+)"',
                    ]
                    for pattern in marca_patterns:
                        match = re.search(pattern, content)
                        if match:
                            result['marca'] = match.group(1).strip()
                            break

                if 'modelo' not in result:
                    modelo_patterns = [
                        r'[Mm]odelo[:\s]+([A-Za-z0-9\s\.\-]+?)(?:\s*[<\n])',
                        r'<td[^>]*>[Mm]odelo</td>\s*<td[^>]*>([^<]+)</td>',
                        r'"modelo"[:\s]*"([^"]+)"',
                    ]
                    for pattern in modelo_patterns:
                        match = re.search(pattern, content)
                        if match:
                            result['modelo'] = match.group(1).strip()
                            break

                # Check for fuel type from content
                if 'combustivel' not in result:
                    content_lower = content.lower()
                    if 'diesel' in content_lower:
                        result['combustivel'] = 'Diesel'
                    elif 'gasolina' in content_lower:
                        result['combustivel'] = 'Gasolina'
                    elif 'elétrico' in content_lower or 'eletrico' in content_lower:
                        result['combustivel'] = 'Elétrico'
                    elif 'híbrido' in content_lower or 'hibrido' in content_lower:
                        result['combustivel'] = 'Híbrido'

                if result:
                    result['source'] = 'infomatricula.pt'
            else:
                result['error'] = 'Não foi possível encontrar o campo de pesquisa'

        except Exception as e:
            result['error'] = str(e)
        finally:
            await browser.close()

    return result


async def check_insurance_asf(plate: str, debug: bool = False) -> Dict[str, Any]:
    """
    Check vehicle insurance status from ASF (Autoridade de Supervisão de Seguros)
    Free service: https://www.asf.com.pt/isp/pesquisaseguroauto

    Returns: tem_seguro, seguradora, data_inicio, data_fim
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "Playwright not installed"}

    result = {}
    clean_plate = plate.replace("-", "").replace(" ", "").upper()

    # Format plate with hyphens (XX-XX-XX)
    if len(clean_plate) == 6:
        formatted_plate = f"{clean_plate[:2]}-{clean_plate[2:4]}-{clean_plate[4:6]}"
    else:
        formatted_plate = plate

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Try multiple URLs (ASF has changed URLs over time)
            asf_urls = [
                'https://www.asf.com.pt/isp/pesquisaseguroauto',
                'https://www.asf.com.pt/NR/exeres/B15BFCD1-5298-4B4E-9C99-4DB8D1960A71.htm',
            ]

            page_loaded = False
            for url in asf_urls:
                try:
                    if debug:
                        print(f"  [DEBUG] Tentando URL: {url}")
                    await page.goto(url, timeout=30000)
                    await page.wait_for_timeout(2000)
                    page_loaded = True
                    break
                except:
                    continue

            if not page_loaded:
                result['error'] = 'Não foi possível aceder ao portal ASF'
                return result

            # Accept cookies if present
            await _accept_cookies(page)

            # Find plate input - try various selectors
            input_selectors = [
                'input[name="matricula"]',
                'input[name="Matricula"]',
                'input[id*="matricula"]',
                'input[id*="Matricula"]',
                'input[placeholder*="matrícula"]',
                'input[type="text"]',
            ]

            plate_input = None
            for selector in input_selectors:
                plate_input = await page.query_selector(selector)
                if plate_input:
                    if debug:
                        print(f"  [DEBUG] Input encontrado: {selector}")
                    break

            if plate_input:
                await plate_input.fill(formatted_plate)
                await page.wait_for_timeout(500)

                # Find and click search/submit button
                btn_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Pesquisar")',
                    'button:has-text("Consultar")',
                    'input[value="Pesquisar"]',
                    '.btn-primary',
                    'form button',
                ]

                for selector in btn_selectors:
                    submit_btn = await page.query_selector(selector)
                    if submit_btn:
                        if debug:
                            print(f"  [DEBUG] Botão encontrado: {selector}")
                        await submit_btn.click()
                        break

                await page.wait_for_timeout(4000)

                # Check results
                content = await page.content()
                content_lower = content.lower()

                if debug:
                    with open('debug_asf.html', 'w', encoding='utf-8') as f:
                        f.write(content)
                    print("  [DEBUG] HTML guardado em debug_asf.html")

                # Check for positive insurance indicators
                positive_indicators = [
                    'seguro válido',
                    'apólice',
                    'contrato de seguro',
                    'seguro em vigor',
                    'tem seguro',
                    'cobertura válida',
                ]

                negative_indicators = [
                    'sem seguro',
                    'não tem seguro',
                    'não possui seguro',
                    'sem cobertura',
                    'não foi encontrad',
                ]

                has_positive = any(ind in content_lower for ind in positive_indicators)
                has_negative = any(ind in content_lower for ind in negative_indicators)

                if has_positive and not has_negative:
                    result['tem_seguro'] = True

                    # Try to extract insurer name
                    seguradora_patterns = [
                        r'[Ss]eguradora[:\s]*([A-Za-z\s\-]+?)(?:\s*[<\n])',
                        r'[Cc]ompanhia[:\s]*([A-Za-z\s\-]+?)(?:\s*[<\n])',
                        r'<td[^>]*>[Ss]eguradora</td>\s*<td[^>]*>([^<]+)</td>',
                    ]
                    for pattern in seguradora_patterns:
                        match = re.search(pattern, content)
                        if match:
                            result['seguradora'] = match.group(1).strip()
                            break

                elif has_negative:
                    result['tem_seguro'] = False

                result['source'] = 'asf.com.pt'

            else:
                result['error'] = 'Não foi possível encontrar o campo de matrícula'

        except Exception as e:
            result['error'] = str(e)
        finally:
            await browser.close()

    return result


async def get_full_vehicle_info(plate: str, include_market: bool = True) -> VehicleFullInfo:
    """
    Get complete vehicle information from all available sources.

    Sources:
    1. Plate decoder (instant)
    2. InfoMatricula.pt (free, requires Playwright)
    3. ASF insurance check (free, requires Playwright)
    4. Standvirtual market prices (free, requires Playwright)
    """
    # 1. Decode plate
    plate_info = decode_portuguese_plate(plate)

    result = VehicleFullInfo(
        plate=plate,
        plate_info=plate_info,
        sources=['plate_decoder']
    )

    # 2. Try InfoMatricula API first (no Playwright needed!)
    try:
        info = await lookup_plate_infomatricula_api(plate)
        if 'error' not in info and info:
            result.marca = info.get('marca')
            result.modelo = info.get('modelo')
            result.versao = info.get('versao')
            result.ano = info.get('ano')
            result.combustivel = info.get('combustivel')
            result.cilindrada = info.get('cilindrada')
            result.potencia = info.get('potencia')
            result.cor = info.get('cor')
            result.sources.append('infomatricula.pt (API)')
        else:
            # Fallback to scraping if API fails
            info = await lookup_plate_infomatricula(plate)
            if 'error' not in info:
                result.marca = info.get('marca')
                result.modelo = info.get('modelo')
                result.ano = info.get('ano')
                result.combustivel = info.get('combustivel')
                result.sources.append('infomatricula.pt')
            else:
                result.errors.append(f"InfoMatricula: {info.get('error', 'unknown')}")
    except Exception as e:
        result.errors.append(f"InfoMatricula: {str(e)}")

    # 3. Check insurance
    try:
        insurance = await check_insurance_asf(plate)
        if 'error' not in insurance:
            result.tem_seguro = insurance.get('tem_seguro')
            result.seguradora = insurance.get('seguradora')
            result.sources.append('asf.fga.com.pt')
        else:
            result.errors.append(f"ASF: {insurance['error']}")
    except Exception as e:
        result.errors.append(f"ASF: {str(e)}")

    # 4. Get market prices (if we have marca/modelo)
    if include_market and result.marca:
        try:
            market = await get_market_prices(
                result.marca,
                result.modelo,
                result.ano or plate_info.year_min
            )
            if market:
                result.market_data = market
                result.sources.append(market.fonte)
        except Exception as e:
            result.errors.append(f"Market prices: {str(e)}")

    return result


async def search_autouncle(marca: str, modelo: str = None, ano: int = None, debug: bool = False) -> Optional[VehicleMarketData]:
    """
    Search AutoUncle.pt for vehicle market prices.
    Alternative to Standvirtual that may be more reliable.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed")
        return None

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Build search URL
            marca_slug = marca.lower().replace(" ", "-").replace("_", "-")

            # AutoUncle URL format
            url = f"https://www.autouncle.pt/pt/carros-usados/{marca_slug}"

            if modelo:
                modelo_slug = modelo.lower().replace(" ", "-").split('-')[0]
                url = f"{url}/{modelo_slug}"

            if ano:
                url = f"{url}?year_from={ano-2}&year_to={ano+2}"

            if debug:
                print(f"  [DEBUG] AutoUncle URL: {url}")

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            # Accept cookies
            await _accept_cookies(page)

            content = await page.content()

            if debug:
                with open('debug_autouncle.html', 'w', encoding='utf-8') as f:
                    f.write(content)

            # Find listings
            listing_selectors = [
                '.car-card',
                '[class*="listing"]',
                'article',
                '.result-item',
            ]

            listings = []
            for selector in listing_selectors:
                listings = await page.query_selector_all(selector)
                if listings and len(listings) > 2:
                    if debug:
                        print(f"  [DEBUG] AutoUncle: {len(listings)} listings com {selector}")
                    break

            for listing in listings[:20]:
                try:
                    # Get all text and look for prices
                    text = await listing.inner_text()

                    # Find price pattern (XX.XXX € or XX XXX EUR)
                    price_match = re.search(r'(\d{1,3}[\.\s]?\d{3})\s*(?:€|EUR)', text)
                    if price_match:
                        price = int(price_match.group(1).replace('.', '').replace(' ', ''))

                        # Get title (first line usually)
                        title = text.split('\n')[0].strip()[:80]

                        if price > 500 and title:
                            results.append({
                                "titulo": title,
                                "preco": price,
                                "params": ""
                            })
                            if debug:
                                print(f"  [DEBUG] AutoUncle: {title[:30]}... - {price} EUR")

                except:
                    continue

        except Exception as e:
            if debug:
                print(f"  [DEBUG] AutoUncle error: {e}")
        finally:
            await browser.close()

    if not results:
        return None

    prices = [r["preco"] for r in results]

    return VehicleMarketData(
        marca=marca,
        modelo=modelo or "?",
        ano=ano or 0,
        num_resultados=len(results),
        preco_min=min(prices),
        preco_max=max(prices),
        preco_medio=sum(prices) / len(prices),
        preco_mediana=sorted(prices)[len(prices) // 2],
        fonte="autouncle",
        data_consulta=datetime.now().isoformat(),
        listings=results
    )


async def get_market_prices(marca: str, modelo: str = None, ano: int = None, debug: bool = False) -> Optional[VehicleMarketData]:
    """
    Get market prices from multiple sources. Tries StandVirtual first, then AutoUncle.
    """
    # Try StandVirtual first
    result = await search_standvirtual(marca, modelo, ano, debug)
    if result and result.num_resultados > 0:
        return result

    # Fallback to AutoUncle
    if debug:
        print("  [DEBUG] StandVirtual sem resultados, tentando AutoUncle...")

    result = await search_autouncle(marca, modelo, ano, debug)
    if result and result.num_resultados > 0:
        return result

    return None


# Quick test function
async def test_plate_lookup(plate: str):
    """Test the plate lookup functionality"""
    print(f"\n{'='*50}")
    print(f"Matrícula: {plate}")
    print(f"{'='*50}\n")

    # Decode plate
    info = decode_portuguese_plate(plate)
    print(f"Formato: {info.format}")
    print(f"Era: {info.era}")
    print(f"Ano estimado: {info.year_min}-{info.year_max}")
    print(f"Notas: {info.notes}")

    return info


async def test_full_lookup(plate: str):
    """Test complete vehicle lookup"""
    print(f"\n{'='*60}")
    print(f"🚗 LOOKUP COMPLETO: {plate}")
    print(f"{'='*60}\n")

    result = await get_full_vehicle_info(plate, include_market=False)

    print(f"📋 Matrícula decodificada:")
    print(f"   Formato: {result.plate_info.format}")
    print(f"   Ano estimado: {result.plate_info.year_min}-{result.plate_info.year_max}")

    if result.marca:
        print(f"\n🚘 Informação do veículo:")
        print(f"   Marca: {result.marca}")
        print(f"   Modelo: {result.modelo}")
        print(f"   Ano: {result.ano}")
        print(f"   Combustível: {result.combustivel}")

    if result.tem_seguro is not None:
        print(f"\n🛡️ Seguro:")
        print(f"   Tem seguro: {'Sim' if result.tem_seguro else 'Não'}")
        if result.seguradora:
            print(f"   Seguradora: {result.seguradora}")

    print(f"\n📊 Fontes utilizadas: {', '.join(result.sources)}")

    if result.errors:
        print(f"\n⚠️ Erros: {', '.join(result.errors)}")

    return result


if __name__ == "__main__":
    import asyncio

    # Test with the plate provided
    asyncio.run(test_full_lookup("AZ-84-OB"))
