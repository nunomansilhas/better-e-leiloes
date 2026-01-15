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
    {
        "id": "final_recommendation",
        "name": "Recomendação Final",
        "description": "Gera a recomendação final com scores e checklist",
        "template": """Com base nestes dados do veículo em leilão:

VEÍCULO: {marca} {modelo} ({ano}, {combustivel})
VALOR BASE: {valor_base}€
LANCE ATUAL: {lance_atual}€
DESCONTO ATUAL: {desconto_percentagem}%
PREÇO MERCADO ESTIMADO: {preco_mercado}€
TEM SEGURO: {tem_seguro}

PROBLEMAS MENCIONADOS NA DESCRIÇÃO:
{problemas_conhecidos}

ANÁLISE ADICIONAL DA DESCRIÇÃO:
{analise_descricao}

Dá a tua recomendação final.

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO (sem texto adicional):
{{
    "scores": {{
        "oportunidade": número 0-10,
        "risco": número 0-10,
        "liquidez": número 0-10,
        "final": número 0-10
    }},
    "recomendacao": "evitar|cautela|considerar|comprar|excelente",
    "resumo": "2-3 frases resumindo a análise",
    "lance_maximo_sugerido": número em euros,
    "pros": ["máximo 5 pontos positivos"],
    "cons": ["máximo 5 pontos negativos"],
    "red_flags": ["alertas críticos se existirem"],
    "checklist_antes_licitar": [
        "ação 1 a fazer antes de licitar",
        "ação 2",
        "..."
    ]
}}

Sê objetivo e conservador nas recomendações.""",
        "default_output": {
            "scores": {
                "oportunidade": 5,
                "risco": 5,
                "liquidez": 5,
                "final": 5
            },
            "recomendacao": "cautela",
            "resumo": "Análise inconclusiva. Recomenda-se cautela.",
            "lance_maximo_sugerido": None,
            "pros": [],
            "cons": [],
            "red_flags": [],
            "checklist_antes_licitar": [
                "Verificar fotos do veículo",
                "Pesquisar problemas comuns do modelo",
                "Definir lance máximo"
            ]
        }
    }
]


class AIQuestionsService:
    """
    Service for asking structured questions to the AI.

    Each question has a fixed JSON output schema to ensure consistent responses.
    """

    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model

    async def analyze_vehicle(
        self,
        vehicle_data: Dict[str, Any],
        market_price: Optional[float] = None,
        skip_questions: Optional[List[str]] = None
    ) -> VehicleAnalysisResult:
        """
        Run complete vehicle analysis with all questions.

        Args:
            vehicle_data: Dict with vehicle info (marca, modelo, ano, etc.)
            market_price: Optional market price for comparison
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

        # Prepare base context
        context = self._prepare_context(vehicle_data, market_price)

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

        # Now run final recommendation with all context
        if "final_recommendation" not in skip_questions:
            final_context = context.copy()
            final_context["problemas_conhecidos"] = json.dumps(problemas_conhecidos, ensure_ascii=False)
            final_context["analise_descricao"] = json.dumps(analise_descricao, ensure_ascii=False)

            final_question = next(q for q in QUESTIONS if q["id"] == "final_recommendation")
            final_result = await self._ask_question(
                ollama=ollama,
                question=final_question,
                context=final_context
            )

            result.question_results.append(final_result)

            if final_result.success:
                scores = final_result.answer.get("scores", {})
                result.score_oportunidade = scores.get("oportunidade", 5)
                result.score_risco = scores.get("risco", 5)
                result.score_liquidez = scores.get("liquidez", 5)
                result.score_final = scores.get("final", 5)

                result.recomendacao = final_result.answer.get("recomendacao", "cautela")
                result.resumo = final_result.answer.get("resumo", "")
                result.lance_maximo_sugerido = final_result.answer.get("lance_maximo_sugerido")

                result.pros = final_result.answer.get("pros", [])
                result.cons = final_result.answer.get("cons", [])
                result.red_flags.extend(final_result.answer.get("red_flags", []))
                result.checklist = final_result.answer.get("checklist_antes_licitar", [])

        # Calculate totals
        result.total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    def _prepare_context(
        self,
        vehicle_data: Dict[str, Any],
        market_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Prepare context dict for question templates"""
        valor_base = vehicle_data.get("valor_base") or 0
        lance_atual = vehicle_data.get("lance_atual") or valor_base

        # Calculate discount
        desconto = 0
        if valor_base and lance_atual and valor_base > 0:
            desconto = round(((valor_base - lance_atual) / valor_base) * 100, 1)

        descricao = vehicle_data.get("descricao") or "Sem descrição disponível"
        descricao_curta = descricao[:500] + "..." if len(descricao) > 500 else descricao

        return {
            "marca": vehicle_data.get("marca") or "Desconhecida",
            "modelo": vehicle_data.get("modelo") or "Desconhecido",
            "versao": vehicle_data.get("versao") or "",
            "ano": vehicle_data.get("ano") or "Desconhecido",
            "combustivel": vehicle_data.get("combustivel") or "Desconhecido",
            "potencia": vehicle_data.get("potencia_cv") or "Desconhecida",
            "titulo": vehicle_data.get("titulo") or "",
            "descricao": descricao,
            "descricao_curta": descricao_curta,
            "valor_base": valor_base,
            "lance_atual": lance_atual,
            "desconto_percentagem": desconto,
            "preco_mercado": market_price or "Desconhecido",
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


def get_ai_questions_service(model: str = "llama3.2:3b") -> AIQuestionsService:
    """Get singleton instance of AIQuestionsService"""
    global _ai_questions_service
    if _ai_questions_service is None or _ai_questions_service.model != model:
        _ai_questions_service = AIQuestionsService(model=model)
    return _ai_questions_service
