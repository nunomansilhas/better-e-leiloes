"""
E-Leiloes Public API - Read-Only
Lightweight API for public frontend consumption
Supports demo mode when database is unavailable
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
import random

from dotenv import load_dotenv
load_dotenv()

# Check if we can connect to database
DEMO_MODE = False
try:
    from database import get_session, EventDB, PriceHistoryDB, init_db
    from sqlalchemy import select, func, desc, and_, or_
except Exception as e:
    print(f"⚠️  Database unavailable, running in DEMO mode: {e}")
    DEMO_MODE = True


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


# ============ Demo Data ============

DEMO_DISTRITOS = ["Lisboa", "Porto", "Faro", "Braga", "Coimbra", "Setubal", "Aveiro", "Leiria"]
DEMO_TIPOS = {1: "Imoveis", 2: "Veiculos", 3: "Equipamentos", 4: "Mobiliario", 5: "Maquinas", 6: "Direitos"}
DEMO_SUBTIPOS = {
    1: ["Apartamento", "Moradia", "Terreno", "Loja", "Armazem"],
    2: ["Automovel", "Motociclo", "Comercial", "Reboque"],
    3: ["Industrial", "Informatica", "Escritorio"],
    4: ["Moveis", "Decoracao", "Electrodomesticos"],
    5: ["Agricola", "Construcao", "Industrial"],
    6: ["Quotas", "Creditos", "Marcas"]
}

def generate_demo_events(count: int = 50) -> List[dict]:
    """Generate realistic demo events"""
    events = []
    now = datetime.utcnow()

    for i in range(count):
        tipo_id = random.choice(list(DEMO_TIPOS.keys()))
        distrito = random.choice(DEMO_DISTRITOS)
        valor_base = random.randint(5000, 500000)

        events.append({
            "reference": f"LO{random.randint(1000000, 9999999)}2024",
            "titulo": f"{random.choice(DEMO_SUBTIPOS[tipo_id])} em {distrito}",
            "capa": f"https://picsum.photos/seed/{i}/400/300",
            "tipo_id": tipo_id,
            "tipo": DEMO_TIPOS[tipo_id],
            "subtipo": random.choice(DEMO_SUBTIPOS[tipo_id]),
            "valor_base": valor_base,
            "valor_minimo": int(valor_base * 0.7),
            "lance_atual": int(valor_base * random.uniform(0.8, 1.5)),
            "data_fim": now + timedelta(hours=random.randint(1, 72)),
            "distrito": distrito,
            "concelho": f"{distrito} Centro",
            "terminado": False,
            "cancelado": False
        })

    return sorted(events, key=lambda x: x["data_fim"])


DEMO_EVENTS = generate_demo_events(100)


# ============ App Setup ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    global DEMO_MODE
    if not DEMO_MODE:
        try:
            await init_db()
            print("✅ Connected to database")
        except Exception as e:
            print(f"⚠️  Database init failed, switching to demo mode: {e}")
            DEMO_MODE = True
            print("🎭 Running in DEMO mode with mock data")
    else:
        print("🎭 Running in DEMO mode with mock data")

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
        "mode": "demo" if DEMO_MODE else "live",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get general statistics"""
    if DEMO_MODE:
        by_type = {}
        by_distrito = {}
        for e in DEMO_EVENTS:
            t = str(e["tipo_id"])
            by_type[t] = by_type.get(t, 0) + 1
            d = e["distrito"]
            by_distrito[d] = by_distrito.get(d, 0) + 1

        now = datetime.utcnow()
        ending = len([e for e in DEMO_EVENTS if e["data_fim"] < now + timedelta(hours=24)])

        return StatsResponse(
            total=len(DEMO_EVENTS),
            active=len(DEMO_EVENTS),
            ending_soon=ending,
            by_type=by_type,
            by_distrito=dict(sorted(by_distrito.items(), key=lambda x: -x[1])[:10])
        )

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
    if DEMO_MODE:
        events = DEMO_EVENTS.copy()

        if tipo_id:
            events = [e for e in events if e["tipo_id"] == tipo_id]
        if distrito:
            events = [e for e in events if e["distrito"] == distrito]
        if search:
            search_lower = search.lower()
            events = [e for e in events if search_lower in e["titulo"].lower() or search_lower in e["reference"].lower()]

        if order_by == "lance_atual":
            events = sorted(events, key=lambda x: -x["lance_atual"])
        elif order_by == "valor_base":
            events = sorted(events, key=lambda x: x["valor_base"])

        # Convert to dict format with ativo field
        result_events = []
        for e in events[offset:offset+limit]:
            event_dict = {
                **e,
                "ativo": not e.get("terminado", False) and not e.get("cancelado", False),
                "data_fim": e["data_fim"].isoformat() if hasattr(e["data_fim"], "isoformat") else e["data_fim"]
            }
            result_events.append(event_dict)

        return {"events": result_events, "total": len(events), "page": offset // limit + 1}

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

        return {"events": result_events, "total": len(result_events), "page": offset // limit + 1}


@app.get("/api/events/{reference}", response_model=EventDetail)
async def get_event(reference: str):
    """Get event details by reference"""
    if DEMO_MODE:
        for e in DEMO_EVENTS:
            if e["reference"] == reference:
                return EventDetail(
                    **e,
                    tipologia="T3",
                    valor_abertura=int(e["valor_base"] * 0.85),
                    data_inicio=e["data_fim"] - timedelta(days=14),
                    freguesia=f"Freguesia de {e['distrito']}",
                    morada=f"Rua Exemplo, 123, {e['distrito']}",
                    area_total=random.randint(50, 300),
                    latitude=38.7 + random.random(),
                    longitude=-9.1 + random.random(),
                    descricao=f"Excelente {e['subtipo'].lower()} localizado em {e['distrito']}. Otima oportunidade de investimento.",
                    fotos=[f"https://picsum.photos/seed/{i}/800/600" for i in range(4)],
                    iniciado=True
                )
        raise HTTPException(status_code=404, detail="Event not found")

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
    if DEMO_MODE:
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)
        events = [e for e in DEMO_EVENTS if e["data_fim"] <= cutoff]
        if tipo_id:
            events = [e for e in events if e["tipo_id"] == tipo_id]
        return [EventSummary(**e) for e in events[:limit]]

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
    if DEMO_MODE:
        # Generate fake price history
        now = datetime.utcnow()
        base_price = random.randint(50000, 200000)
        return [
            PricePoint(
                preco=base_price + (i * random.randint(500, 2000)),
                timestamp=now - timedelta(hours=limit-i)
            )
            for i in range(min(10, limit))
        ]

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
    if DEMO_MODE:
        counts = {}
        for e in DEMO_EVENTS:
            d = e["distrito"]
            counts[d] = counts.get(d, 0) + 1
        return [{"distrito": d, "count": c} for d, c in sorted(counts.items())]

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
    if DEMO_MODE:
        counts = {}
        for e in DEMO_EVENTS:
            t = e["tipo_id"]
            counts[t] = counts.get(t, 0) + 1
        return [
            {"tipo_id": t, "name": DEMO_TIPOS.get(t, f"Tipo {t}"), "count": c}
            for t, c in sorted(counts.items())
        ]

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
    if DEMO_MODE:
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)
        events = [e for e in DEMO_EVENTS if e["data_fim"] <= cutoff]
        return [
            {
                "reference": e["reference"],
                "titulo": e["titulo"],
                "tipo_id": e["tipo_id"],
                "subtipo": e["subtipo"],
                "distrito": e["distrito"],
                "lance_atual": e["lance_atual"],
                "valor_base": e["valor_base"],
                "valor_abertura": e.get("valor_abertura", e["valor_base"] * 0.85),
                "valor_minimo": e["valor_minimo"],
                "data_fim": e["data_fim"].isoformat()
            }
            for e in events[:limit]
        ]

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
    if DEMO_MODE:
        now = datetime.utcnow()
        return [
            {
                "reference": e["reference"],
                "titulo": e["titulo"],
                "lance_atual": e["lance_atual"],
                "distrito": e["distrito"],
                "timestamp": (now - timedelta(minutes=random.randint(1, 120))).isoformat()
            }
            for e in random.sample(DEMO_EVENTS, min(limit, len(DEMO_EVENTS)))
        ]

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
    if DEMO_MODE:
        counts = {}
        for e in DEMO_EVENTS:
            d = e["distrito"]
            if d not in counts:
                counts[d] = {"distrito": d, "count": 0, "total_value": 0}
            counts[d]["count"] += 1
            counts[d]["total_value"] += e["lance_atual"]
        return sorted(counts.values(), key=lambda x: -x["count"])[:limit]

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
    if DEMO_MODE:
        return DEMO_EVENTS[:limit]

    async with get_session() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
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
    if DEMO_MODE:
        by_type = {}
        for e in DEMO_EVENTS:
            t = e["tipo_id"]
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_events": len(DEMO_EVENTS),
            "active_events": len(DEMO_EVENTS),
            "by_type": by_type,
            "database_size": "demo"
        }

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
    if DEMO_MODE:
        for e in DEMO_EVENTS:
            if e["reference"] == reference:
                return {
                    "reference": reference,
                    "lance_atual": e["lance_atual"],
                    "data_fim": e["data_fim"].isoformat(),
                    "ultimos_5m": random.choice([True, False])
                }
        raise HTTPException(status_code=404, detail="Event not found")

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
    """Stub: Pipelines not available on public API"""
    return {
        "xmonitor": {"enabled": False, "next_run": None},
        "ysync": {"enabled": False, "next_run": None},
        "zwatch": {"enabled": False, "next_run": None}
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
    return {"message": "E-Leiloes Public API", "docs": "/docs", "mode": "demo" if DEMO_MODE else "live"}


# ============ Run ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
