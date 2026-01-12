"""
E-Leiloes Public API - Read-Only
Lightweight API for public frontend consumption
Connects to remote MySQL database
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
load_dotenv()

from database import get_session, EventDB, PriceHistoryDB, PipelineStateDB, init_db
from sqlalchemy import select, func, desc, and_, or_


# ============ Pydantic Models ============

class EventSummary(BaseModel):
    reference: str
    titulo: Optional[str] = None
    capa: Optional[str] = None
    tipo_id: Optional[int] = None
    tipo: Optional[str] = None
    subtipo: Optional[str] = None
    valor_base: Optional[float] = None
    valor_minimo: Optional[float] = None
    lance_atual: float = 0
    data_fim: Optional[datetime] = None
    distrito: Optional[str] = None
    concelho: Optional[str] = None
    terminado: bool = False
    cancelado: bool = False

    class Config:
        from_attributes = True


class EventDetail(BaseModel):
    reference: str
    titulo: Optional[str] = None
    capa: Optional[str] = None
    tipo_id: Optional[int] = None
    tipo: Optional[str] = None
    subtipo: Optional[str] = None
    tipologia: Optional[str] = None
    valor_base: Optional[float] = None
    valor_abertura: Optional[float] = None
    valor_minimo: Optional[float] = None
    lance_atual: float = 0
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    distrito: Optional[str] = None
    concelho: Optional[str] = None
    freguesia: Optional[str] = None
    morada: Optional[str] = None
    area_total: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    descricao: Optional[str] = None
    fotos: Optional[List[str]] = None
    terminado: bool = False
    cancelado: bool = False
    iniciado: bool = False

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total: int
    active: int
    ending_soon: int
    by_type: dict
    by_distrito: dict


class PricePoint(BaseModel):
    preco: float
    timestamp: Optional[datetime] = None


# ============ App Setup ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ Connected to database")
    yield


app = FastAPI(
    title="E-Leiloes Public API",
    description="Read-only API for public auction data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - allow all origins for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ============ API Routes ============

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "mode": "live",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get general statistics"""
    async with get_session() as session:
        now = datetime.utcnow()
        soon = now + timedelta(hours=24)

        total = await session.scalar(select(func.count()).select_from(EventDB))
        active = await session.scalar(
            select(func.count()).select_from(EventDB).where(
                and_(EventDB.terminado == 0, EventDB.cancelado == 0)
            )
        )
        ending_soon = await session.scalar(
            select(func.count()).select_from(EventDB).where(
                and_(
                    EventDB.terminado == 0,
                    EventDB.cancelado == 0,
                    EventDB.data_fim >= now,
                    EventDB.data_fim <= soon
                )
            )
        )

        type_query = await session.execute(
            select(EventDB.tipo_id, func.count())
            .where(and_(EventDB.terminado == 0, EventDB.cancelado == 0))
            .group_by(EventDB.tipo_id)
        )
        by_type = {str(t or 0): c for t, c in type_query.all()}

        distrito_query = await session.execute(
            select(EventDB.distrito, func.count())
            .where(
                and_(
                    EventDB.terminado == 0,
                    EventDB.cancelado == 0,
                    EventDB.distrito != None
                )
            )
            .group_by(EventDB.distrito)
            .order_by(desc(func.count()))
            .limit(10)
        )
        by_distrito = {d: c for d, c in distrito_query.all()}

        return StatsResponse(
            total=total or 0,
            active=active or 0,
            ending_soon=ending_soon or 0,
            by_type=by_type,
            by_distrito=by_distrito
        )


@app.get("/api/events")
async def list_events(
    limit: int = Query(100, le=100000),
    offset: int = Query(0, ge=0),
    tipo_id: Optional[int] = None,
    distrito: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    order_by: str = "data_fim"
):
    """List events with filters - returns {events: [...]} format for dashboard compatibility"""
    async with get_session() as session:
        query = select(EventDB)

        conditions = []
        if active_only:
            conditions.append(EventDB.terminado == 0)  # Use 0 for MySQL tinyint
            conditions.append(EventDB.cancelado == 0)  # Use 0 for MySQL tinyint
        if tipo_id:
            conditions.append(EventDB.tipo_id == tipo_id)
        if distrito:
            conditions.append(EventDB.distrito == distrito)
        if search:
            conditions.append(
                or_(
                    EventDB.titulo.ilike(f"%{search}%"),
                    EventDB.reference.ilike(f"%{search}%"),
                    EventDB.descricao.ilike(f"%{search}%")
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        if order_by == "data_fim":
            query = query.order_by(EventDB.data_fim)
        elif order_by == "lance_atual":
            query = query.order_by(desc(EventDB.lance_atual))
        elif order_by == "valor_base":
            query = query.order_by(EventDB.valor_base)

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        events = result.scalars().all()

        # Convert to dict format with ativo field
        import json
        result_events = []
        for e in events:
            # Parse fotos JSON
            fotos = None
            if e.fotos:
                try:
                    fotos_data = json.loads(e.fotos)
                    if isinstance(fotos_data, list):
                        fotos = [f.get("image") or f.get("url") if isinstance(f, dict) else f for f in fotos_data]
                except:
                    pass

            result_events.append({
                "reference": e.reference,
                "titulo": e.titulo,
                "capa": e.capa,
                "fotos": fotos,
                "tipo_id": e.tipo_id,
                "tipo": e.tipo,
                "subtipo": e.subtipo,
                "valor_base": e.valor_base,
                "valor_minimo": e.valor_minimo,
                "lance_atual": e.lance_atual,
                "data_fim": e.data_fim.isoformat() if e.data_fim else None,
                "distrito": e.distrito,
                "concelho": e.concelho,
                "terminado": e.terminado,
                "cancelado": e.cancelado,
                "ativo": not e.terminado and not e.cancelado
            })

        return {"events": result_events, "total": len(result_events), "page": offset // limit + 1 if limit > 0 else 1}


@app.get("/api/events/{reference}")
async def get_event(reference: str):
    """Get event details by reference"""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(EventDB).where(EventDB.reference == reference)
            )
            event = result.scalar_one_or_none()

            if not event:
                raise HTTPException(status_code=404, detail="Event not found")

            fotos = None
            if event.fotos:
                try:
                    import json
                    fotos_data = json.loads(event.fotos)
                    if isinstance(fotos_data, list):
                        fotos = [f.get("image") or f.get("url") if isinstance(f, dict) else f for f in fotos_data]
                except:
                    pass

            # Helper to safely get attribute with default
            def safe_get(attr, default=None):
                return getattr(event, attr, default)

            def safe_date(attr):
                val = getattr(event, attr, None)
                return val.isoformat() if val else None

            # Return dict directly to avoid Pydantic validation issues with None fields
            return {
                "reference": event.reference,
                "titulo": event.titulo,
                "capa": event.capa,
                "tipo_id": event.tipo_id,
                "tipo": event.tipo,
                "subtipo": event.subtipo,
                "tipologia": safe_get('tipologia'),
                "valor_base": event.valor_base,
                "valor_abertura": safe_get('valor_abertura'),
                "valor_minimo": safe_get('valor_minimo'),
                "lance_atual": event.lance_atual or 0,
                "data_inicio": safe_date('data_inicio'),
                "data_fim": safe_date('data_fim'),
                # Location
                "distrito": event.distrito,
                "concelho": event.concelho,
                "freguesia": safe_get('freguesia'),
                "morada": safe_get('morada'),
                "morada_cp": safe_get('morada_cp'),
                "latitude": safe_get('latitude'),
                "longitude": safe_get('longitude'),
                # Areas
                "area_privativa": safe_get('area_privativa'),
                "area_dependente": safe_get('area_dependente'),
                "area_total": safe_get('area_total'),
                # Vehicle
                "matricula": safe_get('matricula'),
                # Process
                "processo_numero": safe_get('processo_numero'),
                "processo_tribunal": safe_get('processo_tribunal'),
                "processo_comarca": safe_get('processo_comarca'),
                # Ceremony
                "cerimonia_data": safe_date('cerimonia_data'),
                "cerimonia_local": safe_get('cerimonia_local'),
                "cerimonia_morada": safe_get('cerimonia_morada'),
                # Manager
                "gestor_nome": safe_get('gestor_nome'),
                "gestor_email": safe_get('gestor_email'),
                "gestor_telefone": safe_get('gestor_telefone'),
                "gestor_tipo": safe_get('gestor_tipo'),
                "gestor_cedula": safe_get('gestor_cedula'),
                # Content
                "descricao": safe_get('descricao'),
                "observacoes": safe_get('observacoes'),
                "fotos": fotos,
                # Status
                "terminado": event.terminado if event.terminado is not None else False,
                "cancelado": event.cancelado if event.cancelado is not None else False,
                "iniciado": safe_get('iniciado', False),
                "ativo": not (event.terminado or event.cancelado)
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting event {reference}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ending-soon", response_model=List[EventSummary])
async def get_ending_soon(
    hours: int = Query(24, le=72),
    limit: int = Query(50, le=200),
    tipo_id: Optional[int] = None
):
    """Get events ending soon"""
    async with get_session() as session:
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)

        query = select(EventDB).where(
            and_(
                EventDB.terminado == 0,
                EventDB.cancelado == 0,
                EventDB.data_fim >= now,
                EventDB.data_fim <= cutoff
            )
        )

        if tipo_id:
            query = query.where(EventDB.tipo_id == tipo_id)

        query = query.order_by(EventDB.data_fim).limit(limit)

        result = await session.execute(query)
        events = result.scalars().all()

        return [EventSummary.model_validate(e) for e in events]


@app.get("/api/price-history/{reference}")
async def get_price_history(reference: str, limit: int = Query(50, le=200)):
    """Get price history for an event"""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(PriceHistoryDB)
                .where(PriceHistoryDB.reference == reference)
                .order_by(PriceHistoryDB.recorded_at)
                .limit(limit)
            )
            history = result.scalars().all()

            return [{"preco": h.new_price or 0, "timestamp": h.recorded_at.isoformat() if h.recorded_at else None} for h in history if h.new_price is not None]
    except Exception as e:
        print(f"[ERROR] get_price_history({reference}): {e}", flush=True)
        return []


@app.get("/api/distritos")
async def list_distritos():
    """List all distritos with event counts"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB.distrito, func.count())
            .where(
                and_(
                    EventDB.terminado == 0,
                    EventDB.cancelado == 0,
                    EventDB.distrito != None
                )
            )
            .group_by(EventDB.distrito)
            .order_by(EventDB.distrito)
        )
        return [{"distrito": d, "count": c} for d, c in result.all()]


@app.get("/api/tipos")
async def list_tipos():
    """List event types with counts"""
    tipo_names = {
        1: "Imoveis",
        2: "Veiculos",
        3: "Equipamentos",
        4: "Mobiliario",
        5: "Maquinas",
        6: "Direitos"
    }

    async with get_session() as session:
        result = await session.execute(
            select(EventDB.tipo_id, func.count())
            .where(and_(EventDB.terminado == 0, EventDB.cancelado == 0))
            .group_by(EventDB.tipo_id)
            .order_by(EventDB.tipo_id)
        )
        return [
            {"tipo_id": t, "name": tipo_names.get(t, f"Tipo {t}"), "count": c}
            for t, c in result.all() if t
        ]


@app.get("/api/filters/subtypes/{tipo_id}")
async def get_subtypes(tipo_id: int):
    """Get subtypes for a specific tipo_id"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB.subtipo, func.count())
            .where(
                and_(
                    EventDB.terminado == 0,
                    EventDB.cancelado == 0,
                    EventDB.tipo_id == tipo_id,
                    EventDB.subtipo != None
                )
            )
            .group_by(EventDB.subtipo)
            .order_by(EventDB.subtipo)
        )
        return [
            {"subtipo": s, "count": c}
            for s, c in result.all() if s
        ]


# ============ Dashboard Endpoints (compatibility with original frontend) ============

@app.get("/api/dashboard/ending-soon")
async def dashboard_ending_soon(hours: int = 24, limit: int = 1000, include_terminated: bool = True, terminated_hours: int = 120):
    """Get events ending soon + recently terminated events.
    - hours: look ahead for active events (default 24h)
    - include_terminated: include recently terminated events (default True)
    - terminated_hours: how far back to look for terminated events (default 120h = 5 days)
    """
    async with get_session() as session:
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)

        # Get active events ending soon
        result = await session.execute(
            select(EventDB).where(
                and_(
                    EventDB.terminado == 0,
                    EventDB.cancelado == 0,
                    EventDB.data_fim >= now,
                    EventDB.data_fim <= cutoff
                )
            ).order_by(EventDB.data_fim).limit(limit)
        )
        active_events = result.scalars().all()

        # Get recently terminated events (last N hours)
        terminated_events = []
        if include_terminated:
            terminated_cutoff = now - timedelta(hours=terminated_hours)
            terminated_result = await session.execute(
                select(EventDB).where(
                    and_(
                        EventDB.terminado == 1,
                        EventDB.data_fim >= terminated_cutoff,
                        EventDB.data_fim <= now
                    )
                ).order_by(desc(EventDB.data_fim)).limit(limit)
            )
            terminated_events = terminated_result.scalars().all()

        def format_event(e, is_terminated=False):
            return {
                "reference": e.reference,
                "titulo": e.titulo,
                "tipo_id": e.tipo_id,
                "subtipo": e.subtipo,
                "distrito": e.distrito,
                "lance_atual": e.lance_atual,
                "valor_base": e.valor_base,
                "valor_abertura": e.valor_abertura,
                "valor_minimo": e.valor_minimo,
                "data_fim": e.data_fim.isoformat() if e.data_fim else None,
                "terminado": is_terminated
            }

        # Return active first, then terminated
        result_list = [format_event(e, False) for e in active_events]
        result_list.extend([format_event(e, True) for e in terminated_events])

        return result_list


@app.get("/api/dashboard/price-history/{reference}")
async def dashboard_price_history(reference: str):
    """Alias for price-history endpoint"""
    return await get_price_history(reference)


@app.get("/api/dashboard/recent-bids")
async def dashboard_recent_bids(limit: int = 30, hours: int = 120):
    """Get recent bid activity with price changes from price_history table.
    Shows only the most recent bid per event, limited to last N hours (default 120h = 5 days).
    Also includes last bids from recently terminated events."""
    async with get_session() as session:
        # Calculate cutoff time
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)

        # Get recent price history entries (already has old_price, new_price, change_amount)
        result = await session.execute(
            select(PriceHistoryDB)
            .where(
                and_(
                    PriceHistoryDB.change_amount != None,  # Only entries with actual changes
                    PriceHistoryDB.recorded_at >= cutoff   # Last N hours only
                )
            )
            .order_by(desc(PriceHistoryDB.recorded_at))
            .limit(limit * 3)  # Get more to filter down to unique events
        )
        history_entries = result.scalars().all()

        # Keep only the most recent bid per event
        seen_refs = set()
        unique_entries = []  # Stores (price_history_entry, event_for_synthetic) tuples
        for h in history_entries:
            if h.reference not in seen_refs:
                seen_refs.add(h.reference)
                unique_entries.append((h, None))

        # Also get recently terminated events to include their last bids
        terminated_result = await session.execute(
            select(EventDB).where(
                and_(
                    EventDB.terminado == 1,
                    EventDB.data_fim >= cutoff,
                    EventDB.data_fim <= now,
                    EventDB.lance_atual > 0  # Only if there was a bid
                )
            ).order_by(desc(EventDB.data_fim)).limit(limit)
        )
        terminated_events = terminated_result.scalars().all()

        # For terminated events not already in our list, get their last price history entry
        # If no price_history exists, create synthetic entry from event data
        for event in terminated_events:
            if event.reference not in seen_refs:
                # Get the last price history entry for this event
                last_bid_result = await session.execute(
                    select(PriceHistoryDB)
                    .where(PriceHistoryDB.reference == event.reference)
                    .order_by(desc(PriceHistoryDB.recorded_at))
                    .limit(1)
                )
                last_bid = last_bid_result.scalar_one_or_none()
                seen_refs.add(event.reference)
                if last_bid:
                    unique_entries.append((last_bid, None))
                else:
                    # No price history - create synthetic entry from event
                    unique_entries.append((None, event))

        if not unique_entries:
            return []

        # Get event details for references that have price_history entries
        refs_with_history = [h.reference for h, e in unique_entries if h is not None]
        events_map = {}
        if refs_with_history:
            events_result = await session.execute(
                select(EventDB).where(EventDB.reference.in_(refs_with_history))
            )
            events_map = {e.reference: e for e in events_result.scalars().all()}

        # Build response - separate active and inactive bids
        active_bids = []
        inactive_bids = []
        for h, synthetic_event in unique_entries:
            if h is not None:
                # Normal entry from price_history
                event = events_map.get(h.reference)
                ativo = True
                data_fim = None
                if event:
                    ativo = not event.terminado and not event.cancelado
                    data_fim = event.data_fim.isoformat() if event.data_fim else None

                bid = {
                    "reference": h.reference,
                    "preco_anterior": h.old_price,
                    "preco_atual": h.new_price,
                    "variacao": h.change_amount,
                    "timestamp": h.recorded_at.isoformat() if h.recorded_at else None,
                    "ativo": ativo,
                    "data_fim": data_fim
                }
                if ativo:
                    active_bids.append(bid)
                else:
                    inactive_bids.append(bid)
            else:
                # Synthetic entry from terminated event (no price_history)
                event = synthetic_event
                inactive_bids.append({
                    "reference": event.reference,
                    "preco_anterior": event.valor_base or event.valor_abertura,
                    "preco_atual": event.lance_atual,
                    "variacao": (event.lance_atual - (event.valor_base or event.valor_abertura or 0)) if event.lance_atual else None,
                    "timestamp": event.data_fim.isoformat() if event.data_fim else None,
                    "ativo": False,
                    "data_fim": event.data_fim.isoformat() if event.data_fim else None
                })

        # Sort each group by timestamp descending
        active_bids.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        inactive_bids.sort(key=lambda x: x['timestamp'] or '', reverse=True)

        # Return active bids (limited) + ALL inactive bids (so they always show)
        # This ensures terminated events are always visible
        result = active_bids[:limit] + inactive_bids

        return result


@app.get("/api/dashboard/stats-by-distrito")
async def dashboard_stats_by_distrito(limit: int = 5):
    """Get stats grouped by distrito with breakdown by type"""
    async with get_session() as session:
        # Get all active events with distrito
        result = await session.execute(
            select(EventDB.distrito, EventDB.tipo_id).where(
                and_(
                    EventDB.terminado == 0,
                    EventDB.cancelado == 0,
                    EventDB.distrito != None
                )
            )
        )
        events = result.all()

        # tipo_id mapping: 1=Imóveis, 2=Veículos, 3=Equipamentos, 4=Mobiliário, 5=Máquinas, 6=Direitos
        tipo_keys = {1: 'imoveis', 2: 'veiculos', 3: 'equipamentos', 4: 'mobiliario', 5: 'maquinas', 6: 'direitos'}

        # Aggregate by distrito
        distrito_stats = {}
        for distrito, tipo_id in events:
            if distrito not in distrito_stats:
                distrito_stats[distrito] = {'distrito': distrito, 'total': 0, 'imoveis': 0, 'veiculos': 0, 'equipamentos': 0, 'mobiliario': 0, 'maquinas': 0, 'direitos': 0}
            distrito_stats[distrito]['total'] += 1
            tipo_key = tipo_keys.get(tipo_id)
            if tipo_key:
                distrito_stats[distrito][tipo_key] += 1

        # Sort by total and limit
        sorted_distritos = sorted(distrito_stats.values(), key=lambda x: x['total'], reverse=True)[:limit]

        return sorted_distritos


@app.get("/api/dashboard/recent-events")
async def dashboard_recent_events(limit: int = 20, days: int = 7):
    """Get recently added events"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB).where(
                and_(EventDB.terminado == 0, EventDB.cancelado == 0)
            ).order_by(desc(EventDB.data_atualizacao)).limit(limit)
        )
        events = result.scalars().all()
        return [
            {
                "reference": e.reference,
                "titulo": e.titulo,
                "tipo_id": e.tipo_id,
                "subtipo": e.subtipo,
                "distrito": e.distrito,
                "lance_atual": e.lance_atual,
                "valor_base": e.valor_base,
                "data_fim": e.data_fim.isoformat() if e.data_fim else None,
                "capa": e.capa
            }
            for e in events
        ]


@app.get("/api/db/stats")
async def db_stats():
    """Get database statistics"""
    async with get_session() as session:
        total = await session.scalar(select(func.count()).select_from(EventDB))
        active = await session.scalar(
            select(func.count()).select_from(EventDB).where(
                and_(EventDB.terminado == 0, EventDB.cancelado == 0)
            )
        )
        type_query = await session.execute(
            select(EventDB.tipo_id, func.count()).group_by(EventDB.tipo_id)
        )
        by_type = {str(t or 0): c for t, c in type_query.all()}

        return {
            "total_events": total or 0,
            "active_events": active or 0,
            "by_type": by_type
        }


@app.get("/api/volatile/{reference}")
async def get_volatile_data(reference: str):
    """Get volatile/real-time data for an event"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return {
            "reference": event.reference,
            "lance_atual": event.lance_atual,
            "data_fim": event.data_fim.isoformat() if event.data_fim else None,
            "ultimos_5m": getattr(event, 'ultimos_5m', False)
        }


# ============ Stub Endpoints (for dashboard compatibility) ============
# These endpoints return empty/disabled responses for admin-only features

@app.get("/api/auto-pipelines/status")
async def auto_pipelines_status():
    """Returns pipeline status and event urgency counts from database"""
    try:
        async with get_session() as session:
            from datetime import timedelta
            now = datetime.utcnow()

            # Read pipeline states from database
            pipeline_result = await session.execute(select(PipelineStateDB))
            pipeline_states = pipeline_result.scalars().all()

            pipelines = {}
            for state in pipeline_states:
                pipelines[state.pipeline_name] = {
                    "type": state.pipeline_name,
                    "name": {"xmonitor": "X-Monitor", "ysync": "Y-Sync", "zwatch": "Z-Watch"}.get(state.pipeline_name, state.pipeline_name),
                    "enabled": state.enabled,
                    "is_running": state.is_running,
                    "interval_hours": state.interval_hours,
                    "last_run": state.last_run.isoformat() if state.last_run else None,
                    "next_run": state.next_run.isoformat() if state.next_run else None,
                    "runs_count": state.runs_count,
                    "description": state.description
                }

            # Ensure all 3 pipelines are present
            for name in ["xmonitor", "ysync", "zwatch"]:
                if name not in pipelines:
                    pipelines[name] = {
                        "type": name,
                        "name": {"xmonitor": "X-Monitor", "ysync": "Y-Sync", "zwatch": "Z-Watch"}.get(name),
                        "enabled": False,
                        "is_running": False,
                        "next_run": None
                    }

            # Count events by urgency level
            critical_cutoff = now + timedelta(minutes=5)
            urgent_cutoff = now + timedelta(hours=1)
            soon_cutoff = now + timedelta(hours=24)

            # Get all active events ending in next 24h
            result = await session.execute(
                select(EventDB).where(
                    and_(
                        EventDB.terminado == 0,
                        EventDB.cancelado == 0,
                        EventDB.data_fim >= now,
                        EventDB.data_fim <= soon_cutoff
                    )
                )
            )
            events = result.scalars().all()

            critical = 0
            urgent = 0
            soon = 0

            for e in events:
                if e.data_fim:
                    if e.data_fim <= critical_cutoff:
                        critical += 1
                    elif e.data_fim <= urgent_cutoff:
                        urgent += 1
                    else:
                        soon += 1

            return {
                "pipelines": pipelines,
                "xmonitor_stats": {
                    "total": critical + urgent + soon,
                    "critical": critical,
                    "urgent": urgent,
                    "soon": soon
                }
            }
    except Exception as e:
        print(f"Error getting pipeline status: {e}")
        return {
            "pipelines": {},
            "xmonitor_stats": {"total": 0, "critical": 0, "urgent": 0, "soon": 0}
        }


@app.get("/api/notifications/count")
async def notifications_count():
    """Stub: Notifications not available on public API"""
    return {"count": 0}


@app.get("/api/notification-rules")
async def notification_rules():
    """Stub: Notification rules not available on public API"""
    return []


@app.get("/api/scrape/status")
async def scrape_status():
    """Stub: Scraping not available on public API"""
    return {"running": False, "status": "disabled"}


@app.get("/api/pipeline/status")
async def pipeline_status():
    """Stub: Pipeline status not available on public API"""
    return {"running": False, "stage": None, "progress": 0}


@app.get("/api/logs")
async def get_logs():
    """Stub: Logs not available on public API"""
    return []


@app.get("/api/live/events")
async def live_events_stub():
    """Stub: SSE not available on public API - returns empty"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("data: {\"type\":\"ping\"}\n\n", media_type="text/event-stream")


# ============ Static Files ============

static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    """Serve the main frontend"""
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "E-Leiloes Public API", "docs": "/docs"}


# ============ Run ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
