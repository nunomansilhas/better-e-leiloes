"""
E-Leiloes Public API - Read-Only
Lightweight API for public frontend consumption
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, func, desc, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import os

from dotenv import load_dotenv
load_dotenv()

from database import get_session, EventDB, PriceHistoryDB, init_db


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
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get general statistics"""
    async with get_session() as session:
        now = datetime.utcnow()
        soon = now + timedelta(hours=24)

        # Total events
        total = await session.scalar(select(func.count()).select_from(EventDB))

        # Active (not terminated, not cancelled)
        active = await session.scalar(
            select(func.count()).select_from(EventDB).where(
                and_(EventDB.terminado == False, EventDB.cancelado == False)
            )
        )

        # Ending soon (next 24h)
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

        # By type
        type_query = await session.execute(
            select(EventDB.tipo_id, func.count())
            .where(and_(EventDB.terminado == False, EventDB.cancelado == False))
            .group_by(EventDB.tipo_id)
        )
        by_type = {str(t or 0): c for t, c in type_query.all()}

        # By distrito (top 10)
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


@app.get("/api/events", response_model=List[EventSummary])
async def list_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    tipo_id: Optional[int] = None,
    distrito: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    order_by: str = "data_fim"
):
    """List events with filters"""
    async with get_session() as session:
        query = select(EventDB)

        # Filters
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

        # Ordering
        if order_by == "data_fim":
            query = query.order_by(EventDB.data_fim)
        elif order_by == "lance_atual":
            query = query.order_by(desc(EventDB.lance_atual))
        elif order_by == "valor_base":
            query = query.order_by(EventDB.valor_base)

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        events = result.scalars().all()

        return [EventSummary.model_validate(e) for e in events]


@app.get("/api/events/{reference}", response_model=EventDetail)
async def get_event(reference: str):
    """Get event details by reference"""
    async with get_session() as session:
        result = await session.execute(
            select(EventDB).where(EventDB.reference == reference)
        )
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Parse fotos JSON
        fotos = None
        if event.fotos:
            try:
                fotos_data = json.loads(event.fotos)
                if isinstance(fotos_data, list):
                    fotos = [f.get("url") if isinstance(f, dict) else f for f in fotos_data]
            except:
                pass

        return EventDetail(
            reference=event.reference,
            titulo=event.titulo,
            capa=event.capa,
            tipo_id=event.tipo_id,
            tipo=event.tipo,
            subtipo=event.subtipo,
            tipologia=event.tipologia,
            valor_base=event.valor_base,
            valor_abertura=event.valor_abertura,
            valor_minimo=event.valor_minimo,
            lance_atual=event.lance_atual,
            data_inicio=event.data_inicio,
            data_fim=event.data_fim,
            distrito=event.distrito,
            concelho=event.concelho,
            freguesia=event.freguesia,
            morada=event.morada,
            area_total=event.area_total,
            latitude=event.latitude,
            longitude=event.longitude,
            descricao=event.descricao,
            fotos=fotos,
            terminado=event.terminado,
            cancelado=event.cancelado,
            iniciado=event.iniciado
        )


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


# ============ Static Files ============

# Serve static files
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
