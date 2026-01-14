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
    # Common car brands in Portugal
    brands = [
        "ABARTH", "ALFA ROMEO", "AUDI", "BMW", "CHEVROLET", "CHRYSLER", "CITROEN",
        "DACIA", "FIAT", "FORD", "HONDA", "HYUNDAI", "JAGUAR", "JEEP", "KIA",
        "LAND ROVER", "LEXUS", "MAZDA", "MERCEDES", "MERCEDES-BENZ", "MINI",
        "MITSUBISHI", "NISSAN", "OPEL", "PEUGEOT", "PORSCHE", "RENAULT", "SEAT",
        "SKODA", "SMART", "SUZUKI", "TESLA", "TOYOTA", "VOLKSWAGEN", "VOLVO"
    ]

    title_upper = title.upper()

    # Find brand
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


async def search_standvirtual(marca: str, modelo: str, ano: int = None) -> Optional[VehicleMarketData]:
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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Build search URL
            marca_slug = marca.lower().replace(" ", "-")
            url = f"https://www.standvirtual.com/carros/{marca_slug}"

            if modelo:
                modelo_slug = modelo.lower().replace(" ", "-").replace(".", "-")
                url = f"{url}/{modelo_slug}"

            # Add year filter
            params = []
            if ano:
                params.append(f"search[filter_float_year:from]={ano-1}")
                params.append(f"search[filter_float_year:to]={ano+1}")

            if params:
                url = f"{url}?{'&'.join(params)}"

            print(f"Searching: {url}")

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            # Extract listings
            listings = await page.query_selector_all('article[data-testid="listing-ad"]')

            for listing in listings[:20]:  # Max 20 results
                try:
                    # Price
                    price_el = await listing.query_selector('[data-testid="ad-price"]')
                    price_text = await price_el.inner_text() if price_el else "0"
                    price = int(re.sub(r'[^\d]', '', price_text) or 0)

                    # Title
                    title_el = await listing.query_selector('h2')
                    title = await title_el.inner_text() if title_el else ""

                    # Year/Km
                    params_el = await listing.query_selector('[data-testid="ad-parameters"]')
                    params_text = await params_el.inner_text() if params_el else ""

                    if price > 0:
                        results.append({
                            "titulo": title.strip(),
                            "preco": price,
                            "params": params_text.strip()
                        })
                except:
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


async def lookup_plate_infomatricula(plate: str) -> Dict[str, Any]:
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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Go to InfoMatricula
            await page.goto('https://infomatricula.pt/', timeout=30000)
            await page.wait_for_timeout(2000)

            # Find and fill the search input
            search_input = await page.query_selector('input[type="text"]')
            if search_input:
                await search_input.fill(clean_plate)
                await page.wait_for_timeout(500)

                # Click search button
                search_btn = await page.query_selector('button[type="submit"]')
                if search_btn:
                    await search_btn.click()
                    await page.wait_for_timeout(3000)

                    # Extract vehicle info from results
                    content = await page.content()

                    # Look for common patterns in the result
                    # Marca
                    marca_match = re.search(r'[Mm]arca[:\s]*([A-Z][A-Za-z\s]+)', content)
                    if marca_match:
                        result['marca'] = marca_match.group(1).strip()

                    # Modelo
                    modelo_match = re.search(r'[Mm]odelo[:\s]*([A-Za-z0-9\s\.]+)', content)
                    if modelo_match:
                        result['modelo'] = modelo_match.group(1).strip()

                    # Ano
                    ano_match = re.search(r'[Aa]no[:\s]*(19\d{2}|20\d{2})', content)
                    if ano_match:
                        result['ano'] = int(ano_match.group(1))

                    # Combustivel
                    if 'diesel' in content.lower():
                        result['combustivel'] = 'Diesel'
                    elif 'gasolina' in content.lower():
                        result['combustivel'] = 'Gasolina'
                    elif 'elétrico' in content.lower() or 'eletrico' in content.lower():
                        result['combustivel'] = 'Elétrico'
                    elif 'híbrido' in content.lower() or 'hibrido' in content.lower():
                        result['combustivel'] = 'Híbrido'

                    result['source'] = 'infomatricula.pt'

        except Exception as e:
            result['error'] = str(e)
        finally:
            await browser.close()

    return result


async def check_insurance_asf(plate: str) -> Dict[str, Any]:
    """
    Check vehicle insurance status from ASF (Autoridade de Supervisão de Seguros)
    Free service: https://www.fga.asf.com.pt/

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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-PT'
        )
        page = await context.new_page()

        try:
            # Go to ASF FGA portal
            await page.goto('https://www.fga.asf.com.pt/pt/verificar-matricula', timeout=30000)
            await page.wait_for_timeout(2000)

            # Find plate input
            plate_input = await page.query_selector('input[name="matricula"]')
            if not plate_input:
                plate_input = await page.query_selector('input[type="text"]')

            if plate_input:
                await plate_input.fill(formatted_plate)
                await page.wait_for_timeout(500)

                # Find and click search/submit button
                submit_btn = await page.query_selector('button[type="submit"]')
                if not submit_btn:
                    submit_btn = await page.query_selector('input[type="submit"]')

                if submit_btn:
                    await submit_btn.click()
                    await page.wait_for_timeout(3000)

                    # Check results
                    content = await page.content()

                    # Check if vehicle has insurance
                    if 'seguro válido' in content.lower() or 'apólice' in content.lower():
                        result['tem_seguro'] = True

                        # Try to extract insurer name
                        seguradora_match = re.search(r'[Ss]eguradora[:\s]*([A-Za-z\s]+)', content)
                        if seguradora_match:
                            result['seguradora'] = seguradora_match.group(1).strip()
                    elif 'sem seguro' in content.lower() or 'não tem' in content.lower():
                        result['tem_seguro'] = False

                    result['source'] = 'asf.fga.com.pt'

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

    # 2. Try InfoMatricula
    try:
        info = await lookup_plate_infomatricula(plate)
        if 'error' not in info:
            result.marca = info.get('marca')
            result.modelo = info.get('modelo')
            result.ano = info.get('ano')
            result.combustivel = info.get('combustivel')
            result.sources.append('infomatricula.pt')
        else:
            result.errors.append(f"InfoMatricula: {info['error']}")
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
            market = await search_standvirtual(
                result.marca,
                result.modelo,
                result.ano or plate_info.year_min
            )
            if market:
                result.market_data = market
                result.sources.append('standvirtual.com')
        except Exception as e:
            result.errors.append(f"Standvirtual: {str(e)}")

    return result


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
