"""
E-Leiloes API - cPanel/Passenger WSGI Entry Point
==================================================
FastAPI is ASGI, but cPanel's Passenger expects WSGI.
This file creates a Passenger-compatible version of the API.

IMPORTANT: The main.py has a lifespan/scheduler that doesn't work with Passenger.
This file creates a simplified API that works with cPanel hosting.

Usage:
1. Clone repo to cPanel: git clone ... /home/user/eleiloes.mansilhas.pt
2. Create .env in backend/ with DATABASE_URL
3. Install deps: pip install -r backend/requirements.txt
4. Configure Python App in cPanel with this file as startup
"""

import sys
import os

# =============================================================================
# PATH SETUP - MUST BE FIRST
# =============================================================================

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(APP_ROOT, 'backend')
ENV_FILE = os.path.join(BACKEND_DIR, '.env')

# =============================================================================
# LOAD ENVIRONMENT - MUST BE BEFORE OTHER IMPORTS
# =============================================================================

from dotenv import load_dotenv
# CRITICAL: Use explicit path - Passenger doesn't find .env automatically
load_dotenv(ENV_FILE)

# Now add paths and change directory
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, APP_ROOT)
os.chdir(BACKEND_DIR)

# =============================================================================
# IMPORTS
# =============================================================================

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from a2wsgi import ASGIMiddleware
from sqlalchemy import text
from database import async_session_maker
from typing import Optional
from datetime import datetime

# =============================================================================
# CREATE FASTAPI APP (without lifespan - Passenger compatible)
# =============================================================================

app = FastAPI(
    title="E-Leiloes API",
    description="API para dados de leilões do e-leiloes.pt",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HELPERS
# =============================================================================

def serialize_value(value):
    """Convert value to JSON-serializable format"""
    if value is None:
        return None
    elif hasattr(value, '__float__'):
        return float(value)
    elif hasattr(value, 'isoformat'):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    return value

def row_to_dict(row, columns):
    """Convert database row to dictionary"""
    return {col: serialize_value(val) for col, val in zip(columns, row)}

# =============================================================================
# BASIC ENDPOINTS
# =============================================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "E-Leiloes API",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "stats": "/api/stats",
            "events": "/api/events",
            "distritos": "/api/distritos",
            "tipos": "/api/tipos",
            "search": "/api/search"
        }
    }

@app.get("/api/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM events"))
            total = result.scalar() or 0

            result = await session.execute(text("SELECT COUNT(*) FROM events WHERE ativo = 1"))
            active = result.scalar() or 0

            result = await session.execute(text(
                "SELECT COUNT(*) FROM events WHERE DATE(data_fim) = CURDATE() AND ativo = 1"
            ))
            ending_today = result.scalar() or 0

            return {
                "total_events": total,
                "active_events": active,
                "ending_today": ending_today,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# EVENTS ENDPOINTS
# =============================================================================

@app.get("/api/events")
async def get_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    tipo: Optional[str] = None,
    distrito: Optional[str] = None,
    concelho: Optional[str] = None,
    ativo: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    order_by: str = Query("data_fim", regex="^(data_fim|valor_base|lance_atual|titulo)$"),
    order_dir: str = Query("DESC", regex="^(ASC|DESC)$")
):
    """Get events with filters and pagination"""
    try:
        async with async_session_maker() as session:
            select_cols = """reference, titulo, tipo, subtipo, distrito, concelho,
                           valor_base, valor_abertura, lance_atual,
                           data_inicio, data_fim, ativo, capa, tipologia"""

            query = f"SELECT {select_cols} FROM events WHERE 1=1"
            params = {"limit": limit, "offset": offset}

            if search:
                query += " AND (titulo LIKE :search OR descricao LIKE :search OR distrito LIKE :search)"
                params["search"] = f"%{search}%"

            if tipo:
                query += " AND tipo = :tipo"
                params["tipo"] = tipo

            if distrito:
                query += " AND distrito = :distrito"
                params["distrito"] = distrito

            if concelho:
                query += " AND concelho = :concelho"
                params["concelho"] = concelho

            if ativo is not None:
                query += " AND ativo = :ativo"
                params["ativo"] = 1 if ativo else 0

            if min_price is not None:
                query += " AND valor_base >= :min_price"
                params["min_price"] = min_price

            if max_price is not None:
                query += " AND valor_base <= :max_price"
                params["max_price"] = max_price

            query += f" ORDER BY {order_by} {order_dir} LIMIT :limit OFFSET :offset"

            result = await session.execute(text(query), params)
            rows = result.fetchall()
            columns = result.keys()
            events = [row_to_dict(row, columns) for row in rows]

            # Get total count for pagination
            count_query = "SELECT COUNT(*) FROM events WHERE 1=1"
            count_params = {}
            if search:
                count_query += " AND (titulo LIKE :search OR descricao LIKE :search)"
                count_params["search"] = f"%{search}%"
            if tipo:
                count_query += " AND tipo = :tipo"
                count_params["tipo"] = tipo
            if distrito:
                count_query += " AND distrito = :distrito"
                count_params["distrito"] = distrito
            if ativo is not None:
                count_query += " AND ativo = :ativo"
                count_params["ativo"] = 1 if ativo else 0

            count_result = await session.execute(text(count_query), count_params)
            total_count = count_result.scalar()

            return {
                "events": events,
                "count": len(events),
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/events/{reference}")
async def get_event(reference: str):
    """Get single event by reference"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                text("SELECT * FROM events WHERE reference = :ref"),
                {"ref": reference}
            )
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Event not found")

            columns = result.keys()
            return row_to_dict(row, columns)
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# FILTER OPTIONS
# =============================================================================

@app.get("/api/distritos")
async def get_distritos():
    """Get list of districts with event counts"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT distrito, COUNT(*) as count
                FROM events
                WHERE distrito IS NOT NULL AND distrito != ''
                GROUP BY distrito
                ORDER BY distrito
            """))
            rows = result.fetchall()
            return {"distritos": [{"name": r[0], "count": r[1]} for r in rows]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/tipos")
async def get_tipos():
    """Get list of event types with counts"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT tipo, COUNT(*) as count
                FROM events
                WHERE tipo IS NOT NULL AND tipo != ''
                GROUP BY tipo
                ORDER BY tipo
            """))
            rows = result.fetchall()
            return {"tipos": [{"name": r[0], "count": r[1]} for r in rows]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/concelhos")
async def get_concelhos(distrito: Optional[str] = None):
    """Get list of municipalities"""
    try:
        async with async_session_maker() as session:
            query = """
                SELECT concelho, COUNT(*) as count
                FROM events
                WHERE concelho IS NOT NULL AND concelho != ''
            """
            params = {}

            if distrito:
                query += " AND distrito = :distrito"
                params["distrito"] = distrito

            query += " GROUP BY concelho ORDER BY concelho"

            result = await session.execute(text(query), params)
            rows = result.fetchall()
            return {"concelhos": [{"name": r[0], "count": r[1]} for r in rows]}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# SEARCH
# =============================================================================

@app.get("/api/search")
async def search_events(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100)
):
    """Quick search across events"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT reference, titulo, tipo, distrito, concelho, valor_base, lance_atual, data_fim, capa
                FROM events
                WHERE titulo LIKE :q OR descricao LIKE :q OR distrito LIKE :q OR concelho LIKE :q
                ORDER BY data_fim DESC
                LIMIT :limit
            """), {"q": f"%{q}%", "limit": limit})

            rows = result.fetchall()
            columns = result.keys()
            events = [row_to_dict(row, columns) for row in rows]

            return {"query": q, "results": events, "count": len(events)}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# WSGI APPLICATION (for Passenger)
# =============================================================================

application = ASGIMiddleware(app)

# =============================================================================
# LOCAL DEVELOPMENT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
