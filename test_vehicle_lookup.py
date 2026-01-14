# -*- coding: utf-8 -*-
"""
Test script for vehicle lookup - Run this locally on Windows!

Usage:
    cd C:/Users/mansi/Downloads/e-leiloes-aux
    python test_vehicle_lookup.py
"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from services.vehicle_lookup import decode_portuguese_plate, extract_vehicle_from_title, search_standvirtual


async def main():
    plate = "AZ-84-OB"

    print("\n" + "=" * 60)
    print("🚗 TESTE DE LOOKUP DE VEÍCULO")
    print("=" * 60)

    # 1. Decode plate
    print(f"\n📋 MATRÍCULA: {plate}")
    print("-" * 40)

    info = decode_portuguese_plate(plate)
    print(f"   Formato: {info.format}")
    print(f"   Era: {info.era}")
    print(f"   Ano estimado: {info.year_min} - {info.year_max}")
    print(f"   Notas: {info.notes}")

    # 2. Test title extraction
    print("\n📝 TESTE DE EXTRAÇÃO DE TÍTULO")
    print("-" * 40)

    test_titles = [
        "BMW 320d de 2015",
        "VOLKSWAGEN GOLF 1.6 TDI 2018",
        "RENAULT MEGANE 1.5 DCI",
        "MERCEDES-BENZ CLASSE C 220d",
        "PEUGEOT 308 1.6 HDI 2020",
    ]

    for title in test_titles:
        result = extract_vehicle_from_title(title)
        print(f"   '{title}'")
        print(f"   → Marca: {result['marca']}, Modelo: {result['modelo']}, Ano: {result['ano']}")
        print()

    # 3. Search Standvirtual (only works locally!)
    print("\n🔍 PESQUISA NO STANDVIRTUAL")
    print("-" * 40)
    print("   A pesquisar por BMW 320d 2020-2025...")

    try:
        market_data = await search_standvirtual("BMW", "320d", 2022)

        if market_data:
            print(f"\n   ✅ Encontrados {market_data.num_resultados} resultados!")
            print(f"   💰 Preço mínimo: {market_data.preco_min:,.0f}€")
            print(f"   💰 Preço máximo: {market_data.preco_max:,.0f}€")
            print(f"   💰 Preço médio: {market_data.preco_medio:,.0f}€")
            print(f"   💰 Preço mediana: {market_data.preco_mediana:,.0f}€")

            print("\n   📋 Alguns anúncios:")
            for listing in market_data.listings[:5]:
                print(f"      - {listing['titulo']}: {listing['preco']:,}€")
        else:
            print("   ❌ Nenhum resultado encontrado")

    except Exception as e:
        print(f"   ❌ Erro: {e}")
        print("   💡 Certifica-te que tens Playwright instalado:")
        print("      pip install playwright")
        print("      playwright install chromium")


if __name__ == "__main__":
    asyncio.run(main())
