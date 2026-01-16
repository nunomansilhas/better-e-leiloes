# -*- coding: utf-8 -*-
"""
AI Questions Service - Structured Vehicle Analysis

Provides structured questions to the AI with fixed JSON output schemas.
Each question has a defined input and output format to ensure consistency.

Author: Better E-Leiloes Team
"""

import json
import re
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from logger import log_info, log_warning, log_error


@dataclass
class QuestionResult:
    """Result of a single AI question"""
    question_id: str
    question: str
    answer: Dict[str, Any]
    raw_answer: str
    confidence: float
    time_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class VehicleAnalysisResult:
    """Complete analysis result from all questions"""
    # Scores (0-10)
    score_oportunidade: float = 0
    score_risco: float = 0
    score_liquidez: float = 0
    score_final: float = 0

    # AI recommendation
    recomendacao: str = "cautela"  # evitar, cautela, considerar, comprar, excelente
    resumo: str = ""
    lance_maximo_sugerido: Optional[float] = None

    # Lists
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)

    # Known issues for the model
    problemas_conhecidos: List[Dict[str, Any]] = field(default_factory=list)

    # Raw question results
    question_results: List[QuestionResult] = field(default_factory=list)

    # Metadata
    model_used: str = ""
    total_time_ms: int = 0
    total_tokens: int = 0

    # Investment analysis (programmatic calculation, not AI)
    investment_analysis: Optional[Dict[str, Any]] = None


# =============================================================================
# STRUCTURED QUESTIONS WITH JSON SCHEMAS
# =============================================================================

QUESTIONS = [
    {
        "id": "known_issues",
        "name": "Problemas Mencionados na Descrição",
        "description": "Extrai problemas mencionados na descrição e observações do leilão",
        "template": """Analisa a descrição e observações deste veículo em leilão e extrai APENAS os problemas que são EXPLICITAMENTE mencionados no texto.

TÍTULO: {titulo}
DESCRIÇÃO: {descricao}

IMPORTANTE: NÃO inventes problemas. Extrai APENAS o que está escrito no texto acima.

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO (sem texto adicional):
{{
    "problemas": [
        {{
            "problema": "descrição do problema conforme mencionado",
            "gravidade": "baixa|media|alta",
            "fonte": "onde no texto foi mencionado"
        }}
    ],
    "estado_geral_mencionado": "desconhecido|mau|razoavel|bom|excelente",
    "observacoes_importantes": ["lista de observações importantes do texto"]
}}

Se não há problemas mencionados no texto, devolve lista vazia em "problemas".""",
        "default_output": {
            "problemas": [],
            "estado_geral_mencionado": "desconhecido",
            "observacoes_importantes": []
        }
    },
    {
        "id": "description_analysis",
        "name": "Análise da Descrição",
        "description": "Analisa a descrição do leilão para extrair informação relevante",
        "template": """Analisa esta descrição de um veículo em leilão e extrai informação relevante:

TÍTULO: {titulo}
DESCRIÇÃO: {descricao}

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO (sem texto adicional):
{{
    "estado_mencionado": "desconhecido|mau|razoavel|bom|excelente",
    "quilometragem": número ou null se não mencionada,
    "alertas": ["lista de alertas ou problemas mencionados"],
    "pontos_positivos": ["lista de pontos positivos mencionados"],
    "informacao_em_falta": ["informação importante que falta na descrição"]
}}

Sê objetivo e baseado apenas no texto fornecido.""",
        "default_output": {
            "estado_mencionado": "desconhecido",
            "quilometragem": None,
            "alertas": [],
            "pontos_positivos": [],
            "informacao_em_falta": ["Quilometragem", "Histórico de manutenção", "Estado geral"]
        }
    },
    {
        "id": "market_position",
        "name": "Posição no Mercado",
        "description": "Avalia a facilidade de revenda e posição no mercado",
        "template": """Para um {marca} {modelo} de {ano} em Portugal:
- Combustível: {combustivel}
- Potência: {potencia}cv

Avalia a posição deste veículo no mercado português atual.

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO (sem texto adicional):
{{
    "facilidade_revenda": "dificil|media|facil",
    "publico_alvo": "descrição curta de quem compra este carro",
    "tempo_medio_venda_dias": número estimado,
    "fatores_positivos_revenda": ["máximo 3 fatores"],
    "fatores_negativos_revenda": ["máximo 3 fatores"],
    "tendencia_mercado": "descendo|estavel|subindo"
}}""",
        "default_output": {
            "facilidade_revenda": "media",
            "publico_alvo": "Público geral",
            "tempo_medio_venda_dias": 60,
            "fatores_positivos_revenda": [],
            "fatores_negativos_revenda": [],
            "tendencia_mercado": "estavel"
        }
    },
    {
        "id": "risk_assessment",
        "name": "Avaliação de Risco",
        "description": "Avalia os riscos de comprar este veículo em leilão",
        "template": """Avalia os riscos de comprar este veículo em leilão judicial:

Veículo: {marca} {modelo} ({ano})
Valor base: {valor_base}€
Lance atual: {lance_atual}€
Tem seguro: {tem_seguro}
Descrição: {descricao_curta}

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO (sem texto adicional):
{{
    "riscos": [
        {{
            "risco": "descrição do risco",
            "gravidade": "baixa|media|alta",
            "mitigacao": "como mitigar este risco"
        }}
    ],
    "documentos_verificar": ["lista de documentos a verificar antes de licitar"],
    "score_risco": número de 0 a 10 (0=sem risco, 10=muito arriscado)
}}

Máximo 4 riscos mais importantes.""",
        "default_output": {
            "riscos": [],
            "documentos_verificar": ["DUA", "Livro de revisões", "Histórico de proprietários"],
            "score_risco": 5
        }
    },
    {
        "id": "cost_estimation",
        "name": "Estimativa de Custos",
        "description": "Estima custos totais de aquisição",
        "template": """Estima os custos totais para adquirir este veículo em leilão:

Veículo: {marca} {modelo} ({ano}, {combustivel})
Lance atual: {lance_atual}€

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO (sem texto adicional):
{{
    "custos": {{
        "lance": {lance_atual},
        "comissao_leilao_percentagem": 10,
        "comissao_leilao_valor": número,
        "transferencia": 250,
        "iuc_anual_estimado": número,
        "inspecao": 30,
        "eventuais_reparacoes": número estimado
    }},
    "custo_total_estimado": número,
    "preco_revenda_minimo_lucro": número para ter lucro mínimo
}}

Considera valores típicos em Portugal.""",
        "default_output": {
            "custos": {
                "lance": 0,
                "comissao_leilao_percentagem": 10,
                "comissao_leilao_valor": 0,
                "transferencia": 250,
                "iuc_anual_estimado": 150,
                "inspecao": 30,
                "eventuais_reparacoes": 500
            },
            "custo_total_estimado": 0,
            "preco_revenda_minimo_lucro": 0
        }
    },
    # NOTE: final_recommendation is now calculated programmatically
    # See _calculate_investment_analysis() method
]


# =============================================================================
# INVESTMENT ANALYSIS - PROGRAMMATIC CALCULATIONS (NOT AI)
# =============================================================================

def calculate_investment_analysis(
    vehicle_data: Dict[str, Any],
    market_price: Optional[float] = None,
    market_price_min: Optional[float] = None,
    market_listings: Optional[List[Dict]] = None,
    problemas_conhecidos: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Calculate investment analysis using HARD RULES - no AI hallucinations.

    This function determines recommendation based on:
    1. KM thresholds (hard limits)
    2. KM/year usage (15k-20k normal, >30k heavy use)
    3. Price vs market comparison (uses valor_minimo, not valor_base)
    4. KM comparison with market listings
    5. Known issues from description
    """
    # Extract data
    km_raw = vehicle_data.get("quilometros") or vehicle_data.get("km")
    try:
        km = int(str(km_raw).replace(".", "").replace(",", "").replace(" ", "")) if km_raw else None
    except (ValueError, TypeError):
        km = None

    # IMPORTANT: Use valor_minimo for pricing (not valor_base)
    # - In LO (Leilão Online): valor_minimo is the minimum mandatory bid
    # - In NP (Negociação Particular): there's negotiation room
    valor_base = float(vehicle_data.get("valor_base") or 0)
    valor_minimo = float(vehicle_data.get("valor_minimo") or valor_base)
    lance_atual = float(vehicle_data.get("lance_atual") or valor_minimo)

    # Use valor_minimo as reference price (what you'll actually pay minimum)
    preco_leilao = lance_atual if lance_atual > valor_minimo else valor_minimo

    ano_raw = vehicle_data.get("ano")
    try:
        ano = int(ano_raw) if ano_raw else None
    except (ValueError, TypeError):
        ano = None

    marca = vehicle_data.get("marca", "").upper()
    modelo = vehicle_data.get("modelo", "")
    combustivel = vehicle_data.get("combustivel", "")

    # Initialize scores and flags
    red_flags = []
    cons = []
    pros = []

    # Calculate age
    current_year = 2026
    idade = current_year - ano if ano else None

    # =================================================================
    # KM ANALYSIS - ABSOLUTE + ANNUAL USAGE
    # Portugal average: 15,000-20,000 km/year
    # >30,000 km/year = heavy use (taxi, commercial)
    # =================================================================
    km_score = 10  # Start with perfect score
    km_status = "desconhecido"
    km_medio_esperado = None
    km_por_ano = None
    km_uso_classificacao = None

    if km is not None and idade and idade > 0:
        # Calculate km/year (important indicator of use intensity)
        km_por_ano = round(km / idade)
        km_medio_esperado = idade * 15000  # Expected based on 15k/year average

        # Classify annual usage (source: Portuguese car market standards)
        if km_por_ano < 10000:
            km_uso_classificacao = "uso_reduzido"  # Weekend car, garage kept
            pros.append(f"Uso reduzido ({km_por_ano:,} km/ano) - bem conservado")
        elif km_por_ano <= 20000:
            km_uso_classificacao = "uso_normal"  # Normal daily use
        elif km_por_ano <= 30000:
            km_uso_classificacao = "uso_intensivo"  # Intensive use
            cons.append(f"Uso intensivo ({km_por_ano:,} km/ano)")
        else:
            km_uso_classificacao = "uso_profissional"  # Taxi, commercial
            red_flags.append(f"🟠 Uso profissional ({km_por_ano:,} km/ano) - desgaste acelerado")
            cons.append(f"Uso muito intensivo ({km_por_ano:,} km/ano) - possível táxi/comercial")

    elif km is not None:
        # No age info, use absolute thresholds only
        km_medio_esperado = None

    # ABSOLUTE KM thresholds (regardless of age)
    if km is not None:
        if km > 400000:
            km_score = 0
            km_status = "critico"
            red_flags.append(f"⛔ {km:,} km - Quilometragem CRÍTICA, fim de vida útil")
            cons.append(f"Quilometragem extremamente elevada ({km:,} km)")
        elif km > 300000:
            km_score = 2
            km_status = "muito_alto"
            red_flags.append(f"🔴 {km:,} km - Quilometragem MUITO ALTA, revenda impossível")
            cons.append(f"Quilometragem muito elevada ({km:,} km)")
        elif km > 200000:
            km_score = 4
            km_status = "alto"
            red_flags.append(f"🟠 {km:,} km - Quilometragem elevada, revenda difícil")
            cons.append(f"Quilometragem elevada ({km:,} km)")
        elif km > 150000:
            km_score = 6
            km_status = "acima_media"
            cons.append(f"Quilometragem acima da média ({km:,} km)")
        elif km > 100000:
            km_score = 8
            km_status = "normal"
            # Only add as pro if below expected for age
            if km_medio_esperado and km < km_medio_esperado * 0.9:
                pros.append(f"Quilometragem abaixo da média para a idade ({km:,} km)")
        else:
            km_score = 10
            km_status = "baixo"
            pros.append(f"Quilometragem baixa ({km:,} km)")

        # Adjust score based on annual usage intensity
        if km_uso_classificacao == "uso_profissional":
            km_score = max(0, km_score - 2)
        elif km_uso_classificacao == "uso_intensivo":
            km_score = max(0, km_score - 1)
        elif km_uso_classificacao == "uso_reduzido":
            km_score = min(10, km_score + 1)
    else:
        red_flags.append("⚠️ Quilometragem desconhecida - RISCO ELEVADO")
        km_score = 3

    # =================================================================
    # PRICE vs MARKET ANALYSIS
    # =================================================================
    price_score = 5  # Default neutral
    desconto_mercado = 0
    margem_lucro = 0

    # Calculate total acquisition cost (Portugal)
    comissao_leilao = preco_leilao * 0.10  # 10% commission
    custos_transferencia = 250
    custos_inspecao = 30
    custo_reparacoes_estimado = 500 if km and km > 200000 else 300

    custo_total = preco_leilao + comissao_leilao + custos_transferencia + custos_inspecao + custo_reparacoes_estimado

    if market_price and market_price > 0:
        desconto_mercado = round(((market_price - custo_total) / market_price) * 100, 1)
        margem_lucro = market_price - custo_total

        if desconto_mercado > 40:
            price_score = 10
            pros.append(f"Desconto de {desconto_mercado}% vs mercado")
        elif desconto_mercado > 25:
            price_score = 8
            pros.append(f"Bom desconto de {desconto_mercado}% vs mercado")
        elif desconto_mercado > 10:
            price_score = 6
        elif desconto_mercado > 0:
            price_score = 4
        else:
            price_score = 2
            cons.append(f"Preço total ({custo_total:,.0f}€) acima do mercado ({market_price:,.0f}€)")

    # =================================================================
    # COMPARE WITH MARKET LISTINGS (KM comparison)
    # =================================================================
    market_comparison = None
    better_options_count = 0

    if market_listings and km:
        for listing in market_listings:
            listing_km = listing.get('km')
            listing_price = listing.get('preco') or listing.get('price')

            if listing_km and listing_price:
                try:
                    l_km = int(str(listing_km).replace(".", "").replace(",", "").replace(" ", ""))
                    l_price = float(str(listing_price).replace(".", "").replace(",", ".").replace("€", "").replace(" ", ""))

                    # If market has LESS km for similar or lower price = bad for auction
                    if l_km < km and l_price <= custo_total * 1.1:
                        better_options_count += 1

                    # If market has HALF the km for same price = very bad
                    if l_km < km * 0.6 and l_price <= custo_total * 1.05:
                        if not market_comparison:
                            market_comparison = f"Existem carros no mercado com {l_km:,} km por {l_price:,.0f}€"
                            red_flags.append(f"❌ Mercado tem opções com metade dos km pelo mesmo preço")
                except (ValueError, TypeError):
                    continue

    if better_options_count >= 2:
        price_score = max(0, price_score - 3)
        cons.append(f"{better_options_count} opções melhores disponíveis no mercado")

    # =================================================================
    # KNOWN ISSUES PENALTY
    # =================================================================
    issues_penalty = 0
    if problemas_conhecidos:
        high_severity = sum(1 for p in problemas_conhecidos if p.get('gravidade') == 'alta')
        medium_severity = sum(1 for p in problemas_conhecidos if p.get('gravidade') == 'media')

        issues_penalty = high_severity * 2 + medium_severity * 1

        if high_severity > 0:
            red_flags.append(f"🔴 {high_severity} problemas graves mencionados na descrição")
        if medium_severity > 0:
            cons.append(f"{medium_severity} problemas médios mencionados")

    # =================================================================
    # FINAL SCORE & RECOMMENDATION (HARD RULES)
    # =================================================================

    # Weighted score calculation
    score_oportunidade = round((price_score * 0.6 + km_score * 0.4), 1)
    score_risco = round(10 - (len(red_flags) * 2 + issues_penalty), 1)
    score_risco = max(0, min(10, score_risco))

    # Liquidity based on brand/model popularity in Portugal
    popular_brands = ["VOLKSWAGEN", "PEUGEOT", "RENAULT", "BMW", "MERCEDES", "AUDI", "TOYOTA", "SEAT"]
    score_liquidez = 7 if marca in popular_brands else 5
    if km and km > 200000:
        score_liquidez = max(2, score_liquidez - 3)

    # Final score
    score_final = round((score_oportunidade * 0.4 + (10 - score_risco) * 0.3 + score_liquidez * 0.3), 1)
    score_final = max(0, min(10, score_final))

    # =================================================================
    # SUMMARY - Data-based, no recommendation (user preference)
    # Recommendation will be based on scores threshold later
    # =================================================================
    recomendacao = None  # Disabled for now - user wants data-driven approach

    # Build factual summary
    resumo_parts = []

    if km:
        if km > 300000:
            resumo_parts.append(f"KM crítico: {km:,}")
        elif km > 200000:
            resumo_parts.append(f"KM elevado: {km:,}")
        elif km > 150000:
            resumo_parts.append(f"KM: {km:,}")
        else:
            resumo_parts.append(f"KM: {km:,}")

        if km_por_ano:
            resumo_parts.append(f"({km_por_ano:,}/ano)")
    else:
        resumo_parts.append("KM: desconhecido")

    if market_price:
        resumo_parts.append(f"Desconto: {desconto_mercado}%")
        resumo_parts.append(f"Margem: {margem_lucro:,.0f}€")

    if better_options_count > 0:
        resumo_parts.append(f"Alternativas mercado: {better_options_count}")

    resumo = " | ".join(resumo_parts)

    if len(red_flags) > 0:
        resumo += f" | ⚠️ {len(red_flags)} alertas"

    # Lance máximo sugerido (to get 20% margin)
    lance_maximo = None
    if market_price and market_price > 0:
        margem_desejada = 0.20  # 20% profit margin
        lance_maximo = (market_price * (1 - margem_desejada)) - comissao_leilao - custos_transferencia - custos_inspecao - custo_reparacoes_estimado
        lance_maximo = max(0, round(lance_maximo, 0))

    # Checklist
    checklist = [
        "Verificar histórico de manutenção se disponível",
        "Pesquisar problemas comuns deste modelo",
        "Confirmar valor real de mercado em StandVirtual",
    ]
    if km and km > 150000:
        checklist.append("Orçamentar substituição da correia de distribuição")
    if not km:
        checklist.insert(0, "⚠️ VERIFICAR QUILOMETRAGEM - não disponível no anúncio")

    return {
        "scores": {
            "oportunidade": score_oportunidade,
            "risco": score_risco,
            "liquidez": score_liquidez,
            "final": score_final
        },
        "recomendacao": recomendacao,
        "resumo": resumo,
        "lance_maximo_sugerido": lance_maximo,
        "pros": pros[:5],
        "cons": cons[:5],
        "red_flags": red_flags,
        "checklist_antes_licitar": checklist,
        "custos": {
            "preco_leilao": preco_leilao,
            "comissao_leilao": comissao_leilao,
            "transferencia": custos_transferencia,
            "inspecao": custos_inspecao,
            "reparacoes_estimadas": custo_reparacoes_estimado,
            "custo_total": custo_total
        },
        "mercado": {
            "preco_medio": market_price,
            "preco_minimo": market_price_min,
            "desconto_percentagem": desconto_mercado,
            "margem_lucro_estimada": margem_lucro,
            "opcoes_melhores": better_options_count
        },
        "km_analysis": {
            "km": km,
            "km_status": km_status,
            "km_esperado_idade": km_medio_esperado,
            "km_por_ano": km_por_ano,
            "km_uso_classificacao": km_uso_classificacao,
            "km_score": km_score
        },
        "leilao": {
            "valor_base": valor_base,
            "valor_minimo": valor_minimo,
            "lance_atual": lance_atual,
            "preco_referencia": preco_leilao  # The actual price to use for calculations
        }
    }


class AIQuestionsService:
    """
    Service for asking structured questions to the AI.

    Each question has a fixed JSON output schema to ensure consistent responses.
    """

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model

    async def analyze_vehicle(
        self,
        vehicle_data: Dict[str, Any],
        market_price: Optional[float] = None,
        market_price_min: Optional[float] = None,
        market_listings: Optional[List[Dict]] = None,
        skip_questions: Optional[List[str]] = None
    ) -> VehicleAnalysisResult:
        """
        Run complete vehicle analysis with all questions.

        Args:
            vehicle_data: Dict with vehicle info (marca, modelo, ano, quilometros, etc.)
            market_price: Average market price for comparison
            market_price_min: Minimum market price for comparison
            market_listings: List of similar vehicles on market with km and price
            skip_questions: List of question IDs to skip

        Returns:
            VehicleAnalysisResult with all analysis data
        """
        from services.ollama_service import OllamaService

        ollama = OllamaService()
        skip_questions = skip_questions or []

        result = VehicleAnalysisResult()
        result.model_used = self.model
        start_time = datetime.now()

        # Prepare base context with market data for comparison
        context = self._prepare_context(vehicle_data, market_price, market_price_min, market_listings)

        # Track intermediate results for final recommendation
        problemas_conhecidos = []
        analise_descricao = {}

        # Run questions sequentially (some depend on previous results)
        for question in QUESTIONS:
            if question["id"] in skip_questions:
                continue

            # Skip final recommendation until we have other results
            if question["id"] == "final_recommendation":
                continue

            log_info(f"Running AI question: {question['name']}")

            q_result = await self._ask_question(
                ollama=ollama,
                question=question,
                context=context
            )

            result.question_results.append(q_result)

            # Store results for final recommendation
            if q_result.success:
                if question["id"] == "known_issues":
                    problemas_conhecidos = q_result.answer.get("problemas", [])
                    result.problemas_conhecidos = problemas_conhecidos
                elif question["id"] == "description_analysis":
                    analise_descricao = q_result.answer
                    result.red_flags.extend(q_result.answer.get("alertas", []))
                elif question["id"] == "risk_assessment":
                    result.score_risco = q_result.answer.get("score_risco", 5)
                elif question["id"] == "cost_estimation":
                    costs = q_result.answer.get("custos", {})
                    result.pros.append(f"Custo total estimado: {q_result.answer.get('custo_total_estimado', 0)}€")

        # IMPORTANT: Use PROGRAMMATIC calculation for final recommendation
        # This avoids AI hallucinations like "Peugeot é ponto forte"
        if "final_recommendation" not in skip_questions:
            log_info("Calculating investment analysis (programmatic - no AI)")

            # Run programmatic investment analysis
            investment_analysis = calculate_investment_analysis(
                vehicle_data=vehicle_data,
                market_price=market_price,
                market_price_min=market_price_min,
                market_listings=market_listings,
                problemas_conhecidos=problemas_conhecidos
            )

            # Apply results to VehicleAnalysisResult
            scores = investment_analysis.get("scores", {})
            result.score_oportunidade = scores.get("oportunidade", 5)
            result.score_risco = scores.get("risco", 5)
            result.score_liquidez = scores.get("liquidez", 5)
            result.score_final = scores.get("final", 5)

            result.recomendacao = investment_analysis.get("recomendacao", "cautela")
            result.resumo = investment_analysis.get("resumo", "")
            result.lance_maximo_sugerido = investment_analysis.get("lance_maximo_sugerido")

            # Merge pros/cons/red_flags (keeping any from AI description analysis)
            result.pros = investment_analysis.get("pros", [])
            result.cons = investment_analysis.get("cons", [])
            result.red_flags.extend(investment_analysis.get("red_flags", []))
            result.checklist = investment_analysis.get("checklist_antes_licitar", [])

            # Store additional investment data for the result
            result.investment_analysis = investment_analysis

        # Calculate totals
        result.total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    def _prepare_context(
        self,
        vehicle_data: Dict[str, Any],
        market_price: Optional[float] = None,
        market_price_min: Optional[float] = None,
        market_listings: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Prepare context dict for question templates"""
        valor_base = vehicle_data.get("valor_base") or 0
        lance_atual = vehicle_data.get("lance_atual") or valor_base

        # Calculate discount vs market price
        desconto = 0
        if market_price and valor_base and market_price > 0:
            desconto = round(((market_price - valor_base) / market_price) * 100, 1)

        descricao = vehicle_data.get("descricao") or "Sem descrição disponível"
        descricao_curta = descricao[:500] + "..." if len(descricao) > 500 else descricao

        # Format market listings for AI context
        listings_text = "Sem anúncios disponíveis para comparação"
        if market_listings and len(market_listings) > 0:
            listings_parts = []
            for i, listing in enumerate(market_listings[:5], 1):  # Top 5 listings
                km = listing.get('km', 'N/A')
                price = listing.get('preco', listing.get('price', 'N/A'))
                year = listing.get('ano', listing.get('year', 'N/A'))
                title = listing.get('titulo', listing.get('title', ''))[:50]
                listings_parts.append(f"{i}. {title} - {year}, {km} km, {price}€")
            listings_text = "\n".join(listings_parts)

        # Get quilometros
        quilometros = vehicle_data.get("quilometros") or vehicle_data.get("km") or "Desconhecido"

        return {
            "marca": vehicle_data.get("marca") or "Desconhecida",
            "modelo": vehicle_data.get("modelo") or "Desconhecido",
            "versao": vehicle_data.get("versao") or "",
            "ano": vehicle_data.get("ano") or "Desconhecido",
            "combustivel": vehicle_data.get("combustivel") or "Desconhecido",
            "potencia": vehicle_data.get("potencia_cv") or "Desconhecida",
            "quilometros": quilometros,
            "titulo": vehicle_data.get("titulo") or "",
            "descricao": descricao,
            "descricao_curta": descricao_curta,
            "valor_base": valor_base,
            "lance_atual": lance_atual,
            "desconto_percentagem": desconto,
            "preco_mercado": market_price or "Desconhecido",
            "preco_mercado_min": market_price_min or "Desconhecido",
            "market_listings": listings_text,
            "tem_seguro": "Sim" if vehicle_data.get("tem_seguro") else "Não/Desconhecido",
        }

    async def _ask_question(
        self,
        ollama,
        question: Dict[str, Any],
        context: Dict[str, Any]
    ) -> QuestionResult:
        """Ask a single question and parse the response"""
        import time

        start_time = time.time()

        # Format the question template with context
        try:
            formatted_question = question["template"].format(**context)
        except KeyError as e:
            return QuestionResult(
                question_id=question["id"],
                question=question["template"],
                answer=question["default_output"],
                raw_answer="",
                confidence=0,
                time_ms=0,
                success=False,
                error=f"Missing context key: {e}"
            )

        try:
            response = await ollama.generate(
                prompt=formatted_question,
                model=self.model,
                temperature=0.2  # Low temperature for more consistent outputs
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            if not response or "error" in response:
                return QuestionResult(
                    question_id=question["id"],
                    question=formatted_question,
                    answer=question["default_output"],
                    raw_answer="",
                    confidence=0,
                    time_ms=elapsed_ms,
                    success=False,
                    error=response.get("error", "Unknown error") if response else "No response"
                )

            raw_answer = response.get("response", "")

            # Try to extract and parse JSON
            parsed_answer = self._extract_json(raw_answer, question["default_output"])

            # Calculate confidence based on how well the response matches expected schema
            confidence = self._calculate_confidence(parsed_answer, question["default_output"])

            return QuestionResult(
                question_id=question["id"],
                question=formatted_question,
                answer=parsed_answer,
                raw_answer=raw_answer,
                confidence=confidence,
                time_ms=elapsed_ms,
                success=True
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            log_error(f"Question {question['id']} failed: {e}")

            return QuestionResult(
                question_id=question["id"],
                question=formatted_question,
                answer=question["default_output"],
                raw_answer="",
                confidence=0,
                time_ms=elapsed_ms,
                success=False,
                error=str(e)
            )

    def _extract_json(self, text: str, default: Dict[str, Any]) -> Dict[str, Any]:
        """Extract JSON from AI response text"""
        # Try to find JSON block
        json_patterns = [
            r'```json\s*(.*?)\s*```',  # Markdown code block
            r'```\s*(.*?)\s*```',       # Generic code block
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested JSON
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    # Clean the match
                    clean = match.strip()
                    if not clean.startswith('{'):
                        # Look for JSON object in the match
                        json_start = clean.find('{')
                        if json_start >= 0:
                            clean = clean[json_start:]

                    parsed = json.loads(clean)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        # Last resort: try to parse entire text as JSON
        try:
            # Find first { and last }
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                potential_json = text[start:end + 1]
                return json.loads(potential_json)
        except json.JSONDecodeError:
            pass

        log_warning(f"Could not extract JSON from response, using default")
        return default

    def _calculate_confidence(self, answer: Dict[str, Any], schema: Dict[str, Any]) -> float:
        """Calculate confidence score based on schema matching"""
        if not answer or answer == schema:
            return 0.3  # Low confidence if using default

        # Count matching keys
        schema_keys = set(schema.keys())
        answer_keys = set(answer.keys())

        matching = len(schema_keys.intersection(answer_keys))
        total = len(schema_keys)

        if total == 0:
            return 0.5

        # Base confidence from key matching
        confidence = (matching / total) * 0.7

        # Bonus for having actual values (not None or empty)
        non_empty = sum(1 for v in answer.values() if v is not None and v != "" and v != [])
        if len(answer) > 0:
            confidence += (non_empty / len(answer)) * 0.3

        return round(min(confidence, 1.0), 2)


# Singleton instance
_ai_questions_service: Optional[AIQuestionsService] = None


def get_ai_questions_service(model: str = "llama3.1:8b") -> AIQuestionsService:
    """Get singleton instance of AIQuestionsService"""
    global _ai_questions_service
    if _ai_questions_service is None or _ai_questions_service.model != model:
        _ai_questions_service = AIQuestionsService(model=model)
    return _ai_questions_service
