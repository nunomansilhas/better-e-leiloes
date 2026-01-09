"""
E-Leiloes API - cPanel/Passenger WSGI Entry Point
==================================================
FastAPI is ASGI, but cPanel's Passenger expects WSGI.
This file creates a Passenger-compatible version of the API.

Serves:
- /           : Landing page with instructions
- /dashboard  : Public dashboard application
- /admin      : Admin/Scraper dashboard
- /api/*      : REST API endpoints
- /api/docs   : Swagger API documentation
"""

import sys
import os

# =============================================================================
# PATH SETUP - MUST BE FIRST
# =============================================================================

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(APP_ROOT, 'backend')
STATIC_DIR = os.path.join(BACKEND_DIR, 'static')
PUBLIC_DIR = os.path.join(STATIC_DIR, 'public')
ADMIN_DIR = os.path.join(STATIC_DIR, 'admin')
ENV_FILE = os.path.join(BACKEND_DIR, '.env')

# =============================================================================
# LOAD ENVIRONMENT - MUST BE BEFORE OTHER IMPORTS
# =============================================================================

from dotenv import load_dotenv
load_dotenv(ENV_FILE)

sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, APP_ROOT)
os.chdir(BACKEND_DIR)

# =============================================================================
# IMPORTS
# =============================================================================

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from a2wsgi import ASGIMiddleware
from sqlalchemy import text
from database import async_session_maker, get_pipeline_status, get_all_pipeline_stats
from typing import Optional
from datetime import datetime

# =============================================================================
# CREATE FASTAPI APP
# =============================================================================

app = FastAPI(
    title="E-Leiloes API",
    description="API para dados de leiloes do e-leiloes.pt",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
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
    return {col: serialize_value(val) for col, val in zip(columns, row)}

# =============================================================================
# FRONTEND ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve landing page"""
    landing_file = os.path.join(PUBLIC_DIR, 'landing.html')
    if os.path.exists(landing_file):
        with open(landing_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>E-Leiloes API</h1><p><a href='/dashboard'>Dashboard</a> | <a href='/admin'>Admin</a> | <a href='/api/docs'>API Docs</a></p>")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve public dashboard application"""
    dashboard_file = os.path.join(PUBLIC_DIR, 'dashboard.html')
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve admin/scraper dashboard"""
    admin_file = os.path.join(ADMIN_DIR, 'index.html')
    if os.path.exists(admin_file):
        with open(admin_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Admin Dashboard not found</h1>", status_code=404)

# =============================================================================
# API ENDPOINTS - CORE
# =============================================================================

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

# Alias for dashboard compatibility
@app.get("/api/db/stats")
async def get_db_stats():
    """Alias for /api/stats - dashboard compatibility"""
    return await get_stats()

# =============================================================================
# API ENDPOINTS - PIPELINE STATUS
# =============================================================================

@app.get("/api/pipeline/status/all")
async def pipeline_status_all():
    """Get status of all pipelines from database"""
    try:
        return await get_pipeline_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/pipeline/status/{pipeline_name}")
async def pipeline_status_single(pipeline_name: str):
    """Get status of a specific pipeline"""
    try:
        status = await get_pipeline_status(pipeline_name)
        if status:
            return status
        return {"error": "Pipeline not found", "pipeline_name": pipeline_name}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/pipeline/stats")
async def pipeline_stats():
    """Get aggregated pipeline statistics"""
    try:
        return await get_all_pipeline_stats()
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# API ENDPOINTS - EVENTS
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

            # Total count
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
# API ENDPOINTS - DASHBOARD (Public Dashboard)
# =============================================================================

@app.get("/api/dashboard/ending-soon")
async def dashboard_ending_soon(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get events ending soon"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT reference, titulo, tipo, subtipo, distrito, concelho,
                       valor_base, valor_abertura, lance_atual,
                       data_inicio, data_fim, ativo, capa, tipologia
                FROM events
                WHERE ativo = 1
                  AND data_fim IS NOT NULL
                  AND data_fim > NOW()
                  AND data_fim <= DATE_ADD(NOW(), INTERVAL :hours HOUR)
                ORDER BY data_fim ASC
                LIMIT :limit
            """), {"hours": hours, "limit": limit})

            rows = result.fetchall()
            columns = result.keys()
            events = [row_to_dict(row, columns) for row in rows]
            return {"events": events, "count": len(events)}
    except Exception as e:
        return {"error": str(e), "events": []}

@app.get("/api/dashboard/recent-events")
async def dashboard_recent_events(
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(7, ge=1, le=30)
):
    """Get recently added events"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT reference, titulo, tipo, subtipo, distrito, concelho,
                       valor_base, valor_abertura, lance_atual,
                       data_inicio, data_fim, ativo, capa, tipologia
                FROM events
                WHERE data_inicio >= DATE_SUB(NOW(), INTERVAL :days DAY)
                ORDER BY data_inicio DESC
                LIMIT :limit
            """), {"days": days, "limit": limit})

            rows = result.fetchall()
            columns = result.keys()
            events = [row_to_dict(row, columns) for row in rows]
            return {"events": events, "count": len(events)}
    except Exception as e:
        return {"error": str(e), "events": []}

@app.get("/api/dashboard/recent-bids")
async def dashboard_recent_bids(limit: int = Query(30, ge=1, le=100)):
    """Get recent price changes (bids) from price_history"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT ph.reference, ph.old_price, ph.new_price,
                       ph.change_amount, ph.change_percent, ph.recorded_at,
                       e.titulo, e.tipo, e.distrito, e.capa
                FROM price_history ph
                LEFT JOIN events e ON ph.reference = e.reference
                WHERE ph.old_price IS NOT NULL
                ORDER BY ph.recorded_at DESC
                LIMIT :limit
            """), {"limit": limit})

            rows = result.fetchall()
            columns = result.keys()
            bids = [row_to_dict(row, columns) for row in rows]
            return {"bids": bids, "count": len(bids)}
    except Exception as e:
        return {"error": str(e), "bids": []}

@app.get("/api/dashboard/stats-by-distrito")
async def dashboard_stats_by_distrito(limit: int = Query(5, ge=1, le=20)):
    """Get stats grouped by distrito"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT distrito,
                       COUNT(*) as total,
                       SUM(CASE WHEN ativo = 1 THEN 1 ELSE 0 END) as active,
                       AVG(valor_base) as avg_price
                FROM events
                WHERE distrito IS NOT NULL AND distrito != ''
                GROUP BY distrito
                ORDER BY total DESC
                LIMIT :limit
            """), {"limit": limit})

            rows = result.fetchall()
            columns = result.keys()
            stats = [row_to_dict(row, columns) for row in rows]
            return {"stats": stats, "count": len(stats)}
    except Exception as e:
        return {"error": str(e), "stats": []}

@app.get("/api/dashboard/price-history/{reference}")
async def dashboard_price_history(reference: str):
    """Get price history for a specific event"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT old_price, new_price, change_amount, change_percent,
                       recorded_at, source
                FROM price_history
                WHERE reference = :ref
                ORDER BY recorded_at ASC
            """), {"ref": reference})

            rows = result.fetchall()
            columns = result.keys()
            history = [row_to_dict(row, columns) for row in rows]
            return {"reference": reference, "history": history, "count": len(history)}
    except Exception as e:
        return {"error": str(e), "history": []}

@app.get("/api/volatile/{reference}")
async def get_volatile_data(reference: str):
    """Get volatile/live data for an event (latest price info)"""
    try:
        async with async_session_maker() as session:
            # Get latest price from price_history
            result = await session.execute(text("""
                SELECT new_price as lance_atual, recorded_at as last_update
                FROM price_history
                WHERE reference = :ref
                ORDER BY recorded_at DESC
                LIMIT 1
            """), {"ref": reference})

            row = result.fetchone()
            if row:
                columns = result.keys()
                return row_to_dict(row, columns)

            # Fallback: get from events table
            result = await session.execute(text("""
                SELECT lance_atual, data_fim
                FROM events
                WHERE reference = :ref
            """), {"ref": reference})

            row = result.fetchone()
            if row:
                columns = result.keys()
                return row_to_dict(row, columns)

            return {"lance_atual": None, "last_update": None}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# API ENDPOINTS - NOTIFICATIONS
# =============================================================================

@app.get("/api/notifications/count")
async def notifications_count():
    """Get count of unread notifications"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT COUNT(*) FROM notifications WHERE `read` = 0
            """))
            count = result.scalar() or 0
            return {"count": count}
    except Exception as e:
        return {"count": 0, "error": str(e)}

@app.get("/api/notifications")
async def get_notifications(limit: int = Query(50, ge=1, le=200)):
    """Get notifications"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT id, rule_id, notification_type, event_reference,
                       event_titulo, event_tipo, event_subtipo, event_distrito,
                       preco_anterior, preco_atual, preco_variacao,
                       `read`, created_at
                FROM notifications
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})

            rows = result.fetchall()
            columns = result.keys()
            notifications = [row_to_dict(row, columns) for row in rows]
            return {"notifications": notifications, "count": len(notifications)}
    except Exception as e:
        return {"error": str(e), "notifications": []}

@app.get("/api/notification-rules")
async def get_notification_rules():
    """Get notification rules"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT id, name, rule_type, active, tipos, subtipos,
                       distritos, concelhos, preco_min, preco_max,
                       variacao_min, minutos_restantes, event_reference,
                       created_at, triggers_count
                FROM notification_rules
                ORDER BY created_at DESC
            """))

            rows = result.fetchall()
            columns = result.keys()
            rules = [row_to_dict(row, columns) for row in rows]
            return rules
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# API ENDPOINTS - SCRAPER/PIPELINE STATUS (Read-only for remote dashboard)
# =============================================================================

@app.get("/api/scrape/status")
async def scrape_status():
    """Get scraper status - returns info from pipeline_status table"""
    try:
        status = await get_pipeline_status()
        return {"status": "idle", "pipelines": status}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}

@app.get("/api/auto-pipelines/status")
async def auto_pipelines_status():
    """Get auto pipelines status from database"""
    try:
        return await get_pipeline_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/logs")
async def get_logs():
    """Return empty logs - actual logs are on local scraper"""
    return {"logs": [], "message": "Logs are available on the local scraper machine"}

# =============================================================================
# WSGI APPLICATION
# =============================================================================

application = ASGIMiddleware(app)

# =============================================================================
# LOCAL DEVELOPMENT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
