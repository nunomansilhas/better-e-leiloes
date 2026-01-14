"""
AI Tips Router
Endpoints for AI-generated event analysis and tips.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import json

router = APIRouter(prefix="/api/ai", tags=["AI Tips"])


# Response models
class AiTipResponse(BaseModel):
    reference: str
    event_titulo: Optional[str]
    event_tipo: Optional[str]
    event_subtipo: Optional[str]
    event_distrito: Optional[str]
    event_valor_base: Optional[float]
    tip_summary: Optional[str]
    tip_analysis: Optional[str]
    tip_pros: List[str]
    tip_cons: List[str]
    tip_recommendation: Optional[str]
    tip_confidence: Optional[float]
    status: str
    error_message: Optional[str]
    model_used: Optional[str]
    tokens_used: Optional[int]
    processing_time_ms: Optional[int]
    created_at: datetime
    processed_at: Optional[datetime]


class AiPipelineStatus(BaseModel):
    is_running: bool
    current_reference: Optional[str]
    current_event_titulo: Optional[str]
    total_processed: int
    total_failed: int
    total_pending: int
    last_started_at: Optional[datetime]
    last_completed_at: Optional[datetime]
    ollama_status: dict


class AiTipListResponse(BaseModel):
    tips: List[AiTipResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


@router.get("/health")
async def ai_health():
    """Check AI service health (Ollama connectivity)"""
    from services.ollama_service import get_ollama_service

    service = get_ollama_service()
    health = await service.check_health()

    return {
        "service": "ollama",
        "status": "healthy" if health.get("healthy") else "unhealthy",
        "details": health
    }


@router.get("/tips", response_model=AiTipListResponse)
async def list_tips(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed"),
    search: Optional[str] = Query(None, description="Search by reference or title"),
    tipo: Optional[str] = Query(None, description="Filter by event type: imoveis, veiculos"),
):
    """List AI tips with pagination and filters"""
    from database import get_db, EventAiTipDB
    from sqlalchemy import select, func, or_

    async with get_db() as db:
        # Base query
        query = select(EventAiTipDB)
        count_query = select(func.count(EventAiTipDB.id))

        # Apply filters
        if status:
            query = query.where(EventAiTipDB.status == status)
            count_query = count_query.where(EventAiTipDB.status == status)

        if search:
            search_filter = or_(
                EventAiTipDB.reference.ilike(f"%{search}%"),
                EventAiTipDB.event_titulo.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if tipo:
            tipo_map = {"imoveis": "Imovel", "veiculos": "Veiculo"}
            if tipo in tipo_map:
                query = query.where(EventAiTipDB.event_tipo == tipo_map[tipo])
                count_query = count_query.where(EventAiTipDB.event_tipo == tipo_map[tipo])

        # Get total count
        total_result = await db.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(EventAiTipDB.created_at.desc()).offset(offset).limit(page_size)

        # Execute
        result = await db.session.execute(query)
        tips_db = result.scalars().all()

        # Convert to response
        tips = []
        for tip in tips_db:
            tips.append(AiTipResponse(
                reference=tip.reference,
                event_titulo=tip.event_titulo,
                event_tipo=tip.event_tipo,
                event_subtipo=tip.event_subtipo,
                event_distrito=tip.event_distrito,
                event_valor_base=float(tip.event_valor_base) if tip.event_valor_base else None,
                tip_summary=tip.tip_summary,
                tip_analysis=tip.tip_analysis,
                tip_pros=json.loads(tip.tip_pros) if tip.tip_pros else [],
                tip_cons=json.loads(tip.tip_cons) if tip.tip_cons else [],
                tip_recommendation=tip.tip_recommendation,
                tip_confidence=tip.tip_confidence,
                status=tip.status,
                error_message=tip.error_message,
                model_used=tip.model_used,
                tokens_used=tip.tokens_used,
                processing_time_ms=tip.processing_time_ms,
                created_at=tip.created_at,
                processed_at=tip.processed_at
            ))

        return AiTipListResponse(
            tips=tips,
            total=total,
            page=page,
            page_size=page_size,
            has_more=offset + len(tips) < total
        )


@router.get("/tips/{reference}", response_model=AiTipResponse)
async def get_tip(reference: str):
    """Get AI tip for a specific event"""
    from database import get_db, EventAiTipDB
    from sqlalchemy import select

    async with get_db() as db:
        query = select(EventAiTipDB).where(EventAiTipDB.reference == reference)
        result = await db.session.execute(query)
        tip = result.scalar_one_or_none()

        if not tip:
            raise HTTPException(status_code=404, detail=f"No AI tip found for event {reference}")

        return AiTipResponse(
            reference=tip.reference,
            event_titulo=tip.event_titulo,
            event_tipo=tip.event_tipo,
            event_subtipo=tip.event_subtipo,
            event_distrito=tip.event_distrito,
            event_valor_base=float(tip.event_valor_base) if tip.event_valor_base else None,
            tip_summary=tip.tip_summary,
            tip_analysis=tip.tip_analysis,
            tip_pros=json.loads(tip.tip_pros) if tip.tip_pros else [],
            tip_cons=json.loads(tip.tip_cons) if tip.tip_cons else [],
            tip_recommendation=tip.tip_recommendation,
            tip_confidence=tip.tip_confidence,
            status=tip.status,
            error_message=tip.error_message,
            model_used=tip.model_used,
            tokens_used=tip.tokens_used,
            processing_time_ms=tip.processing_time_ms,
            created_at=tip.created_at,
            processed_at=tip.processed_at
        )


@router.post("/tips/{reference}/analyze")
async def analyze_event(reference: str, background_tasks: BackgroundTasks):
    """
    Trigger AI analysis for a specific event.
    The analysis runs in the background.
    """
    from database import get_db, EventDB, EventAiTipDB
    from sqlalchemy import select

    async with get_db() as db:
        # Check if event exists
        event_query = select(EventDB).where(EventDB.reference == reference)
        event_result = await db.session.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail=f"Event {reference} not found")

        # Check if it's a supported type (imovel or veiculo)
        if event.tipo_id not in [1, 2]:
            raise HTTPException(
                status_code=400,
                detail=f"AI analysis only supports Imoveis (tipo_id=1) and Veiculos (tipo_id=2). This event is tipo_id={event.tipo_id}"
            )

        # Check if tip already exists
        tip_query = select(EventAiTipDB).where(EventAiTipDB.reference == reference)
        tip_result = await db.session.execute(tip_query)
        existing_tip = tip_result.scalar_one_or_none()

        if existing_tip and existing_tip.status == "completed":
            return {
                "status": "already_completed",
                "message": f"AI analysis already completed for {reference}",
                "tip_id": existing_tip.id
            }

        # Create or update tip entry as pending
        if existing_tip:
            existing_tip.status = "pending"
            existing_tip.error_message = None
        else:
            new_tip = EventAiTipDB(
                reference=reference,
                event_titulo=event.titulo,
                event_tipo=event.tipo,
                event_subtipo=event.subtipo,
                event_distrito=event.distrito,
                event_valor_base=event.valor_base,
                status="pending"
            )
            db.session.add(new_tip)

        await db.session.commit()

    # Trigger background analysis
    background_tasks.add_task(_run_single_analysis, reference)

    return {
        "status": "queued",
        "message": f"AI analysis queued for {reference}",
        "reference": reference
    }


async def _run_single_analysis(reference: str):
    """Run AI analysis for a single event (background task)"""
    from database import get_db, EventDB, EventAiTipDB
    from services.ollama_service import get_ollama_service
    from sqlalchemy import select
    import json

    async with get_db() as db:
        # Get event data
        event_query = select(EventDB).where(EventDB.reference == reference)
        event_result = await db.session.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return

        # Get tip entry
        tip_query = select(EventAiTipDB).where(EventAiTipDB.reference == reference)
        tip_result = await db.session.execute(tip_query)
        tip = tip_result.scalar_one_or_none()

        if not tip:
            return

        # Update status to processing
        tip.status = "processing"
        await db.session.commit()

        try:
            # Convert event to dict for analysis
            event_dict = {
                "reference": event.reference,
                "titulo": event.titulo,
                "tipo_id": event.tipo_id,
                "tipo": event.tipo,
                "subtipo": event.subtipo,
                "tipologia": event.tipologia,
                "distrito": event.distrito,
                "concelho": event.concelho,
                "freguesia": event.freguesia,
                "valor_base": float(event.valor_base) if event.valor_base else 0,
                "valor_abertura": float(event.valor_abertura) if event.valor_abertura else 0,
                "lance_atual": float(event.lance_atual) if event.lance_atual else 0,
                "area_total": event.area_total,
                "area_privativa": event.area_privativa,
                "matricula": event.matricula,
                "descricao": event.descricao,
                "observacoes": event.observacoes,
            }

            # Run analysis
            ollama = get_ollama_service()
            result = await ollama.analyze_event(event_dict)

            # Update tip with results
            tip.tip_summary = result.summary
            tip.tip_analysis = result.analysis
            tip.tip_pros = json.dumps(result.pros)
            tip.tip_cons = json.dumps(result.cons)
            tip.tip_recommendation = result.recommendation
            tip.tip_confidence = result.confidence
            tip.tokens_used = result.tokens_used
            tip.processing_time_ms = result.processing_time_ms
            tip.model_used = result.model_used
            tip.status = "completed"
            tip.processed_at = datetime.utcnow()
            tip.error_message = None

        except Exception as e:
            tip.status = "failed"
            tip.error_message = str(e)[:500]

        tip.updated_at = datetime.utcnow()
        await db.session.commit()


@router.get("/pipeline/status", response_model=AiPipelineStatus)
async def get_pipeline_status():
    """Get AI pipeline processing status"""
    from database import get_db, AiPipelineStateDB, EventAiTipDB
    from services.ollama_service import get_ollama_service
    from sqlalchemy import select, func

    async with get_db() as db:
        # Get pipeline state
        query = select(AiPipelineStateDB).where(AiPipelineStateDB.pipeline_name == "ai_tips")
        result = await db.session.execute(query)
        state = result.scalar_one_or_none()

        # Count pending tips
        pending_query = select(func.count(EventAiTipDB.id)).where(EventAiTipDB.status == "pending")
        pending_result = await db.session.execute(pending_query)
        pending_count = pending_result.scalar() or 0

        # Get Ollama status
        ollama = get_ollama_service()
        ollama_status = await ollama.check_health()

        if state:
            return AiPipelineStatus(
                is_running=state.is_running,
                current_reference=state.current_reference,
                current_event_titulo=state.current_event_titulo,
                total_processed=state.total_processed,
                total_failed=state.total_failed,
                total_pending=pending_count,
                last_started_at=state.last_started_at,
                last_completed_at=state.last_completed_at,
                ollama_status=ollama_status
            )
        else:
            return AiPipelineStatus(
                is_running=False,
                current_reference=None,
                current_event_titulo=None,
                total_processed=0,
                total_failed=0,
                total_pending=pending_count,
                last_started_at=None,
                last_completed_at=None,
                ollama_status=ollama_status
            )


@router.post("/pipeline/start")
async def start_pipeline(background_tasks: BackgroundTasks):
    """Start the AI analysis pipeline"""
    from ai_pipeline import get_ai_pipeline_manager

    pipeline = get_ai_pipeline_manager()

    if pipeline.is_running:
        return {"status": "already_running", "message": "AI pipeline is already running"}

    background_tasks.add_task(pipeline.start)

    return {"status": "starting", "message": "AI pipeline is starting"}


@router.post("/pipeline/stop")
async def stop_pipeline():
    """Stop the AI analysis pipeline"""
    from ai_pipeline import get_ai_pipeline_manager

    pipeline = get_ai_pipeline_manager()
    await pipeline.stop()

    return {"status": "stopped", "message": "AI pipeline stopped"}


@router.get("/stats")
async def get_ai_stats():
    """Get AI tips statistics"""
    from database import get_db, EventAiTipDB
    from sqlalchemy import select, func

    async with get_db() as db:
        # Count by status
        status_query = select(
            EventAiTipDB.status,
            func.count(EventAiTipDB.id)
        ).group_by(EventAiTipDB.status)
        status_result = await db.session.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        # Count by recommendation
        rec_query = select(
            EventAiTipDB.tip_recommendation,
            func.count(EventAiTipDB.id)
        ).where(EventAiTipDB.status == "completed").group_by(EventAiTipDB.tip_recommendation)
        rec_result = await db.session.execute(rec_query)
        rec_counts = {row[0]: row[1] for row in rec_result.all() if row[0]}

        # Average confidence
        conf_query = select(func.avg(EventAiTipDB.tip_confidence)).where(
            EventAiTipDB.status == "completed"
        )
        conf_result = await db.session.execute(conf_query)
        avg_confidence = conf_result.scalar()

        # Average processing time
        time_query = select(func.avg(EventAiTipDB.processing_time_ms)).where(
            EventAiTipDB.status == "completed"
        )
        time_result = await db.session.execute(time_query)
        avg_time_ms = time_result.scalar()

        return {
            "by_status": status_counts,
            "by_recommendation": rec_counts,
            "avg_confidence": round(avg_confidence, 2) if avg_confidence else None,
            "avg_processing_time_ms": int(avg_time_ms) if avg_time_ms else None,
            "total": sum(status_counts.values())
        }
