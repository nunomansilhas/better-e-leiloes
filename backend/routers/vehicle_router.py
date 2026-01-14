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

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
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


# ============== EVENT VEHICLE DATA ENDPOINTS ==============

class AIQuestionResultResponse(BaseModel):
    """AI question result"""
    question_id: str
    question: str
    answer: str
    confidence: float
    time_ms: int


class AIImageAnalysisResponse(BaseModel):
    """AI image analysis result"""
    image_url: str
    description: str
    condition: str
    issues_found: List[str]
    confidence: float


class EventVehicleDataResponse(BaseModel):
    """Vehicle data for an auction event"""
    reference: str
    matricula: Optional[str] = None
    event_titulo: Optional[str] = None
    event_valor_base: Optional[float] = None
    event_lance_atual: Optional[float] = None

    # Vehicle info
    marca: Optional[str] = None
    modelo: Optional[str] = None
    versao: Optional[str] = None
    ano: Optional[int] = None
    combustivel: Optional[str] = None
    potencia_cv: Optional[int] = None
    cor: Optional[str] = None
    vin: Optional[str] = None

    # Insurance
    tem_seguro: Optional[bool] = None
    seguradora: Optional[str] = None
    seguro_data_fim: Optional[str] = None

    # Market comparison
    market_num_resultados: Optional[int] = None
    market_preco_min: Optional[float] = None
    market_preco_max: Optional[float] = None
    market_preco_medio: Optional[float] = None
    market_preco_mediana: Optional[float] = None
    market_fonte: Optional[str] = None
    market_listings: Optional[List[MarketListingResponse]] = None

    # Analysis
    poupanca_estimada: Optional[float] = None
    desconto_percentagem: Optional[float] = None

    # AI Analysis
    ai_score: Optional[float] = None
    ai_recommendation: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_pros: Optional[List[str]] = None
    ai_cons: Optional[List[str]] = None
    ai_questions: Optional[List[AIQuestionResultResponse]] = None
    ai_image_analyses: Optional[List[AIImageAnalysisResponse]] = None
    ai_model_used: Optional[str] = None
    ai_tokens_used: Optional[int] = None
    ai_processing_time_ms: Optional[int] = None

    # Status
    status: str
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None


class VehiclePipelineStatus(BaseModel):
    """Pipeline status"""
    is_running: bool
    current_reference: Optional[str] = None
    current_event_titulo: Optional[str] = None
    total_processed: int
    total_failed: int
    total_pending: int


@router.get("/event/{reference}", response_model=EventVehicleDataResponse)
async def get_event_vehicle_data(reference: str):
    """
    Get cached vehicle data for a specific auction event.

    Returns vehicle info, insurance status, and market comparison
    if already processed. Returns status='pending' if not yet processed.
    """
    from database import get_db, EventVehicleDataDB
    from sqlalchemy import select
    import json

    async with get_db() as db:
        result = await db.session.execute(
            select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
        )
        vehicle_data = result.scalar_one_or_none()

        if not vehicle_data:
            return EventVehicleDataResponse(
                reference=reference,
                status='not_found'
            )

        # Parse market listings if available
        listings = None
        if vehicle_data.market_listings:
            try:
                listings_raw = json.loads(vehicle_data.market_listings)
                listings = [
                    MarketListingResponse(
                        titulo=l.get('titulo', ''),
                        preco=l.get('preco', 0),
                        params=l.get('params')
                    )
                    for l in listings_raw
                ]
            except:
                pass

        # Parse AI fields
        ai_questions = None
        if vehicle_data.ai_questions_results:
            try:
                q_raw = json.loads(vehicle_data.ai_questions_results)
                ai_questions = [
                    AIQuestionResultResponse(
                        question_id=q.get('question_id', ''),
                        question=q.get('question', ''),
                        answer=q.get('answer', ''),
                        confidence=q.get('confidence', 0),
                        time_ms=q.get('time_ms', 0)
                    )
                    for q in q_raw
                ]
            except:
                pass

        ai_image_analyses = None
        if vehicle_data.ai_image_analyses:
            try:
                img_raw = json.loads(vehicle_data.ai_image_analyses)
                ai_image_analyses = [
                    AIImageAnalysisResponse(
                        image_url=img.get('image_url', ''),
                        description=img.get('description', ''),
                        condition=img.get('condition', 'unknown'),
                        issues_found=img.get('issues_found', []),
                        confidence=img.get('confidence', 0)
                    )
                    for img in img_raw
                ]
            except:
                pass

        ai_pros = None
        ai_cons = None
        if vehicle_data.ai_pros:
            try:
                ai_pros = json.loads(vehicle_data.ai_pros)
            except:
                pass
        if vehicle_data.ai_cons:
            try:
                ai_cons = json.loads(vehicle_data.ai_cons)
            except:
                pass

        return EventVehicleDataResponse(
            reference=vehicle_data.reference,
            matricula=vehicle_data.matricula,
            event_titulo=vehicle_data.event_titulo,
            event_valor_base=float(vehicle_data.event_valor_base) if vehicle_data.event_valor_base else None,
            event_lance_atual=float(vehicle_data.event_lance_atual) if vehicle_data.event_lance_atual else None,
            marca=vehicle_data.marca,
            modelo=vehicle_data.modelo,
            versao=vehicle_data.versao,
            ano=vehicle_data.ano,
            combustivel=vehicle_data.combustivel,
            potencia_cv=vehicle_data.potencia_cv,
            cor=vehicle_data.cor,
            vin=vehicle_data.vin,
            tem_seguro=vehicle_data.tem_seguro,
            seguradora=vehicle_data.seguradora,
            seguro_data_fim=vehicle_data.seguro_data_fim,
            market_num_resultados=vehicle_data.market_num_resultados,
            market_preco_min=float(vehicle_data.market_preco_min) if vehicle_data.market_preco_min else None,
            market_preco_max=float(vehicle_data.market_preco_max) if vehicle_data.market_preco_max else None,
            market_preco_medio=float(vehicle_data.market_preco_medio) if vehicle_data.market_preco_medio else None,
            market_preco_mediana=float(vehicle_data.market_preco_mediana) if vehicle_data.market_preco_mediana else None,
            market_fonte=vehicle_data.market_fonte,
            market_listings=listings,
            poupanca_estimada=float(vehicle_data.poupanca_estimada) if vehicle_data.poupanca_estimada else None,
            desconto_percentagem=vehicle_data.desconto_percentagem,
            ai_score=vehicle_data.ai_score,
            ai_recommendation=vehicle_data.ai_recommendation,
            ai_summary=vehicle_data.ai_summary,
            ai_pros=ai_pros,
            ai_cons=ai_cons,
            ai_questions=ai_questions,
            ai_image_analyses=ai_image_analyses,
            ai_model_used=vehicle_data.ai_model_used,
            ai_tokens_used=vehicle_data.ai_tokens_used,
            ai_processing_time_ms=vehicle_data.ai_processing_time_ms,
            status=vehicle_data.status,
            error_message=vehicle_data.error_message,
            processed_at=vehicle_data.processed_at
        )


@router.post("/event/{reference}/process")
async def process_event_vehicle(reference: str, background_tasks: BackgroundTasks):
    """
    Trigger vehicle data processing for a specific event.
    Runs in background and returns immediately.
    """
    from vehicle_pipeline import get_vehicle_pipeline_manager

    pipeline = get_vehicle_pipeline_manager()

    # Run in background
    background_tasks.add_task(pipeline.process_single, reference)

    return {
        "status": "queued",
        "message": f"Vehicle data processing queued for {reference}",
        "reference": reference
    }


@router.get("/pipeline/status", response_model=VehiclePipelineStatus)
async def get_vehicle_pipeline_status():
    """Get vehicle pipeline processing status"""
    from database import get_db, EventVehicleDataDB, EventDB
    from sqlalchemy import select, func, and_
    from vehicle_pipeline import get_vehicle_pipeline_manager

    pipeline = get_vehicle_pipeline_manager()

    # Count pending events (vehicles with matricula not yet processed)
    async with get_db() as db:
        subquery = select(EventVehicleDataDB.reference).where(
            EventVehicleDataDB.status.in_(['completed', 'processing'])
        )

        pending_result = await db.session.execute(
            select(func.count(EventDB.reference)).where(
                and_(
                    EventDB.tipo_id == 2,
                    EventDB.matricula.isnot(None),
                    EventDB.matricula != '',
                    EventDB.terminado == False,
                    EventDB.cancelado == False,
                    EventDB.reference.notin_(subquery)
                )
            )
        )
        pending_count = pending_result.scalar() or 0

    return VehiclePipelineStatus(
        is_running=pipeline.is_running,
        current_reference=pipeline.current_reference,
        current_event_titulo=pipeline.current_event_titulo,
        total_processed=pipeline.total_processed,
        total_failed=pipeline.total_failed,
        total_pending=pending_count
    )


@router.post("/pipeline/start")
async def start_vehicle_pipeline(background_tasks: BackgroundTasks):
    """Start the vehicle data pipeline"""
    from vehicle_pipeline import get_vehicle_pipeline_manager

    pipeline = get_vehicle_pipeline_manager()

    if pipeline.is_running:
        return {"status": "already_running", "message": "Vehicle pipeline is already running"}

    background_tasks.add_task(pipeline.start)

    return {"status": "starting", "message": "Vehicle pipeline is starting"}


@router.post("/pipeline/stop")
async def stop_vehicle_pipeline():
    """Stop the vehicle data pipeline"""
    from vehicle_pipeline import get_vehicle_pipeline_manager

    pipeline = get_vehicle_pipeline_manager()
    await pipeline.stop()

    return {"status": "stopped", "message": "Vehicle pipeline stopped"}


@router.get("/events/list")
async def list_vehicle_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, completed, failed"),
):
    """
    List vehicle events with their processing status.
    Shows events that have matricula and their market comparison status.
    """
    from database import get_db, EventDB, EventVehicleDataDB
    from sqlalchemy import select, func, outerjoin

    async with get_db() as db:
        # Get vehicle events with their processing status
        query = (
            select(
                EventDB.reference,
                EventDB.titulo,
                EventDB.matricula,
                EventDB.valor_base,
                EventDB.lance_atual,
                EventDB.data_fim,
                EventVehicleDataDB.status,
                EventVehicleDataDB.marca,
                EventVehicleDataDB.modelo,
                EventVehicleDataDB.market_preco_medio,
                EventVehicleDataDB.poupanca_estimada,
            )
            .outerjoin(EventVehicleDataDB, EventDB.reference == EventVehicleDataDB.reference)
            .where(
                and_(
                    EventDB.tipo_id == 2,
                    EventDB.matricula.isnot(None),
                    EventDB.matricula != '',
                    EventDB.terminado == False,
                    EventDB.cancelado == False,
                )
            )
        )

        # Filter by status
        if status:
            if status == 'pending':
                query = query.where(EventVehicleDataDB.status.is_(None))
            else:
                query = query.where(EventVehicleDataDB.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(EventDB.data_fim.asc()).offset(offset).limit(page_size)

        result = await db.session.execute(query)
        events = result.all()

        return {
            "events": [
                {
                    "reference": e.reference,
                    "titulo": e.titulo,
                    "matricula": e.matricula,
                    "valor_base": float(e.valor_base) if e.valor_base else None,
                    "lance_atual": float(e.lance_atual) if e.lance_atual else None,
                    "data_fim": e.data_fim.isoformat() if e.data_fim else None,
                    "status": e.status or "pending",
                    "marca": e.marca,
                    "modelo": e.modelo,
                    "market_preco_medio": float(e.market_preco_medio) if e.market_preco_medio else None,
                    "poupanca_estimada": float(e.poupanca_estimada) if e.poupanca_estimada else None,
                }
                for e in events
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(events) < total
        }


# ============== COMPLETE ANALYSIS ENDPOINT ==============

@router.post("/event/{reference}/complete-analysis")
async def complete_vehicle_analysis(
    reference: str,
    include_market: bool = Query(True, description="Include market prices lookup"),
    include_ai: bool = Query(True, description="Include AI analysis"),
    analyze_images: bool = Query(True, description="Analyze images with LLaVA"),
    max_images: int = Query(3, ge=1, le=5, description="Max images to analyze")
):
    """
    Complete vehicle analysis in one request (synchronous).

    Performs ALL analysis steps:
    1. Vehicle info from InfoMatricula API
    2. Insurance status check
    3. Market prices from StandVirtual/AutoUncle (optional)
    4. AI batch questions via Ollama (optional)
    5. Image analysis via LLaVA (optional)

    Returns complete analysis data and saves to database.
    Note: This may take 30-60 seconds depending on options selected.
    """
    from database import get_db, EventDB, EventVehicleDataDB
    from services.vehicle_lookup import (
        lookup_plate_infomatricula_api,
        check_insurance_api,
        get_market_prices as search_market_prices,
        decode_portuguese_plate
    )
    from services.ai_analysis_service import get_enhanced_ai_service
    from sqlalchemy import select
    import time
    import json

    start_time = time.time()
    errors = []

    # 1. Get event from database
    async with get_db() as db:
        result = await db.session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail=f"Event {reference} not found")

        if not event.matricula:
            raise HTTPException(status_code=400, detail=f"Event {reference} has no matricula")

        # Create event dict for analysis
        event_dict = {
            'reference': event.reference,
            'titulo': event.titulo,
            'matricula': event.matricula,
            'valor_base': float(event.valor_base) if event.valor_base else None,
            'lance_atual': float(event.lance_atual) if event.lance_atual else None,
            'descricao': event.descricao,
            'fotos': event.fotos,
        }

        # Get or create vehicle data record
        vd_result = await db.session.execute(
            select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
        )
        vehicle_data = vd_result.scalar_one_or_none()

        if not vehicle_data:
            vehicle_data = EventVehicleDataDB(
                reference=reference,
                matricula=event.matricula,
                event_titulo=event.titulo,
                event_valor_base=event_dict['valor_base'],
                event_lance_atual=event_dict['lance_atual'],
                status='processing'
            )
            db.session.add(vehicle_data)
        else:
            vehicle_data.status = 'processing'

        await db.session.commit()

    normalized_plate = _normalize_plate(event_dict['matricula'])

    # 2. Get vehicle info from InfoMatricula API
    vehicle_info = {}
    try:
        vehicle_info = await lookup_plate_infomatricula_api(normalized_plate)
        if 'error' not in vehicle_info:
            async with get_db() as db:
                result = await db.session.execute(
                    select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                )
                vd = result.scalar_one()
                vd.marca = vehicle_info.get('marca')
                vd.modelo = vehicle_info.get('modelo')
                vd.versao = vehicle_info.get('versao')
                vd.ano = vehicle_info.get('ano')
                vd.combustivel = vehicle_info.get('combustivel')
                vd.potencia_cv = vehicle_info.get('potencia_cv')
                vd.potencia_kw = vehicle_info.get('potencia_kw')
                vd.cor = vehicle_info.get('cor')
                vd.categoria = vehicle_info.get('categoria')
                vd.vin = vehicle_info.get('vin')
                vd.tipo_proprietario = vehicle_info.get('tipo_proprietario')
                vd.origem = vehicle_info.get('origem')
                await db.session.commit()
        else:
            errors.append(f"Vehicle info: {vehicle_info.get('error')}")
    except Exception as e:
        errors.append(f"Vehicle info: {str(e)}")

    # 3. Check insurance
    insurance_info = {}
    try:
        insurance_info = await check_insurance_api(normalized_plate)
        if 'error' not in insurance_info:
            async with get_db() as db:
                result = await db.session.execute(
                    select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                )
                vd = result.scalar_one()
                vd.tem_seguro = insurance_info.get('tem_seguro')
                vd.seguradora = insurance_info.get('seguradora')
                vd.seguro_apolice = insurance_info.get('apolice')
                vd.seguro_data_fim = insurance_info.get('data_fim')
                await db.session.commit()
        else:
            errors.append(f"Insurance: {insurance_info.get('error')}")
    except Exception as e:
        errors.append(f"Insurance: {str(e)}")

    # 4. Market prices (optional, may fail due to Playwright)
    market_data = None
    if include_market and vehicle_info.get('marca'):
        try:
            market_data = await search_market_prices(
                marca=vehicle_info.get('marca'),
                modelo=vehicle_info.get('modelo'),
                ano=vehicle_info.get('ano'),
                combustivel=vehicle_info.get('combustivel'),
                km=None,
                debug=False
            )
            if market_data:
                async with get_db() as db:
                    result = await db.session.execute(
                        select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                    )
                    vd = result.scalar_one()
                    vd.market_num_resultados = market_data.num_resultados
                    vd.market_preco_min = market_data.preco_min
                    vd.market_preco_max = market_data.preco_max
                    vd.market_preco_medio = market_data.preco_medio
                    vd.market_preco_mediana = market_data.preco_mediana
                    vd.market_fonte = market_data.fonte
                    vd.market_listings = json.dumps(market_data.listings[:10])

                    # Calculate savings
                    valor_leilao = event_dict['valor_base'] or event_dict['lance_atual'] or 0
                    if valor_leilao > 0 and market_data.preco_medio > 0:
                        vd.poupanca_estimada = market_data.preco_medio - valor_leilao
                        vd.desconto_percentagem = ((market_data.preco_medio - valor_leilao) / market_data.preco_medio) * 100

                    await db.session.commit()
        except Exception as e:
            errors.append(f"Market prices: {str(e)}")

    # 5. AI Analysis (optional)
    ai_result = None
    if include_ai:
        try:
            ai_service = get_enhanced_ai_service()

            # Check if Ollama is available
            models_check = await ai_service.check_models()
            if 'error' not in models_check and models_check.get('text_model_available'):
                ai_result = await ai_service.analyze_vehicle(
                    event_dict,
                    analyze_images=analyze_images,
                    max_images=max_images
                )

                # Save AI results to database
                async with get_db() as db:
                    result = await db.session.execute(
                        select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
                    )
                    vd = result.scalar_one()
                    vd.ai_score = ai_result.score
                    vd.ai_recommendation = ai_result.recommendation
                    vd.ai_summary = ai_result.summary
                    vd.ai_pros = json.dumps(ai_result.pros)
                    vd.ai_cons = json.dumps(ai_result.cons)

                    # Save question results
                    questions_json = [
                        {
                            "question_id": q.question_id,
                            "question": q.question,
                            "answer": q.answer,
                            "confidence": q.confidence,
                            "time_ms": q.time_ms
                        }
                        for q in ai_result.questions
                    ]
                    vd.ai_questions_results = json.dumps(questions_json)

                    # Save image analyses
                    images_json = [
                        {
                            "image_url": img.image_url,
                            "description": img.description,
                            "condition": img.condition,
                            "issues_found": img.issues_found,
                            "confidence": img.confidence
                        }
                        for img in ai_result.image_analyses
                    ]
                    vd.ai_image_analyses = json.dumps(images_json)

                    vd.ai_model_used = ",".join(ai_result.models_used)
                    vd.ai_tokens_used = ai_result.total_tokens
                    vd.ai_processing_time_ms = ai_result.total_time_ms

                    await db.session.commit()
            else:
                errors.append(f"AI: Ollama not available or model not found")
        except Exception as e:
            errors.append(f"AI analysis: {str(e)}")

    # Mark as completed
    total_time_ms = int((time.time() - start_time) * 1000)

    async with get_db() as db:
        result = await db.session.execute(
            select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
        )
        vd = result.scalar_one()
        vd.status = 'completed'
        vd.processed_at = datetime.utcnow()
        vd.error_message = "; ".join(errors) if errors else None
        await db.session.commit()

    # Build response
    async with get_db() as db:
        result = await db.session.execute(
            select(EventVehicleDataDB).where(EventVehicleDataDB.reference == reference)
        )
        vd = result.scalar_one()

        # Parse stored JSON fields
        market_listings = None
        if vd.market_listings:
            try:
                listings_raw = json.loads(vd.market_listings)
                market_listings = [
                    MarketListingResponse(
                        titulo=l.get('titulo', ''),
                        preco=l.get('preco', 0),
                        params=l.get('params')
                    )
                    for l in listings_raw
                ]
            except:
                pass

        ai_questions = None
        if vd.ai_questions_results:
            try:
                q_raw = json.loads(vd.ai_questions_results)
                ai_questions = [
                    AIQuestionResultResponse(
                        question_id=q.get('question_id', ''),
                        question=q.get('question', ''),
                        answer=q.get('answer', ''),
                        confidence=q.get('confidence', 0),
                        time_ms=q.get('time_ms', 0)
                    )
                    for q in q_raw
                ]
            except:
                pass

        ai_image_analyses = None
        if vd.ai_image_analyses:
            try:
                img_raw = json.loads(vd.ai_image_analyses)
                ai_image_analyses = [
                    AIImageAnalysisResponse(
                        image_url=img.get('image_url', ''),
                        description=img.get('description', ''),
                        condition=img.get('condition', 'unknown'),
                        issues_found=img.get('issues_found', []),
                        confidence=img.get('confidence', 0)
                    )
                    for img in img_raw
                ]
            except:
                pass

        ai_pros = None
        ai_cons = None
        if vd.ai_pros:
            try:
                ai_pros = json.loads(vd.ai_pros)
            except:
                pass
        if vd.ai_cons:
            try:
                ai_cons = json.loads(vd.ai_cons)
            except:
                pass

        return {
            "reference": vd.reference,
            "matricula": vd.matricula,
            "event_titulo": vd.event_titulo,
            "event_valor_base": float(vd.event_valor_base) if vd.event_valor_base else None,
            "event_lance_atual": float(vd.event_lance_atual) if vd.event_lance_atual else None,

            # Vehicle info
            "marca": vd.marca,
            "modelo": vd.modelo,
            "versao": vd.versao,
            "ano": vd.ano,
            "combustivel": vd.combustivel,
            "potencia_cv": vd.potencia_cv,
            "cor": vd.cor,
            "vin": vd.vin,

            # Insurance
            "tem_seguro": vd.tem_seguro,
            "seguradora": vd.seguradora,
            "seguro_data_fim": vd.seguro_data_fim,

            # Market comparison
            "market_num_resultados": vd.market_num_resultados,
            "market_preco_min": float(vd.market_preco_min) if vd.market_preco_min else None,
            "market_preco_max": float(vd.market_preco_max) if vd.market_preco_max else None,
            "market_preco_medio": float(vd.market_preco_medio) if vd.market_preco_medio else None,
            "market_preco_mediana": float(vd.market_preco_mediana) if vd.market_preco_mediana else None,
            "market_fonte": vd.market_fonte,
            "market_listings": market_listings,
            "poupanca_estimada": float(vd.poupanca_estimada) if vd.poupanca_estimada else None,
            "desconto_percentagem": vd.desconto_percentagem,

            # AI Analysis
            "ai_score": vd.ai_score,
            "ai_recommendation": vd.ai_recommendation,
            "ai_summary": vd.ai_summary,
            "ai_pros": ai_pros,
            "ai_cons": ai_cons,
            "ai_questions": ai_questions,
            "ai_image_analyses": ai_image_analyses,
            "ai_model_used": vd.ai_model_used,
            "ai_tokens_used": vd.ai_tokens_used,
            "ai_processing_time_ms": vd.ai_processing_time_ms,

            # Status
            "status": vd.status,
            "error_message": vd.error_message,
            "processed_at": vd.processed_at.isoformat() if vd.processed_at else None,

            # Metadata
            "total_processing_time_ms": total_time_ms,
            "errors": errors
        }
