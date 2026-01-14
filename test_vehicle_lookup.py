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

from services.vehicle_lookup import (
    decode_portuguese_plate,
    extract_vehicle_from_title,
    search_standvirtual,
    search_autouncle,
    get_market_prices,
    lookup_plate_infomatricula,
    check_insurance_asf,
    get_full_vehicle_info
)


async def main():
    plate = "AZ-84-OB"

    print("\n" + "=" * 60)
    print("🚗 TESTE DE LOOKUP DE VEÍCULO")
    print("=" * 60)

    # 1. Decode plate (instant)
    print(f"\n📋 1. DECODE DA MATRÍCULA: {plate}")
    print("-" * 40)

    info = decode_portuguese_plate(plate)
    print(f"   Formato: {info.format}")
    print(f"   Era: {info.era}")
    print(f"   Ano estimado: {info.year_min} - {info.year_max}")
    print(f"   Notas: {info.notes}")

    # 2. Test title extraction
    print("\n📝 2. EXTRAÇÃO DE TÍTULO")
    print("-" * 40)

    test_titles = [
        "BMW 320d de 2015",
        "VOLKSWAGEN GOLF 1.6 TDI 2018",
        "RENAULT MEGANE 1.5 DCI",
        "MERCEDES-BENZ CLASSE C 220d",
    ]

    for title in test_titles:
        result = extract_vehicle_from_title(title)
        print(f"   '{title}'")
        print(f"   -> Marca: {result['marca']}, Modelo: {result['modelo']}, Ano: {result['ano']}")

    # 3. Lookup from InfoMatricula.pt
    print("\n🔍 3. LOOKUP INFOMATRICULA.PT")
    print("-" * 40)
    print(f"   A pesquisar {plate}...")

    try:
        info_result = await lookup_plate_infomatricula(plate, debug=True)
        if 'error' in info_result:
            print(f"   ⚠️  Erro: {info_result['error']}")
        elif not any(k for k in info_result if k != 'source'):
            print(f"   ⚠️  Sem dados encontrados (ver debug_infomatricula.html)")
        else:
            print(f"   ✅ Resultado:")
            for key, value in info_result.items():
                if value and key != 'source':
                    print(f"      {key}: {value}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    # 4. Check insurance from ASF
    print("\n🛡️  4. VERIFICAR SEGURO (ASF)")
    print("-" * 40)
    print(f"   A verificar {plate}...")

    try:
        insurance = await check_insurance_asf(plate, debug=True)
        if 'error' in insurance:
            print(f"   ⚠️  Erro: {insurance['error']}")
        else:
            if insurance.get('tem_seguro') is True:
                print(f"   ✅ Veículo TEM seguro válido")
                if insurance.get('seguradora'):
                    print(f"      Seguradora: {insurance['seguradora']}")
            elif insurance.get('tem_seguro') is False:
                print(f"   ❌ Veículo NÃO tem seguro!")
            else:
                print(f"   ⚠️  Não foi possível determinar (ver debug_asf.html)")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    # 5. Search market prices (StandVirtual + AutoUncle)
    print("\n💰 5. PREÇOS DE MERCADO")
    print("-" * 40)
    print("   A pesquisar BMW 320d 2020-2024...")

    try:
        # Try combined search (StandVirtual first, then AutoUncle)
        market_data = await get_market_prices("BMW", "320d", 2022, debug=True)

        if market_data:
            print(f"\n   ✅ Encontrados {market_data.num_resultados} resultados!")
            print(f"   Fonte: {market_data.fonte}")
            print(f"   Preço mínimo:  {market_data.preco_min:>10,.0f} EUR")
            print(f"   Preço máximo:  {market_data.preco_max:>10,.0f} EUR")
            print(f"   Preço médio:   {market_data.preco_medio:>10,.0f} EUR")
            print(f"   Preço mediana: {market_data.preco_mediana:>10,.0f} EUR")

            print("\n   📋 Alguns anúncios:")
            for listing in market_data.listings[:5]:
                print(f"      - {listing['titulo'][:40]}: {listing['preco']:,} EUR")
        else:
            print("   ⚠️  Nenhum resultado encontrado")
            print("   (ver debug_standvirtual.html e debug_autouncle.html)")

    except Exception as e:
        print(f"   ❌ Erro: {e}")
        print("   💡 Certifica-te que tens Playwright instalado:")
        print("      pip install playwright")
        print("      playwright install chromium")

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
