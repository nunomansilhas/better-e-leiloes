# -*- coding: utf-8 -*-
"""
Vehicle Lookup Router
API endpoints for vehicle information lookup using license plate (matrícula).

Features:
- Decode Portuguese license plate format
- Lookup vehicle info from InfoMatricula.pt API
- Check insurance status
- Search market prices (StandVirtual/AutoUncle)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/vehicle", tags=["Vehicle Lookup"])


# Response models
class PlateInfoResponse(BaseModel):
    """Decoded plate information"""
    plate: str
    format: str
    era: str
    year_min: int
    year_max: int
    notes: str


class VehicleInfoResponse(BaseModel):
    """Vehicle information from InfoMatricula API"""
    plate: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    versao: Optional[str] = None
    ano: Optional[int] = None
    combustivel: Optional[str] = None
    potencia_cv: Optional[int] = None
    potencia_kw: Optional[int] = None
    cor: Optional[str] = None
    categoria: Optional[str] = None
    vin: Optional[str] = None
    tipo_proprietario: Optional[str] = None
    origem: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


class InsuranceInfoResponse(BaseModel):
    """Insurance information"""
    plate: str
    tem_seguro: Optional[bool] = None
    seguradora: Optional[str] = None
    apolice: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


class MarketListingResponse(BaseModel):
    """Individual market listing"""
    titulo: str
    preco: int
    params: Optional[str] = None


class MarketPricesResponse(BaseModel):
    """Market prices summary"""
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
    listings: List[MarketListingResponse]


class FullVehicleResponse(BaseModel):
    """Complete vehicle information from all sources"""
    plate: str
    plate_info: PlateInfoResponse
    vehicle_info: Optional[VehicleInfoResponse] = None
    insurance: Optional[InsuranceInfoResponse] = None
    market_prices: Optional[MarketPricesResponse] = None
    sources: List[str]
    errors: List[str]
    lookup_time_ms: int


def _normalize_plate(plate: str) -> str:
    """Normalize plate format to XX-XX-XX"""
    clean = plate.replace("-", "").replace(" ", "").upper()
    if len(clean) == 6:
        return f"{clean[:2]}-{clean[2:4]}-{clean[4:6]}"
    return plate.upper()


@router.get("/decode/{plate}", response_model=PlateInfoResponse)
async def decode_plate(plate: str):
    """
    Decode a Portuguese license plate to estimate vehicle year.

    Portuguese plate formats:
    - Pre-1992: XX-00-00 (letters-numbers-numbers)
    - 1992-2005: 00-00-XX (numbers-numbers-letters)
    - 2005-2020: 00-XX-00 (numbers-letters-numbers)
    - 2020+: XX-00-XX (letters-numbers-letters)
    """
    from services.vehicle_lookup import decode_portuguese_plate

    info = decode_portuguese_plate(plate)

    return PlateInfoResponse(
        plate=info.plate,
        format=info.format,
        era=info.era,
        year_min=info.year_min,
        year_max=info.year_max,
        notes=info.notes
    )


@router.get("/info/{plate}", response_model=VehicleInfoResponse)
async def get_vehicle_info(plate: str):
    """
    Get vehicle information from InfoMatricula.pt API.

    Returns: marca, modelo, ano, combustivel, potencia, cor, etc.
    """
    from services.vehicle_lookup import lookup_plate_infomatricula_api

    normalized_plate = _normalize_plate(plate)

    try:
        result = await lookup_plate_infomatricula_api(normalized_plate)

        if "error" in result:
            return VehicleInfoResponse(
                plate=normalized_plate,
                error=result["error"]
            )

        return VehicleInfoResponse(
            plate=normalized_plate,
            marca=result.get("marca"),
            modelo=result.get("modelo"),
            versao=result.get("versao"),
            ano=result.get("ano"),
            combustivel=result.get("combustivel"),
            potencia_cv=result.get("potencia_cv"),
            potencia_kw=result.get("potencia_kw"),
            cor=result.get("cor"),
            categoria=result.get("categoria"),
            vin=result.get("vin"),
            tipo_proprietario=result.get("tipo_proprietario"),
            origem=result.get("origem"),
            source=result.get("source")
        )

    except Exception as e:
        return VehicleInfoResponse(
            plate=normalized_plate,
            error=str(e)
        )


@router.get("/insurance/{plate}", response_model=InsuranceInfoResponse)
async def get_insurance_info(plate: str):
    """
    Check vehicle insurance status from InfoMatricula API.

    Returns: tem_seguro, seguradora, apolice, data_inicio, data_fim
    """
    from services.vehicle_lookup import check_insurance_api

    normalized_plate = _normalize_plate(plate)

    try:
        result = await check_insurance_api(normalized_plate)

        if "error" in result:
            return InsuranceInfoResponse(
                plate=normalized_plate,
                error=result["error"]
            )

        return InsuranceInfoResponse(
            plate=normalized_plate,
            tem_seguro=result.get("tem_seguro"),
            seguradora=result.get("seguradora"),
            apolice=result.get("apolice"),
            data_inicio=result.get("data_inicio"),
            data_fim=result.get("data_fim"),
            source=result.get("source")
        )

    except Exception as e:
        return InsuranceInfoResponse(
            plate=normalized_plate,
            error=str(e)
        )


@router.get("/market-prices")
async def get_market_prices(
    marca: str = Query(..., description="Vehicle brand (e.g., POLESTAR)"),
    modelo: Optional[str] = Query(None, description="Vehicle model (e.g., POLESTAR 2)"),
    ano: Optional[int] = Query(None, description="Vehicle year (e.g., 2023)"),
    combustivel: Optional[str] = Query(None, description="Fuel type (e.g., ELÉTRICO, Diesel, Gasolina)"),
    km: Optional[int] = Query(None, description="Current mileage for filtering (+/- 25000 km range)")
):
    """
    Search market prices for a vehicle on StandVirtual and AutoUncle.

    Note: This uses Playwright for web scraping and may take a few seconds.
    Should be run locally, not on cloud servers which typically get blocked.
    """
    from services.vehicle_lookup import get_market_prices as search_market_prices

    try:
        result = await search_market_prices(marca, modelo, ano, combustivel, km, debug=False)

        if not result:
            return {
                "error": "Nenhum resultado encontrado",
                "marca": marca,
                "modelo": modelo,
                "ano": ano
            }

        return MarketPricesResponse(
            marca=result.marca,
            modelo=result.modelo,
            ano=result.ano,
            num_resultados=result.num_resultados,
            preco_min=result.preco_min,
            preco_max=result.preco_max,
            preco_medio=result.preco_medio,
            preco_mediana=result.preco_mediana,
            fonte=result.fonte,
            data_consulta=result.data_consulta,
            listings=[
                MarketListingResponse(
                    titulo=l["titulo"],
                    preco=l["preco"],
                    params=l.get("params")
                )
                for l in result.listings
            ]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/full/{plate}", response_model=FullVehicleResponse)
async def get_full_vehicle_info(
    plate: str,
    include_market: bool = Query(False, description="Include market prices (slower, requires Playwright)")
):
    """
    Get complete vehicle information from all sources.

    Sources:
    1. Plate decoder (instant)
    2. InfoMatricula.pt API (vehicle info)
    3. InfoMatricula.pt API (insurance)
    4. StandVirtual/AutoUncle (market prices - optional)

    Note: Set include_market=true to also fetch market prices (requires Playwright).
    """
    from services.vehicle_lookup import (
        decode_portuguese_plate,
        lookup_plate_infomatricula_api,
        check_insurance_api,
        get_market_prices as search_market_prices
    )
    import time

    start_time = time.time()
    normalized_plate = _normalize_plate(plate)
    sources = ["plate_decoder"]
    errors = []

    # 1. Decode plate (instant)
    plate_info = decode_portuguese_plate(normalized_plate)
    plate_info_response = PlateInfoResponse(
        plate=plate_info.plate,
        format=plate_info.format,
        era=plate_info.era,
        year_min=plate_info.year_min,
        year_max=plate_info.year_max,
        notes=plate_info.notes
    )

    # 2. Get vehicle info from API
    vehicle_info_response = None
    try:
        vehicle_result = await lookup_plate_infomatricula_api(normalized_plate)
        if "error" not in vehicle_result:
            vehicle_info_response = VehicleInfoResponse(
                plate=normalized_plate,
                marca=vehicle_result.get("marca"),
                modelo=vehicle_result.get("modelo"),
                versao=vehicle_result.get("versao"),
                ano=vehicle_result.get("ano"),
                combustivel=vehicle_result.get("combustivel"),
                potencia_cv=vehicle_result.get("potencia_cv"),
                potencia_kw=vehicle_result.get("potencia_kw"),
                cor=vehicle_result.get("cor"),
                categoria=vehicle_result.get("categoria"),
                vin=vehicle_result.get("vin"),
                tipo_proprietario=vehicle_result.get("tipo_proprietario"),
                origem=vehicle_result.get("origem"),
                source=vehicle_result.get("source")
            )
            sources.append("infomatricula.pt (API)")
        else:
            errors.append(f"InfoMatricula: {vehicle_result['error']}")
    except Exception as e:
        errors.append(f"InfoMatricula: {str(e)}")

    # 3. Get insurance info from API
    insurance_response = None
    try:
        insurance_result = await check_insurance_api(normalized_plate)
        if "error" not in insurance_result:
            insurance_response = InsuranceInfoResponse(
                plate=normalized_plate,
                tem_seguro=insurance_result.get("tem_seguro"),
                seguradora=insurance_result.get("seguradora"),
                apolice=insurance_result.get("apolice"),
                data_inicio=insurance_result.get("data_inicio"),
                data_fim=insurance_result.get("data_fim"),
                source=insurance_result.get("source")
            )
            sources.append("infomatricula.pt (seguro)")
        else:
            errors.append(f"Seguro: {insurance_result['error']}")
    except Exception as e:
        errors.append(f"Seguro: {str(e)}")

    # 4. Get market prices (optional, slower)
    market_prices_response = None
    if include_market and vehicle_info_response and vehicle_info_response.marca:
        try:
            market_result = await search_market_prices(
                vehicle_info_response.marca,
                vehicle_info_response.modelo,
                vehicle_info_response.ano or plate_info.year_min,
                vehicle_info_response.combustivel,
                None,  # km not available from API
                debug=False
            )
            if market_result:
                market_prices_response = MarketPricesResponse(
                    marca=market_result.marca,
                    modelo=market_result.modelo,
                    ano=market_result.ano,
                    num_resultados=market_result.num_resultados,
                    preco_min=market_result.preco_min,
                    preco_max=market_result.preco_max,
                    preco_medio=market_result.preco_medio,
                    preco_mediana=market_result.preco_mediana,
                    fonte=market_result.fonte,
                    data_consulta=market_result.data_consulta,
                    listings=[
                        MarketListingResponse(
                            titulo=l["titulo"],
                            preco=l["preco"],
                            params=l.get("params")
                        )
                        for l in market_result.listings[:10]  # Limit to 10 listings
                    ]
                )
                sources.append(market_result.fonte)
        except Exception as e:
            errors.append(f"Market prices: {str(e)}")

    lookup_time_ms = int((time.time() - start_time) * 1000)

    return FullVehicleResponse(
        plate=normalized_plate,
        plate_info=plate_info_response,
        vehicle_info=vehicle_info_response,
        insurance=insurance_response,
        market_prices=market_prices_response,
        sources=sources,
        errors=errors,
        lookup_time_ms=lookup_time_ms
    )
