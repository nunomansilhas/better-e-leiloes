# -*- coding: utf-8 -*-
"""
Test Enhanced AI Analysis Service
Run this locally on Windows to test the full analysis pipeline.

Usage:
    cd C:/Users/mansi/Downloads/e-leiloes-aux
    python test_enhanced_ai.py
"""

import asyncio
import sys
import json
sys.path.insert(0, 'backend')

from services.ai_analysis_service import get_enhanced_ai_service, EnhancedAIAnalysisService


# Sample test data
SAMPLE_VEHICLE = {
    "reference": "LO1424842025",
    "titulo": "BMW 320D de 2021",
    "tipo_id": 2,
    "tipo": "Veículo",
    "subtipo": "Ligeiro de Passageiros",
    "matricula": "AZ-84-OB",
    "distrito": "Lisboa",
    "concelho": "Lisboa",
    "valor_base": 18500,
    "valor_abertura": 14000,
    "lance_atual": 0,
    "descricao": "Veículo BMW 320D, cor preta, 5 lugares, motor diesel 2.0, 150cv. Estado geral bom. Quilometragem: 85.000km. Revisões em dia.",
    "fotos": [
        {"url": "https://e-leiloes.pt/fotos/exemplo1.jpg"},
        {"url": "https://e-leiloes.pt/fotos/exemplo2.jpg"},
    ]
}

SAMPLE_PROPERTY = {
    "reference": "LO1427992025",
    "titulo": "Apartamento T2 em Almada",
    "tipo_id": 1,
    "tipo": "Imóvel",
    "subtipo": "Apartamento",
    "tipologia": "T2",
    "distrito": "Setúbal",
    "concelho": "Almada",
    "freguesia": "Cacilhas",
    "valor_base": 125000,
    "valor_abertura": 95000,
    "lance_atual": 0,
    "area_total": 75,
    "area_privativa": 68,
    "descricao": "Apartamento T2 com 75m2, 3º andar com elevador. Cozinha equipada, 2 quartos, 1 WC. Arrecadação no sótão. Necessita de algumas obras de remodelação. Boa exposição solar.",
    "fotos": []
}


async def test_models():
    """Check if required models are available"""
    print("\n" + "=" * 60)
    print("🔍 VERIFICAR MODELOS OLLAMA")
    print("=" * 60 + "\n")

    service = get_enhanced_ai_service()
    status = await service.check_models()

    print(f"Modelos disponíveis: {len(status.get('available_models', []))}")
    for model in status.get('available_models', []):
        print(f"  - {model}")

    print(f"\n📝 Modelo de texto: {status.get('text_model')}")
    print(f"   Disponível: {'✅' if status.get('text_model_available') else '❌'}")

    print(f"\n🖼️  Modelo de visão: {status.get('vision_model')}")
    print(f"   Disponível: {'✅' if status.get('vision_model_available') else '❌'}")

    if not status.get('text_model_available'):
        print(f"\n⚠️  Instala o modelo de texto com: ollama pull {status.get('text_model')}")

    if not status.get('vision_model_available'):
        print(f"\n⚠️  Para análise de imagens, instala: ollama pull llava:7b")

    return status


async def test_vehicle_analysis():
    """Test vehicle analysis with batch questions"""
    print("\n" + "=" * 60)
    print("🚗 TESTE DE ANÁLISE DE VEÍCULO")
    print("=" * 60 + "\n")

    service = get_enhanced_ai_service()

    print(f"Evento: {SAMPLE_VEHICLE['titulo']}")
    print(f"Referência: {SAMPLE_VEHICLE['reference']}")
    print(f"Matrícula: {SAMPLE_VEHICLE['matricula']}")
    print(f"Valor: {SAMPLE_VEHICLE['valor_base']}€")
    print("\nA analisar... (pode demorar 1-2 minutos)\n")

    # Run analysis WITHOUT images (since we don't have real URLs)
    result = await service.analyze_vehicle(SAMPLE_VEHICLE, analyze_images=False)

    print("=" * 40)
    print("📊 RESULTADO DA ANÁLISE")
    print("=" * 40)

    print(f"\n📋 Informação da Matrícula:")
    if result.plate_info:
        print(f"   Formato: {result.plate_info.get('format')}")
        print(f"   Era: {result.plate_info.get('era')}")
        print(f"   Ano estimado: {result.plate_info.get('year_min')}-{result.plate_info.get('year_max')}")

    print(f"\n🚘 Informação do Veículo:")
    if result.vehicle_info:
        print(f"   Marca: {result.vehicle_info.get('marca')}")
        print(f"   Modelo: {result.vehicle_info.get('modelo')}")

    print(f"\n❓ Perguntas Batch ({len(result.questions)}):")
    for i, q in enumerate(result.questions, 1):
        print(f"\n   {i}. {q.question_id}")
        print(f"      Tempo: {q.time_ms}ms | Tokens: {q.tokens_used}")
        # Show truncated answer
        answer = q.answer[:200] + "..." if len(q.answer) > 200 else q.answer
        print(f"      Resposta: {answer}")

    print(f"\n⭐ VEREDICTO FINAL:")
    print(f"   Score: {result.score}/10")
    print(f"   Recomendação: {result.recommendation.upper()}")
    print(f"   Resumo: {result.summary}")

    if result.pros:
        print(f"\n   ✅ Prós:")
        for pro in result.pros:
            print(f"      - {pro}")

    if result.cons:
        print(f"\n   ❌ Contras:")
        for con in result.cons:
            print(f"      - {con}")

    print(f"\n📈 Estatísticas:")
    print(f"   Tempo total: {result.total_time_ms}ms")
    print(f"   Tokens usados: {result.total_tokens}")
    print(f"   Modelos: {', '.join(result.models_used)}")

    return result


async def test_property_analysis():
    """Test property analysis with batch questions"""
    print("\n" + "=" * 60)
    print("🏠 TESTE DE ANÁLISE DE IMÓVEL")
    print("=" * 60 + "\n")

    service = get_enhanced_ai_service()

    print(f"Evento: {SAMPLE_PROPERTY['titulo']}")
    print(f"Referência: {SAMPLE_PROPERTY['reference']}")
    print(f"Local: {SAMPLE_PROPERTY['freguesia']}, {SAMPLE_PROPERTY['concelho']}")
    print(f"Área: {SAMPLE_PROPERTY['area_total']}m²")
    print(f"Valor: {SAMPLE_PROPERTY['valor_base']}€")
    print("\nA analisar... (pode demorar 1-2 minutos)\n")

    result = await service.analyze_property(SAMPLE_PROPERTY, analyze_images=False)

    print("=" * 40)
    print("📊 RESULTADO DA ANÁLISE")
    print("=" * 40)

    print(f"\n❓ Perguntas Batch ({len(result.questions)}):")
    for i, q in enumerate(result.questions, 1):
        print(f"\n   {i}. {q.question_id}")
        print(f"      Tempo: {q.time_ms}ms | Tokens: {q.tokens_used}")
        answer = q.answer[:200] + "..." if len(q.answer) > 200 else q.answer
        print(f"      Resposta: {answer}")

    print(f"\n⭐ VEREDICTO FINAL:")
    print(f"   Score: {result.score}/10")
    print(f"   Recomendação: {result.recommendation.upper()}")
    print(f"   Resumo: {result.summary}")

    if result.pros:
        print(f"\n   ✅ Prós:")
        for pro in result.pros:
            print(f"      - {pro}")

    if result.cons:
        print(f"\n   ❌ Contras:")
        for con in result.cons:
            print(f"      - {con}")

    print(f"\n📈 Estatísticas:")
    print(f"   Tempo total: {result.total_time_ms}ms")
    print(f"   Tokens usados: {result.total_tokens}")

    return result


async def main():
    print("\n" + "🤖" * 30)
    print("\n   TESTE DO SERVIÇO DE ANÁLISE AI MELHORADO")
    print("\n" + "🤖" * 30)

    # 1. Check models
    status = await test_models()

    if not status.get('text_model_available'):
        print("\n❌ Modelo de texto não disponível. Instala com:")
        print(f"   ollama pull {status.get('text_model')}")
        return

    # 2. Test vehicle analysis
    print("\n\nQueres testar a análise de VEÍCULO? (s/n): ", end="")
    try:
        if input().lower() in ['s', 'sim', 'y', 'yes', '']:
            await test_vehicle_analysis()
    except:
        await test_vehicle_analysis()

    # 3. Test property analysis
    print("\n\nQueres testar a análise de IMÓVEL? (s/n): ", end="")
    try:
        if input().lower() in ['s', 'sim', 'y', 'yes', '']:
            await test_property_analysis()
    except:
        await test_property_analysis()

    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
