"""
Ollama AI Service for E-Leiloes
Generates tips and analysis for auction events using local LLM.
"""

import httpx
import json
import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds


@dataclass
class AiTipResult:
    """Result from AI analysis"""
    summary: str
    analysis: str
    pros: List[str]
    cons: List[str]
    recommendation: str  # 'buy', 'watch', 'skip'
    confidence: float  # 0.0-1.0
    tokens_used: int
    processing_time_ms: int
    model_used: str


class OllamaService:
    """Service for interacting with Ollama API"""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = OLLAMA_TIMEOUT

    async def check_health(self) -> Dict[str, Any]:
        """Check if Ollama is running and model is available"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check API is running
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return {"healthy": False, "error": "Ollama API not responding"}

                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                # Check if our model is available
                model_available = any(self.model in m for m in models)

                return {
                    "healthy": True,
                    "model": self.model,
                    "model_available": model_available,
                    "available_models": models
                }
        except httpx.ConnectError:
            return {"healthy": False, "error": "Cannot connect to Ollama. Is it running?"}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generic generate method for custom prompts.

        Args:
            prompt: The prompt to send to Ollama
            model: Optional model override (uses instance model if not specified)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with 'response' key containing the generated text, or 'error' key on failure
        """
        use_model = model or self.model

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": use_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        }
                    }
                )

                if response.status_code != 200:
                    return {"error": f"Ollama API error: {response.status_code} - {response.text}"}

                data = response.json()
                return {
                    "response": data.get("response", ""),
                    "model": data.get("model", use_model),
                    "eval_count": data.get("eval_count", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "total_duration": data.get("total_duration", 0),
                }

        except httpx.ConnectError:
            return {"error": "Cannot connect to Ollama. Is it running?"}
        except httpx.TimeoutException:
            return {"error": f"Ollama request timed out after {self.timeout}s"}
        except Exception as e:
            return {"error": str(e)}

    def _build_property_prompt(self, event: Dict[str, Any]) -> str:
        """Build analysis prompt for property (imovel)"""
        titulo = event.get('titulo', 'N/A')
        subtipo = event.get('subtipo', 'N/A')
        distrito = event.get('distrito', 'N/A')
        concelho = event.get('concelho', 'N/A')
        freguesia = event.get('freguesia', 'N/A')
        valor_base = event.get('valor_base', 0)
        valor_abertura = event.get('valor_abertura', 0)
        lance_atual = event.get('lance_atual', 0)
        area_total = event.get('area_total', 'N/A')
        area_privativa = event.get('area_privativa', 'N/A')
        tipologia = event.get('tipologia', 'N/A')
        descricao = event.get('descricao', '')[:500] if event.get('descricao') else 'N/A'
        observacoes = event.get('observacoes', '')[:300] if event.get('observacoes') else ''

        # Calculate price per m2 if possible
        preco_m2 = ""
        if area_total and valor_base and area_total != 'N/A' and valor_base > 0:
            try:
                pm2 = valor_base / float(area_total)
                preco_m2 = f"Preco/m2: {pm2:.2f}EUR"
            except:
                pass

        return f"""Analisa este imovel em leilao judicial portugues e da conselhos ao potencial comprador.

DADOS DO IMOVEL:
- Titulo: {titulo}
- Tipo: {subtipo}
- Tipologia: {tipologia}
- Localizacao: {freguesia}, {concelho}, {distrito}
- Area Total: {area_total} m2
- Area Privativa: {area_privativa} m2
- Valor Base: {valor_base}EUR
- Valor Abertura: {valor_abertura}EUR
- Lance Atual: {lance_atual}EUR
{preco_m2}

Descricao: {descricao}
{f"Observacoes: {observacoes}" if observacoes else ""}

Responde em JSON com esta estrutura EXATA:
{{
  "summary": "Resumo curto de 1-2 frases sobre o imovel",
  "analysis": "Analise detalhada de 3-4 paragrafos sobre valor, localizacao, potencial, riscos",
  "pros": ["vantagem 1", "vantagem 2", "vantagem 3"],
  "cons": ["desvantagem 1", "desvantagem 2", "desvantagem 3"],
  "recommendation": "buy/watch/skip",
  "confidence": 0.7
}}

Considera:
- Precos de mercado na zona
- Estado do imovel (se mencionado)
- Localizacao e acessibilidades
- Potencial de valorizacao
- Riscos de leiloes judiciais (onus, dividas, ocupacao)
- Se o preco/m2 e competitivo

Responde APENAS com JSON valido, sem texto adicional."""

    def _build_vehicle_prompt(self, event: Dict[str, Any]) -> str:
        """Build analysis prompt for vehicle (veiculo)"""
        titulo = event.get('titulo', 'N/A')
        subtipo = event.get('subtipo', 'N/A')
        matricula = event.get('matricula', 'N/A')
        distrito = event.get('distrito', 'N/A')
        valor_base = event.get('valor_base', 0)
        valor_abertura = event.get('valor_abertura', 0)
        lance_atual = event.get('lance_atual', 0)
        descricao = event.get('descricao', '')[:500] if event.get('descricao') else 'N/A'
        observacoes = event.get('observacoes', '')[:300] if event.get('observacoes') else ''

        return f"""Analisa este veiculo em leilao judicial portugues e da conselhos ao potencial comprador.

DADOS DO VEICULO:
- Titulo: {titulo}
- Tipo: {subtipo}
- Matricula: {matricula}
- Localizacao: {distrito}
- Valor Base: {valor_base}EUR
- Valor Abertura: {valor_abertura}EUR
- Lance Atual: {lance_atual}EUR

Descricao: {descricao}
{f"Observacoes: {observacoes}" if observacoes else ""}

Responde em JSON com esta estrutura EXATA:
{{
  "summary": "Resumo curto de 1-2 frases sobre o veiculo",
  "analysis": "Analise detalhada de 2-3 paragrafos sobre valor, estado, potencial, riscos",
  "pros": ["vantagem 1", "vantagem 2", "vantagem 3"],
  "cons": ["desvantagem 1", "desvantagem 2", "desvantagem 3"],
  "recommendation": "buy/watch/skip",
  "confidence": 0.7
}}

Considera:
- Ano do veiculo (se possivel determinar pela matricula)
- Valor de mercado para veiculos similares
- Estado mencionado na descricao
- Quilometragem (se mencionada)
- Riscos de leiloes judiciais (documentacao, dividas)
- Se o preco e competitivo vs mercado

Responde APENAS com JSON valido, sem texto adicional."""

    async def analyze_event(self, event: Dict[str, Any]) -> AiTipResult:
        """
        Analyze an auction event and generate tips.

        Args:
            event: Event data dictionary with keys like titulo, tipo_id, subtipo, etc.

        Returns:
            AiTipResult with the analysis

        Raises:
            Exception if analysis fails
        """
        start_time = time.time()

        # Determine prompt based on event type
        tipo_id = event.get('tipo_id')
        if tipo_id == 1:  # Imovel
            prompt = self._build_property_prompt(event)
        elif tipo_id == 2:  # Veiculo
            prompt = self._build_vehicle_prompt(event)
        else:
            raise ValueError(f"Unsupported event type: {tipo_id}")

        # Call Ollama API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1024,
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

            data = response.json()

        # Parse response
        response_text = data.get("response", "")
        tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

        # Try to extract JSON from response
        try:
            # Find JSON in response (might have extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result_data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response as JSON: {e}\nResponse: {response_text[:500]}")

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Validate and extract fields
        return AiTipResult(
            summary=result_data.get("summary", "Analise nao disponivel"),
            analysis=result_data.get("analysis", ""),
            pros=result_data.get("pros", [])[:5],  # Limit to 5
            cons=result_data.get("cons", [])[:5],  # Limit to 5
            recommendation=result_data.get("recommendation", "watch"),
            confidence=min(1.0, max(0.0, float(result_data.get("confidence", 0.5)))),
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
            model_used=self.model
        )


# Singleton instance
_ollama_service: Optional[OllamaService] = None


def get_ollama_service() -> OllamaService:
    """Get or create the Ollama service singleton"""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
