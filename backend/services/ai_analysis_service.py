"""
Enhanced AI Analysis Service for E-Leiloes
Uses batch questions, image analysis (LLaVA), and market data integration.
"""

import httpx
import json
import os
import time
import base64
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from .vehicle_lookup import decode_portuguese_plate, extract_vehicle_from_title

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")  # or llava:34b
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))


@dataclass
class QuestionResult:
    """Result from a single AI question"""
    question_id: str
    question: str
    answer: str
    confidence: float
    tokens_used: int
    time_ms: int


@dataclass
class ImageAnalysis:
    """Result from image analysis"""
    image_url: str
    description: str
    condition: str  # 'excellent', 'good', 'fair', 'poor', 'unknown'
    issues_found: List[str]
    confidence: float


@dataclass
class MarketComparison:
    """Market price comparison data"""
    source: str
    num_comparables: int
    price_min: float
    price_max: float
    price_avg: float
    price_median: float
    auction_price: float
    discount_percent: float  # negative = below market, positive = above
    verdict: str  # 'great_deal', 'good_deal', 'fair', 'overpriced'


@dataclass
class DetailedAnalysis:
    """Complete detailed analysis result"""
    reference: str
    tipo: str

    # Basic info extracted
    vehicle_info: Optional[Dict[str, Any]] = None  # marca, modelo, ano
    plate_info: Optional[Dict[str, Any]] = None    # decoded plate

    # Batch question answers
    questions: List[QuestionResult] = field(default_factory=list)

    # Image analysis
    image_analyses: List[ImageAnalysis] = field(default_factory=list)

    # Market comparison
    market_data: Optional[MarketComparison] = None

    # Final verdict
    score: float = 0.0  # 1-10
    recommendation: str = "watch"  # buy, watch, skip
    summary: str = ""
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)

    # Metadata
    total_time_ms: int = 0
    total_tokens: int = 0
    models_used: List[str] = field(default_factory=list)


class EnhancedAIAnalysisService:
    """
    Enhanced AI analysis with:
    - Batch questions (focused, specific questions)
    - Image analysis using LLaVA
    - Market data integration
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        text_model: str = OLLAMA_TEXT_MODEL,
        vision_model: str = OLLAMA_VISION_MODEL
    ):
        self.base_url = base_url.rstrip('/')
        self.text_model = text_model
        self.vision_model = vision_model
        self.timeout = OLLAMA_TIMEOUT

    async def check_models(self) -> Dict[str, Any]:
        """Check available models"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return {"error": "Ollama not responding"}

                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                return {
                    "available_models": models,
                    "text_model": self.text_model,
                    "text_model_available": any(self.text_model in m for m in models),
                    "vision_model": self.vision_model,
                    "vision_model_available": any(self.vision_model in m for m in models),
                }
        except Exception as e:
            return {"error": str(e)}

    async def _ask_question(self, prompt: str, model: str = None) -> Dict[str, Any]:
        """Ask a single question to Ollama"""
        model = model or self.text_model
        start_time = time.time()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 512,
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")

            data = response.json()

        return {
            "response": data.get("response", ""),
            "tokens": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            "time_ms": int((time.time() - start_time) * 1000)
        }

    async def _analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """Analyze an image using LLaVA"""
        start_time = time.time()

        # Download image and convert to base64
        # Note: verify=False needed for e-leiloes.pt SSL certificate issues
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            img_response = await client.get(image_url)
            if img_response.status_code != 200:
                return {"error": f"Failed to download image: {img_response.status_code}"}

            image_base64 = base64.b64encode(img_response.content).decode('utf-8')

        # Send to LLaVA
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 512,
                    }
                }
            )

            if response.status_code != 200:
                return {"error": f"LLaVA error: {response.status_code}"}

            data = response.json()

        return {
            "response": data.get("response", ""),
            "tokens": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            "time_ms": int((time.time() - start_time) * 1000)
        }

    # ========== VEHICLE QUESTIONS ==========

    def _get_vehicle_questions(self, event: Dict[str, Any], plate_info: Dict, vehicle_info: Dict) -> List[Dict]:
        """Get batch questions for vehicle analysis"""
        titulo = event.get('titulo', '')
        matricula = event.get('matricula', 'N/A')
        valor_base = event.get('valor_base', 0)
        descricao = event.get('descricao', '')[:300] or 'Sem descrição'

        marca = vehicle_info.get('marca', 'Desconhecida')
        modelo = vehicle_info.get('modelo', 'Desconhecido')
        ano_min = plate_info.get('year_min', 2000)
        ano_max = plate_info.get('year_max', 2024)

        return [
            {
                "id": "vehicle_identification",
                "question": f"""Identifica este veículo:
Título: {titulo}
Matrícula: {matricula} (formato indica ano entre {ano_min}-{ano_max})

Responde APENAS em JSON:
{{"marca": "...", "modelo": "...", "ano_provavel": 2020, "motorizacao": "...", "combustivel": "diesel/gasolina/híbrido/elétrico"}}"""
            },
            {
                "id": "market_value",
                "question": f"""Para um {marca} {modelo} de aproximadamente {ano_min}-{ano_max} em Portugal:
- Qual o valor médio de mercado em segunda mão?
- O preço de leilão de {valor_base}€ está acima ou abaixo do mercado?

Responde APENAS em JSON:
{{"valor_mercado_estimado": 15000, "preco_leilao": {valor_base}, "desconto_percentual": -20, "avaliacao": "bom_negocio/negocio_justo/caro"}}"""
            },
            {
                "id": "condition_from_description",
                "question": f"""Analisa a descrição deste veículo e avalia o estado:
"{descricao}"

Responde APENAS em JSON:
{{"estado_geral": "excelente/bom/razoavel/mau/desconhecido", "quilometragem_mencionada": null, "problemas_mencionados": [], "pontos_positivos": []}}"""
            },
            {
                "id": "auction_risks",
                "question": f"""Quais são os riscos específicos de comprar um veículo ({marca} {modelo}) em leilão judicial em Portugal?

Lista os 3 principais riscos e como mitigá-los.

Responde APENAS em JSON:
{{"riscos": [{{"risco": "...", "gravidade": "alta/media/baixa", "mitigacao": "..."}}], "documentos_verificar": []}}"""
            },
            {
                "id": "final_recommendation",
                "question": f"""Com base nestes dados de um {marca} {modelo} ({ano_min}-{ano_max}):
- Preço leilão: {valor_base}€
- Descrição: {descricao[:200]}

Dá uma recomendação final.

Responde APENAS em JSON:
{{"score": 7.5, "recomendacao": "comprar/acompanhar/evitar", "resumo": "Frase curta de recomendação", "pros": ["...", "..."], "cons": ["...", "..."]}}"""
            }
        ]

    # ========== PROPERTY QUESTIONS ==========

    def _get_property_questions(self, event: Dict[str, Any]) -> List[Dict]:
        """Get batch questions for property analysis"""
        titulo = event.get('titulo', '')
        subtipo = event.get('subtipo', 'Imóvel')
        tipologia = event.get('tipologia', 'N/A')
        distrito = event.get('distrito', 'N/A')
        concelho = event.get('concelho', 'N/A')
        freguesia = event.get('freguesia', 'N/A')
        valor_base = event.get('valor_base', 0)
        area_total = event.get('area_total') or event.get('area_privativa') or 0
        descricao = event.get('descricao', '')[:400] or 'Sem descrição'

        # Calculate price per m2
        preco_m2 = valor_base / area_total if area_total > 0 else 0

        return [
            {
                "id": "location_analysis",
                "question": f"""Analisa a localização deste imóvel em Portugal:
- Freguesia: {freguesia}
- Concelho: {concelho}
- Distrito: {distrito}

Avalia: qualidade da zona, acessibilidades, serviços, potencial.

Responde APENAS em JSON:
{{"qualidade_zona": "premium/boa/media/baixa", "acessibilidades": "...", "servicos_proximos": [], "potencial_valorizacao": "alto/medio/baixo", "notas": "..."}}"""
            },
            {
                "id": "price_analysis",
                "question": f"""Para um {subtipo} {tipologia} em {concelho}, {distrito}:
- Área: {area_total}m²
- Preço: {valor_base}€
- Preço/m²: {preco_m2:.0f}€/m²

Compara com o mercado imobiliário português atual.

Responde APENAS em JSON:
{{"preco_m2_mercado_zona": 2000, "preco_m2_imovel": {preco_m2:.0f}, "diferenca_percentual": -15, "avaliacao": "excelente/bom/justo/caro"}}"""
            },
            {
                "id": "property_condition",
                "question": f"""Analisa a descrição deste imóvel e avalia o estado:
Tipo: {subtipo} {tipologia}
"{descricao}"

Responde APENAS em JSON:
{{"estado_geral": "novo/bom/razoavel/para_obras/desconhecido", "obras_necessarias": [], "pontos_positivos": [], "ano_construcao_estimado": null}}"""
            },
            {
                "id": "auction_risks_property",
                "question": f"""Quais são os riscos específicos de comprar este imóvel em leilão judicial?
Tipo: {subtipo} em {concelho}

Lista os 3-4 principais riscos.

Responde APENAS em JSON:
{{"riscos": [{{"risco": "...", "gravidade": "alta/media/baixa", "como_verificar": "..."}}], "documentos_pedir": [], "custos_ocultos_possiveis": []}}"""
            },
            {
                "id": "investment_potential",
                "question": f"""Avalia o potencial de investimento:
- {subtipo} {tipologia} em {concelho}, {distrito}
- Área: {area_total}m²
- Preço: {valor_base}€

Para: habitação própria, arrendamento, revenda.

Responde APENAS em JSON:
{{"potencial_habitacao": "alto/medio/baixo", "potencial_arrendamento": "alto/medio/baixo", "renda_estimada_mensal": 500, "yield_estimada": 4.5, "potencial_revenda": "alto/medio/baixo"}}"""
            },
            {
                "id": "final_recommendation_property",
                "question": f"""Recomendação final para este {subtipo} {tipologia}:
- Local: {freguesia}, {concelho}
- Área: {area_total}m²
- Preço: {valor_base}€ ({preco_m2:.0f}€/m²)

Responde APENAS em JSON:
{{"score": 7.5, "recomendacao": "comprar/acompanhar/evitar", "resumo": "...", "pros": ["...", "..."], "cons": ["...", "..."], "perfil_ideal_comprador": "..."}}"""
            }
        ]

    # ========== IMAGE ANALYSIS ==========

    async def analyze_vehicle_image(self, image_url: str) -> ImageAnalysis:
        """Analyze a vehicle image using LLaVA"""
        prompt = """Analisa esta imagem de um veículo à venda em leilão.

Descreve:
1. Estado geral visível (excelente/bom/razoável/mau)
2. Danos ou problemas visíveis
3. Limpeza e cuidado aparente
4. Qualquer detalhe relevante para um comprador

Responde em JSON:
{"descricao": "...", "estado": "bom", "problemas": ["risco no para-choques"], "pontos_positivos": ["interior limpo"]}"""

        try:
            result = await self._analyze_image(image_url, prompt)

            if "error" in result:
                return ImageAnalysis(
                    image_url=image_url,
                    description=f"Erro: {result['error']}",
                    condition="unknown",
                    issues_found=[],
                    confidence=0.0
                )

            # Parse response
            response_text = result["response"]
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0:
                    data = json.loads(response_text[json_start:json_end])
                else:
                    data = {"descricao": response_text, "estado": "unknown", "problemas": []}
            except:
                data = {"descricao": response_text, "estado": "unknown", "problemas": []}

            return ImageAnalysis(
                image_url=image_url,
                description=data.get("descricao", ""),
                condition=data.get("estado", "unknown"),
                issues_found=data.get("problemas", []),
                confidence=0.7
            )

        except Exception as e:
            return ImageAnalysis(
                image_url=image_url,
                description=f"Erro na análise: {str(e)}",
                condition="unknown",
                issues_found=[],
                confidence=0.0
            )

    async def analyze_property_image(self, image_url: str) -> ImageAnalysis:
        """Analyze a property image using LLaVA"""
        prompt = """Analisa esta imagem de um imóvel à venda em leilão.

Descreve:
1. Estado geral visível (novo/bom/razoável/para obras)
2. Problemas visíveis (humidade, fissuras, degradação)
3. Qualidade dos acabamentos
4. Qualquer detalhe relevante para um comprador

Responde em JSON:
{"descricao": "...", "estado": "bom", "problemas": ["humidade na parede"], "pontos_positivos": ["boa luz natural"]}"""

        try:
            result = await self._analyze_image(image_url, prompt)

            if "error" in result:
                return ImageAnalysis(
                    image_url=image_url,
                    description=f"Erro: {result['error']}",
                    condition="unknown",
                    issues_found=[],
                    confidence=0.0
                )

            response_text = result["response"]
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0:
                    data = json.loads(response_text[json_start:json_end])
                else:
                    data = {"descricao": response_text, "estado": "unknown", "problemas": []}
            except:
                data = {"descricao": response_text, "estado": "unknown", "problemas": []}

            return ImageAnalysis(
                image_url=image_url,
                description=data.get("descricao", ""),
                condition=data.get("estado", "unknown"),
                issues_found=data.get("problemas", []),
                confidence=0.7
            )

        except Exception as e:
            return ImageAnalysis(
                image_url=image_url,
                description=f"Erro na análise: {str(e)}",
                condition="unknown",
                issues_found=[],
                confidence=0.0
            )

    # ========== MAIN ANALYSIS ==========

    async def analyze_vehicle(self, event: Dict[str, Any], analyze_images: bool = True, max_images: int = 3) -> DetailedAnalysis:
        """
        Complete vehicle analysis with batch questions and image analysis.
        """
        start_time = time.time()
        total_tokens = 0
        models_used = set()

        reference = event.get('reference', '')
        titulo = event.get('titulo', '')
        matricula = event.get('matricula', '')

        # 1. Decode plate
        plate_info = None
        if matricula:
            decoded = decode_portuguese_plate(matricula)
            plate_info = {
                "plate": decoded.plate,
                "format": decoded.format,
                "era": decoded.era,
                "year_min": decoded.year_min,
                "year_max": decoded.year_max,
            }

        # 2. Extract vehicle info from title
        vehicle_info = extract_vehicle_from_title(titulo)

        # 3. Run batch questions
        questions = self._get_vehicle_questions(event, plate_info or {}, vehicle_info)
        question_results = []

        for q in questions:
            try:
                result = await self._ask_question(q["question"])
                total_tokens += result["tokens"]
                models_used.add(self.text_model)

                question_results.append(QuestionResult(
                    question_id=q["id"],
                    question=q["question"][:100] + "...",
                    answer=result["response"],
                    confidence=0.7,
                    tokens_used=result["tokens"],
                    time_ms=result["time_ms"]
                ))
            except Exception as e:
                question_results.append(QuestionResult(
                    question_id=q["id"],
                    question=q["question"][:100] + "...",
                    answer=f"Erro: {str(e)}",
                    confidence=0.0,
                    tokens_used=0,
                    time_ms=0
                ))

        # 4. Analyze images
        image_analyses = []
        if analyze_images:
            fotos = event.get('fotos', [])
            if isinstance(fotos, str):
                try:
                    fotos = json.loads(fotos)
                except:
                    fotos = []

            for foto in fotos[:max_images]:
                url = foto.get('url') if isinstance(foto, dict) else foto
                if url:
                    try:
                        analysis = await self.analyze_vehicle_image(url)
                        image_analyses.append(analysis)
                        models_used.add(self.vision_model)
                    except Exception as e:
                        print(f"Error analyzing image: {e}")

        # 5. Extract final recommendation from last question
        final_rec = {}
        for qr in question_results:
            if qr.question_id == "final_recommendation":
                try:
                    json_start = qr.answer.find('{')
                    json_end = qr.answer.rfind('}') + 1
                    if json_start >= 0:
                        final_rec = json.loads(qr.answer[json_start:json_end])
                except:
                    pass

        total_time = int((time.time() - start_time) * 1000)

        return DetailedAnalysis(
            reference=reference,
            tipo="Veículo",
            vehicle_info=vehicle_info,
            plate_info=plate_info,
            questions=question_results,
            image_analyses=image_analyses,
            score=final_rec.get("score", 5.0),
            recommendation=final_rec.get("recomendacao", "watch"),
            summary=final_rec.get("resumo", ""),
            pros=final_rec.get("pros", []),
            cons=final_rec.get("cons", []),
            total_time_ms=total_time,
            total_tokens=total_tokens,
            models_used=list(models_used)
        )

    async def analyze_property(self, event: Dict[str, Any], analyze_images: bool = True, max_images: int = 3) -> DetailedAnalysis:
        """
        Complete property analysis with batch questions and image analysis.
        """
        start_time = time.time()
        total_tokens = 0
        models_used = set()

        reference = event.get('reference', '')

        # 1. Run batch questions
        questions = self._get_property_questions(event)
        question_results = []

        for q in questions:
            try:
                result = await self._ask_question(q["question"])
                total_tokens += result["tokens"]
                models_used.add(self.text_model)

                question_results.append(QuestionResult(
                    question_id=q["id"],
                    question=q["question"][:100] + "...",
                    answer=result["response"],
                    confidence=0.7,
                    tokens_used=result["tokens"],
                    time_ms=result["time_ms"]
                ))
            except Exception as e:
                question_results.append(QuestionResult(
                    question_id=q["id"],
                    question=q["question"][:100] + "...",
                    answer=f"Erro: {str(e)}",
                    confidence=0.0,
                    tokens_used=0,
                    time_ms=0
                ))

        # 2. Analyze images
        image_analyses = []
        if analyze_images:
            fotos = event.get('fotos', [])
            if isinstance(fotos, str):
                try:
                    fotos = json.loads(fotos)
                except:
                    fotos = []

            for foto in fotos[:max_images]:
                url = foto.get('url') if isinstance(foto, dict) else foto
                if url:
                    try:
                        analysis = await self.analyze_property_image(url)
                        image_analyses.append(analysis)
                        models_used.add(self.vision_model)
                    except Exception as e:
                        print(f"Error analyzing image: {e}")

        # 3. Extract final recommendation
        final_rec = {}
        for qr in question_results:
            if qr.question_id == "final_recommendation_property":
                try:
                    json_start = qr.answer.find('{')
                    json_end = qr.answer.rfind('}') + 1
                    if json_start >= 0:
                        final_rec = json.loads(qr.answer[json_start:json_end])
                except:
                    pass

        total_time = int((time.time() - start_time) * 1000)

        return DetailedAnalysis(
            reference=reference,
            tipo="Imóvel",
            questions=question_results,
            image_analyses=image_analyses,
            score=final_rec.get("score", 5.0),
            recommendation=final_rec.get("recomendacao", "watch"),
            summary=final_rec.get("resumo", ""),
            pros=final_rec.get("pros", []),
            cons=final_rec.get("cons", []),
            total_time_ms=total_time,
            total_tokens=total_tokens,
            models_used=list(models_used)
        )


# Singleton
_enhanced_service: Optional[EnhancedAIAnalysisService] = None


def get_enhanced_ai_service() -> EnhancedAIAnalysisService:
    """Get the enhanced AI analysis service"""
    global _enhanced_service
    if _enhanced_service is None:
        _enhanced_service = EnhancedAIAnalysisService()
    return _enhanced_service
