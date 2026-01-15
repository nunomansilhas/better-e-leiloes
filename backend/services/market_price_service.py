# -*- coding: utf-8 -*-
"""
Market Price Service - Hybrid Approach

Gets market prices using a fallback strategy:
1. Database cache (instant, most reliable if recent)
2. Real-time scraping (slower, may fail)
3. AI estimation (always available, lower confidence)

Author: Better E-Leiloes Team
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from sqlalchemy import select, and_, desc

from logger import log_info, log_warning, log_error


@dataclass
class MarketPriceResult:
    """Result of a market price lookup"""
    marca: str
    modelo: str
    ano: int

    # Price data
    preco_min: Optional[float] = None
    preco_max: Optional[float] = None
    preco_medio: Optional[float] = None
    preco_mediana: Optional[float] = None
    num_anuncios: int = 0

    # Sample listings
    listings: List[Dict[str, Any]] = field(default_factory=list)

    # Source tracking
    fonte: str = "unknown"  # 'database', 'scraping', 'ai_estimate'
    confianca: str = "baixa"  # 'baixa', 'media', 'alta'
    data_recolha: Optional[datetime] = None

    # Error tracking
    error: Optional[str] = None


class MarketPriceService:
    """
    Hybrid market price service with fallback strategy.

    Usage:
        service = MarketPriceService()
        result = await service.get_market_price("CITROEN", "C4 Picasso", 2019, "Diesel")
    """

    # How old can cached data be before we consider it stale
    CACHE_MAX_AGE_DAYS = 30

    def __init__(self):
        pass

    async def get_market_price(
        self,
        marca: str,
        modelo: str,
        ano: int,
        combustivel: Optional[str] = None,
        force_refresh: bool = False
    ) -> MarketPriceResult:
        """
        Get market price using hybrid approach.

        Args:
            marca: Vehicle brand (e.g., "CITROEN")
            modelo: Vehicle model (e.g., "C4 Picasso")
            ano: Vehicle year
            combustivel: Fuel type (optional)
            force_refresh: Skip cache and force scraping

        Returns:
            MarketPriceResult with price data and confidence level
        """
        marca_normalized = self._normalize_marca(marca)
        modelo_normalized = self._normalize_modelo(modelo)

        log_info(f"Getting market price for {marca_normalized} {modelo_normalized} ({ano})")

        # Strategy 1: Try database cache first (unless force_refresh)
        if not force_refresh:
            cached = await self._get_from_database(marca_normalized, modelo_normalized, ano, combustivel)
            if cached and cached.preco_medio:
                log_info(f"Found cached price: {cached.preco_medio}€ (from {cached.fonte})")
                return cached

        # Strategy 2: Try real-time scraping
        scraped = await self._get_from_scraping(marca_normalized, modelo_normalized, ano, combustivel)
        if scraped and scraped.preco_medio and not scraped.error:
            # Save to cache for future use
            await self._save_to_database(scraped)
            log_info(f"Scraped price: {scraped.preco_medio}€")
            return scraped

        # Strategy 3: Fallback to AI estimation
        estimated = await self._get_from_ai_estimation(marca_normalized, modelo_normalized, ano, combustivel)
        if estimated and estimated.preco_medio:
            # Also save AI estimates to cache (with lower confidence)
            await self._save_to_database(estimated)
            log_info(f"AI estimated price: {estimated.preco_medio}€ (confidence: {estimated.confianca})")
            return estimated

        # All strategies failed
        log_warning(f"Could not get market price for {marca_normalized} {modelo_normalized} ({ano})")
        return MarketPriceResult(
            marca=marca_normalized,
            modelo=modelo_normalized,
            ano=ano,
            fonte="none",
            confianca="baixa",
            error="Could not determine market price from any source"
        )

    def _normalize_marca(self, marca: str) -> str:
        """Normalize brand name for consistency"""
        marca = marca.upper().strip()

        # Common brand name variations
        brand_map = {
            "MERCEDES-BENZ": "MERCEDES",
            "MERCEDES BENZ": "MERCEDES",
            "VW": "VOLKSWAGEN",
            "ALFA-ROMEO": "ALFA ROMEO",
            "LAND-ROVER": "LAND ROVER",
            "ASTON-MARTIN": "ASTON MARTIN",
        }

        return brand_map.get(marca, marca)

    def _normalize_modelo(self, modelo: str) -> str:
        """Normalize model name for better matching"""
        if not modelo:
            return ""

        modelo = modelo.strip()

        # Remove common suffixes that vary
        for suffix in [" (GASOLEO)", " (GASOLINA)", " (DIESEL)", " (ELETRICO)"]:
            if modelo.upper().endswith(suffix):
                modelo = modelo[:-len(suffix)]

        return modelo

    async def _get_from_database(
        self,
        marca: str,
        modelo: str,
        ano: int,
        combustivel: Optional[str] = None
    ) -> Optional[MarketPriceResult]:
        """Try to get price from database cache"""
        try:
            from database import get_db, MarketPricesDB

            cutoff_date = datetime.utcnow() - timedelta(days=self.CACHE_MAX_AGE_DAYS)

            async with get_db() as db:
                # Build query
                query = select(MarketPricesDB).where(
                    and_(
                        MarketPricesDB.marca == marca,
                        MarketPricesDB.data_recolha >= cutoff_date
                    )
                )

                # Try exact model match first
                exact_query = query.where(MarketPricesDB.modelo == modelo)
                if ano:
                    exact_query = exact_query.where(MarketPricesDB.ano == ano)
                if combustivel:
                    exact_query = exact_query.where(MarketPricesDB.combustivel == combustivel)

                exact_query = exact_query.order_by(desc(MarketPricesDB.data_recolha)).limit(1)

                result = await db.session.execute(exact_query)
                cached = result.scalar_one_or_none()

                if cached:
                    listings = []
                    if cached.sample_listings:
                        try:
                            listings = json.loads(cached.sample_listings)
                        except:
                            pass

                    return MarketPriceResult(
                        marca=cached.marca,
                        modelo=cached.modelo,
                        ano=cached.ano,
                        preco_min=float(cached.preco_min) if cached.preco_min else None,
                        preco_max=float(cached.preco_max) if cached.preco_max else None,
                        preco_medio=float(cached.preco_medio) if cached.preco_medio else None,
                        preco_mediana=float(cached.preco_mediana) if cached.preco_mediana else None,
                        num_anuncios=cached.num_anuncios or 0,
                        listings=listings,
                        fonte="database",
                        confianca=cached.confianca or "media",
                        data_recolha=cached.data_recolha
                    )

                # Try partial model match (model contains search term)
                partial_query = query.where(
                    MarketPricesDB.modelo.contains(modelo.split()[0])  # First word of model
                )
                if ano:
                    # Allow +/- 2 years
                    partial_query = partial_query.where(
                        and_(
                            MarketPricesDB.ano >= ano - 2,
                            MarketPricesDB.ano <= ano + 2
                        )
                    )

                partial_query = partial_query.order_by(desc(MarketPricesDB.data_recolha)).limit(1)

                result = await db.session.execute(partial_query)
                cached = result.scalar_one_or_none()

                if cached:
                    listings = []
                    if cached.sample_listings:
                        try:
                            listings = json.loads(cached.sample_listings)
                        except:
                            pass

                    return MarketPriceResult(
                        marca=cached.marca,
                        modelo=cached.modelo,
                        ano=cached.ano,
                        preco_min=float(cached.preco_min) if cached.preco_min else None,
                        preco_max=float(cached.preco_max) if cached.preco_max else None,
                        preco_medio=float(cached.preco_medio) if cached.preco_medio else None,
                        preco_mediana=float(cached.preco_mediana) if cached.preco_mediana else None,
                        num_anuncios=cached.num_anuncios or 0,
                        listings=listings,
                        fonte="database",
                        confianca="media",  # Lower confidence for partial match
                        data_recolha=cached.data_recolha
                    )

                return None

        except Exception as e:
            log_error(f"Database cache lookup failed: {e}")
            return None

    async def _get_from_scraping(
        self,
        marca: str,
        modelo: str,
        ano: int,
        combustivel: Optional[str] = None
    ) -> Optional[MarketPriceResult]:
        """Try to get price from real-time scraping"""
        try:
            from services.vehicle_lookup import get_market_prices

            result = await get_market_prices(
                marca=marca,
                modelo=modelo,
                ano=ano,
                combustivel=combustivel,
                km=None,
                debug=False
            )

            if result and result.num_resultados > 0:
                return MarketPriceResult(
                    marca=marca,
                    modelo=modelo,
                    ano=ano,
                    preco_min=result.preco_min,
                    preco_max=result.preco_max,
                    preco_medio=result.preco_medio,
                    preco_mediana=result.preco_mediana,
                    num_anuncios=result.num_resultados,
                    listings=result.listings[:10],  # Keep top 10
                    fonte="scraping",
                    confianca="alta" if result.num_resultados >= 10 else "media",
                    data_recolha=datetime.utcnow()
                )

            return None

        except Exception as e:
            log_error(f"Scraping failed: {e}")
            return MarketPriceResult(
                marca=marca,
                modelo=modelo,
                ano=ano,
                fonte="scraping",
                confianca="baixa",
                error=str(e)
            )

    async def _get_from_ai_estimation(
        self,
        marca: str,
        modelo: str,
        ano: int,
        combustivel: Optional[str] = None
    ) -> Optional[MarketPriceResult]:
        """Get price estimation from AI"""
        try:
            from services.ollama_service import OllamaService

            ollama = OllamaService()

            # Check if Ollama is available
            if not await ollama.is_available():
                log_warning("Ollama not available for price estimation")
                return None

            fuel_text = f", {combustivel}" if combustivel else ""
            current_year = datetime.now().year
            vehicle_age = current_year - ano

            prompt = f"""Para um {marca} {modelo} de {ano}{fuel_text} em Portugal:

Estima o valor de mercado atual para venda em stand/particular.

RESPONDE APENAS EM JSON COM ESTE FORMATO EXATO:
{{
    "valor_estimado_min": <número em euros>,
    "valor_estimado_max": <número em euros>,
    "valor_estimado_medio": <número em euros>,
    "confianca": "baixa" ou "media" ou "alta",
    "fatores": [
        {{"fator": "descrição", "impacto": "positivo" ou "negativo"}}
    ],
    "notas": "contexto adicional"
}}

Considera:
- Idade do veículo: {vehicle_age} anos
- Mercado português atual
- Estado médio/bom para a idade
- Sê conservador nas estimativas"""

            response = await ollama.generate(
                prompt=prompt,
                model="llama3.2:3b",
                temperature=0.3
            )

            if response and "error" not in response:
                try:
                    # Extract JSON from response
                    response_text = response.get("response", "")

                    # Try to find JSON in the response
                    import re
                    json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())

                        preco_min = data.get("valor_estimado_min")
                        preco_max = data.get("valor_estimado_max")
                        preco_medio = data.get("valor_estimado_medio")

                        if preco_medio:
                            return MarketPriceResult(
                                marca=marca,
                                modelo=modelo,
                                ano=ano,
                                preco_min=preco_min,
                                preco_max=preco_max,
                                preco_medio=preco_medio,
                                preco_mediana=preco_medio,  # Use medio as mediana for AI estimates
                                num_anuncios=0,
                                listings=[],
                                fonte="ai_estimate",
                                confianca=data.get("confianca", "baixa"),
                                data_recolha=datetime.utcnow()
                            )
                except json.JSONDecodeError as e:
                    log_error(f"Failed to parse AI price estimation: {e}")

            return None

        except Exception as e:
            log_error(f"AI price estimation failed: {e}")
            return None

    async def _save_to_database(self, result: MarketPriceResult) -> bool:
        """Save price result to database cache"""
        try:
            from database import get_db, MarketPricesDB
            from sqlalchemy import select

            async with get_db() as db:
                # Check if entry exists for this marca/modelo/ano/fonte
                existing_query = select(MarketPricesDB).where(
                    and_(
                        MarketPricesDB.marca == result.marca,
                        MarketPricesDB.modelo == result.modelo,
                        MarketPricesDB.ano == result.ano,
                        MarketPricesDB.fonte == result.fonte
                    )
                )

                existing_result = await db.session.execute(existing_query)
                existing = existing_result.scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.preco_min = result.preco_min
                    existing.preco_max = result.preco_max
                    existing.preco_medio = result.preco_medio
                    existing.preco_mediana = result.preco_mediana
                    existing.num_anuncios = result.num_anuncios
                    existing.sample_listings = json.dumps(result.listings) if result.listings else None
                    existing.confianca = result.confianca
                    existing.data_recolha = result.data_recolha or datetime.utcnow()
                    existing.updated_at = datetime.utcnow()
                else:
                    # Insert new
                    new_entry = MarketPricesDB(
                        marca=result.marca,
                        modelo=result.modelo,
                        ano=result.ano,
                        preco_min=result.preco_min,
                        preco_max=result.preco_max,
                        preco_medio=result.preco_medio,
                        preco_mediana=result.preco_mediana,
                        num_anuncios=result.num_anuncios,
                        sample_listings=json.dumps(result.listings) if result.listings else None,
                        fonte=result.fonte,
                        confianca=result.confianca,
                        data_recolha=result.data_recolha or datetime.utcnow()
                    )
                    db.session.add(new_entry)

                await db.session.commit()
                return True

        except Exception as e:
            log_error(f"Failed to save price to database: {e}")
            return False

    async def get_auction_history(
        self,
        marca: str,
        modelo: str,
        ano: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get historical auction data for similar vehicles.

        Args:
            marca: Vehicle brand
            modelo: Vehicle model
            ano: Vehicle year (optional, will search +/- 3 years)
            limit: Maximum results to return

        Returns:
            List of historical auction records
        """
        try:
            from database import get_db, AuctionHistoryDB

            marca_normalized = self._normalize_marca(marca)

            async with get_db() as db:
                query = select(AuctionHistoryDB).where(
                    AuctionHistoryDB.marca == marca_normalized
                )

                # Partial model match
                if modelo:
                    first_word = modelo.split()[0]
                    query = query.where(AuctionHistoryDB.modelo.contains(first_word))

                # Year range
                if ano:
                    query = query.where(
                        and_(
                            AuctionHistoryDB.ano >= ano - 3,
                            AuctionHistoryDB.ano <= ano + 3
                        )
                    )

                query = query.order_by(desc(AuctionHistoryDB.data_fim)).limit(limit)

                result = await db.session.execute(query)
                records = result.scalars().all()

                return [
                    {
                        "reference": r.reference,
                        "marca": r.marca,
                        "modelo": r.modelo,
                        "ano": r.ano,
                        "valor_base": float(r.valor_base) if r.valor_base else None,
                        "valor_venda": float(r.valor_venda) if r.valor_venda else None,
                        "vendido": r.vendido,
                        "data_fim": r.data_fim.isoformat() if r.data_fim else None
                    }
                    for r in records
                ]

        except Exception as e:
            log_error(f"Failed to get auction history: {e}")
            return []

    async def calculate_auction_stats(
        self,
        marca: str,
        modelo: str,
        ano: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate statistics from historical auctions.

        Returns:
            Dict with stats like average sale price, success rate, etc.
        """
        history = await self.get_auction_history(marca, modelo, ano, limit=50)

        if not history:
            return {
                "total_leiloes": 0,
                "taxa_sucesso": None,
                "preco_medio_venda": None,
                "desconto_medio_vs_base": None
            }

        total = len(history)
        vendidos = [h for h in history if h["vendido"]]
        taxa_sucesso = len(vendidos) / total if total > 0 else 0

        precos_venda = [h["valor_venda"] for h in vendidos if h["valor_venda"]]
        preco_medio = sum(precos_venda) / len(precos_venda) if precos_venda else None

        # Calculate average discount vs base
        descontos = []
        for h in vendidos:
            if h["valor_base"] and h["valor_venda"] and h["valor_base"] > 0:
                desconto = ((h["valor_base"] - h["valor_venda"]) / h["valor_base"]) * 100
                descontos.append(desconto)

        desconto_medio = sum(descontos) / len(descontos) if descontos else None

        return {
            "total_leiloes": total,
            "total_vendidos": len(vendidos),
            "taxa_sucesso": round(taxa_sucesso * 100, 1),
            "preco_medio_venda": round(preco_medio, 2) if preco_medio else None,
            "desconto_medio_vs_base": round(desconto_medio, 1) if desconto_medio else None,
            "ultimos_leiloes": history[:5]
        }


# Singleton instance
_market_price_service: Optional[MarketPriceService] = None


def get_market_price_service() -> MarketPriceService:
    """Get singleton instance of MarketPriceService"""
    global _market_price_service
    if _market_price_service is None:
        _market_price_service = MarketPriceService()
    return _market_price_service
