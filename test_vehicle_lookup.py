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
    lookup_plate_infomatricula_api,
    check_insurance_api,
    get_market_prices,
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

    # 2. Lookup from InfoMatricula.pt API
    print("\n🔍 2. LOOKUP INFOMATRICULA.PT (API)")
    print("-" * 40)
    print(f"   A pesquisar {plate} via API...")

    vehicle_info = None
    try:
        info_result = await lookup_plate_infomatricula_api(plate, debug=True)
        if 'error' in info_result:
            print(f"   ⚠️  Erro: {info_result['error']}")
        elif not any(k for k in info_result if k != 'source'):
            print(f"   ⚠️  Sem dados encontrados")
        else:
            print(f"   ✅ Resultado (fonte: {info_result.get('source', 'API')}):")
            for key, value in info_result.items():
                if value and key != 'source':
                    print(f"      {key}: {value}")
            vehicle_info = info_result
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    # 3. Check insurance via API
    print("\n🛡️  3. VERIFICAR SEGURO (API)")
    print("-" * 40)
    print(f"   A verificar {plate} via API...")

    try:
        insurance = await check_insurance_api(plate, debug=True)
        if 'error' in insurance:
            print(f"   ⚠️  Erro: {insurance['error']}")
        elif 'raw_data' in insurance:
            print(f"   📋 Dados brutos da API:")
            print(f"      {insurance['raw_data']}")
        else:
            if insurance.get('tem_seguro') is True:
                print(f"   ✅ Veículo TEM seguro válido")
                if insurance.get('seguradora'):
                    print(f"      Seguradora: {insurance['seguradora']}")
                if insurance.get('apolice'):
                    print(f"      Apólice: {insurance['apolice']}")
                if insurance.get('data_fim'):
                    print(f"      Válido até: {insurance['data_fim']}")
            elif insurance.get('tem_seguro') is False:
                print(f"   ❌ Veículo NÃO tem seguro!")
            else:
                print(f"   ⚠️  Não foi possível determinar")
                print(f"      Dados: {insurance}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    # 4. Search market prices using vehicle info
    print("\n💰 4. PREÇOS DE MERCADO")
    print("-" * 40)

    # Use vehicle info from API if available
    if vehicle_info:
        marca = vehicle_info.get('marca', 'POLESTAR')
        modelo = vehicle_info.get('modelo', 'POLESTAR 2')
        ano = vehicle_info.get('ano', 2023)
        combustivel = vehicle_info.get('combustivel', 'ELÉTRICO')
        print(f"   A pesquisar {marca} {modelo} {ano} ({combustivel})...")
    else:
        marca = "POLESTAR"
        modelo = "POLESTAR 2"
        ano = 2023
        combustivel = "ELÉTRICO"
        print(f"   A pesquisar {marca} {modelo} {ano}...")

    try:
        market_data = await get_market_prices(marca, modelo, ano, debug=True)

        if market_data:
            print(f"\n   ✅ Encontrados {market_data.num_resultados} resultados!")
            print(f"   Fonte: {market_data.fonte}")
            print(f"   Preço mínimo:  {market_data.preco_min:>10,.0f} EUR")
            print(f"   Preço máximo:  {market_data.preco_max:>10,.0f} EUR")
            print(f"   Preço médio:   {market_data.preco_medio:>10,.0f} EUR")
            print(f"   Preço mediana: {market_data.preco_mediana:>10,.0f} EUR")

            print("\n   📋 Alguns anúncios:")
            for listing in market_data.listings[:5]:
                print(f"      - {listing['titulo'][:50]}: {listing['preco']:,} EUR")
        else:
            print("   ⚠️  Nenhum resultado encontrado")

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
