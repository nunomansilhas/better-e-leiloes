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
                and_(EventDB.terminado == False, EventDB.cancelado == False)
            )
        )
        ending_soon = await session.scalar(
            select(func.count()).select_from(EventDB).where(
                and_(
                    EventDB.terminado == False,
                    EventDB.cancelado == False,
                    EventDB.data_fim >= now,
                    EventDB.data_fim <= soon
                )
            )
        )

        type_query = await session.execute(
            select(EventDB.tipo_id, func.count())
            .where(and_(EventDB.terminado == False, EventDB.cancelado == False))
            .group_by(EventDB.tipo_id)
        )
        by_type = {str(t or 0): c for t, c in type_query.all()}

        distrito_query = await session.execute(
            select(EventDB.distrito, func.count())
            .where(
                and_(
                    EventDB.terminado == False,
                    EventDB.cancelado == False,
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
            conditions.append(EventDB.terminado == False)
            conditions.append(EventDB.cancelado == False)
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
        result_events = []
        for e in events:
            result_events.append({
                "reference": e.reference,
                "titulo": e.titulo,
                "capa": e.capa,
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
                        fotos = [f.get("url") if isinstance(f, dict) else f for f in fotos_data]
                except:
                    pass

            # Return dict directly to avoid Pydantic validation issues with None fields
            return {
                "reference": event.reference,
                "titulo": event.titulo,
                "capa": event.capa,
                "tipo_id": event.tipo_id,
                "tipo": event.tipo,
                "subtipo": event.subtipo,
                "tipologia": event.tipologia,
                "valor_base": event.valor_base,
                "valor_abertura": event.valor_abertura,
                "valor_minimo": event.valor_minimo,
                "lance_atual": event.lance_atual or 0,
                "data_inicio": event.data_inicio.isoformat() if event.data_inicio else None,
                "data_fim": event.data_fim.isoformat() if event.data_fim else None,
                "distrito": event.distrito,
                "concelho": event.concelho,
                "freguesia": event.freguesia,
                "morada": event.morada,
                "area_total": event.area_total,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "descricao": event.descricao,
                "fotos": fotos,
                "terminado": event.terminado if event.terminado is not None else False,
                "cancelado": event.cancelado if event.cancelado is not None else False,
                "iniciado": event.iniciado if event.iniciado is not None else False,
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
                EventDB.terminado == False,
                EventDB.cancelado == False,
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


@app.get("/api/price-history/{reference}", response_model=List[PricePoint])
async def get_price_history(reference: str, limit: int = Query(50, le=200)):
    """Get price history for an event"""
    async with get_session() as session:
        result = await session.execute(
            select(PriceHistoryDB)
            .where(PriceHistoryDB.reference == reference)
            .order_by(PriceHistoryDB.timestamp)
            .limit(limit)
        )
        history = result.scalars().all()

        return [PricePoint(preco=h.preco, timestamp=h.timestamp) for h in history]


@app.get("/api/distritos")
async def list_distritos():
    """List all distritos with event counts"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB.distrito, func.count())
            .where(
                and_(
                    EventDB.terminado == False,
                    EventDB.cancelado == False,
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
            .where(and_(EventDB.terminado == False, EventDB.cancelado == False))
            .group_by(EventDB.tipo_id)
            .order_by(EventDB.tipo_id)
        )
        return [
            {"tipo_id": t, "name": tipo_names.get(t, f"Tipo {t}"), "count": c}
            for t, c in result.all() if t
        ]


# ============ Dashboard Endpoints (compatibility with original frontend) ============

@app.get("/api/dashboard/ending-soon")
async def dashboard_ending_soon(hours: int = 24, limit: int = 1000):
    """Alias for ending-soon endpoint"""
    async with get_session() as session:
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)
        result = await session.execute(
            select(EventDB).where(
                and_(
                    EventDB.terminado == False,
                    EventDB.cancelado == False,
                    EventDB.data_fim >= now,
                    EventDB.data_fim <= cutoff
                )
            ).order_by(EventDB.data_fim).limit(limit)
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
                "valor_abertura": e.valor_abertura,
                "valor_minimo": e.valor_minimo,
                "data_fim": e.data_fim.isoformat() if e.data_fim else None
            }
            for e in events
        ]


@app.get("/api/dashboard/price-history/{reference}")
async def dashboard_price_history(reference: str):
    """Alias for price-history endpoint"""
    return await get_price_history(reference)


@app.get("/api/dashboard/recent-bids")
async def dashboard_recent_bids(limit: int = 30):
    """Get recent bid activity"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB).where(
                and_(EventDB.terminado == False, EventDB.cancelado == False, EventDB.lance_atual > 0)
            ).order_by(desc(EventDB.data_atualizacao)).limit(limit)
        )
        events = result.scalars().all()
        return [
            {
                "reference": e.reference,
                "titulo": e.titulo,
                "lance_atual": e.lance_atual,
                "distrito": e.distrito,
                "timestamp": e.data_atualizacao.isoformat() if e.data_atualizacao else None
            }
            for e in events
        ]


@app.get("/api/dashboard/stats-by-distrito")
async def dashboard_stats_by_distrito(limit: int = 5):
    """Get stats grouped by distrito"""
    async with get_session() as session:
        result = await session.execute(
            select(
                EventDB.distrito,
                func.count().label("count"),
                func.sum(EventDB.lance_atual).label("total_value")
            ).where(
                and_(EventDB.terminado == False, EventDB.cancelado == False, EventDB.distrito != None)
            ).group_by(EventDB.distrito).order_by(desc(func.count())).limit(limit)
        )
        return [
            {"distrito": d, "count": c, "total_value": float(v or 0)}
            for d, c, v in result.all()
        ]


@app.get("/api/dashboard/recent-events")
async def dashboard_recent_events(limit: int = 20, days: int = 7):
    """Get recently added events"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB).where(
                and_(EventDB.terminado == False, EventDB.cancelado == False)
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
                and_(EventDB.terminado == False, EventDB.cancelado == False)
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
                        EventDB.terminado == False,
                        EventDB.cancelado == False,
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
