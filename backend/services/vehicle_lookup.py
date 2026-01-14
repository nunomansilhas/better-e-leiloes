"""
Vehicle Lookup Service
Provides license plate decoding and market price lookup for Portuguese vehicles.
"""

import re
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
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


if __name__ == "__main__":
    import asyncio

    # Test with the plate provided
    asyncio.run(test_plate_lookup("AZ-84-OB"))
