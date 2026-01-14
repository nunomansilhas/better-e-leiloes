"""
E-Leiloes Data API - FastAPI Backend
Recolhe e serve dados dos leilões do e-leiloes.pt
"""

import sys
import asyncio

# Fix para Windows - asyncio com Playwright/subprocessos
# IMPORTANTE: O modo --reload do uvicorn força SelectorEventLoop que não suporta subprocessos!
# Para usar Playwright no Windows, correr sem --reload ou usar esta correção
if sys.platform == 'win32':
    # Python 3.8+ no Windows: usar ProactorEventLoop para suportar subprocessos
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Forçar ProactorEventLoop se ainda não existe um event loop
    try:
        loop = asyncio.get_running_loop()
        if not isinstance(loop, asyncio.ProactorEventLoop):
            print("⚠️ AVISO: Event loop não é ProactorEventLoop - Playwright pode falhar!")
            print("   Sugestão: Correr sem --reload ou usar 'python -m uvicorn main:app'")
    except RuntimeError:
        # Nenhum loop a correr ainda - criar ProactorEventLoop
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)

# nest_asyncio permite nested event loops (necessário para Playwright + uvicorn)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # nest_asyncio não instalado, tentar sem

# CRITICAL: Load .env BEFORE importing database!
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import List, Optional, Set
import os
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from models import EventData, EventListResponse, ScraperStatus, ValoresLeilao
from database import init_db, get_db
from scraper import EventScraper
from cache import CacheManager
from pipeline_state import get_pipeline_state, SafeJSONEncoder
from auto_pipelines import get_auto_pipelines_manager
from collections import deque
import threading
from logger import log_info, log_error, log_warning, log_exception

# Global instances
scraper = None
cache_manager = None
scheduler = None
scheduled_job_id = None

# SSE: Set of queues for broadcasting price updates to connected clients
sse_clients: Set[asyncio.Queue] = set()

# Logging system for dashboard console
log_buffer = deque(maxlen=100)  # Circular buffer, keeps last 100 logs
log_lock = threading.Lock()

# SSE clients for real-time logs
log_sse_clients: Set[asyncio.Queue] = set()

# Pipeline execution history
pipeline_history = deque(maxlen=50)  # Keep last 50 pipeline runs
pipeline_history_lock = threading.Lock()

def add_dashboard_log(message: str, level: str = "info"):
    """Adiciona um log ao buffer para o dashboard console e envia para SSE clients"""
    log_entry = {
        "message": message,
        "level": level,
        "timestamp": datetime.now().isoformat()
    }
    with log_lock:
        log_buffer.append(log_entry)

    # Broadcast to SSE clients
    asyncio.create_task(broadcast_log(log_entry))


async def broadcast_log(log_entry: dict):
    """Broadcast log entry to all connected SSE log clients"""
    dead_clients = set()
    for queue in log_sse_clients:
        try:
            await queue.put(log_entry)
        except:
            dead_clients.add(queue)

    for client in dead_clients:
        log_sse_clients.discard(client)


def add_pipeline_history(pipeline_type: str, status: str, details: dict = None):
    """Adiciona uma execução de pipeline ao histórico"""
    with pipeline_history_lock:
        pipeline_history.append({
            "pipeline": pipeline_type,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })


async def broadcast_price_update(event_data: dict):
    """Broadcast a price update to all connected SSE clients"""
    dead_clients = set()
    for queue in sse_clients:
        try:
            await queue.put(event_data)
        except:
            dead_clients.add(queue)

    # Remove disconnected clients
    for client in dead_clients:
        sse_clients.discard(client)


async def broadcast_new_event(event_data: dict):
    """Broadcast a new event to all connected SSE clients"""
    dead_clients = set()
    for queue in sse_clients:
        try:
            await queue.put({
                "type": "new_event",
                **event_data
            })
        except:
            dead_clients.add(queue)

    # Remove disconnected clients
    for client in dead_clients:
        sse_clients.discard(client)


def get_sse_clients():
    """Get the SSE clients set (for use in auto_pipelines)"""
    return sse_clients


async def process_refresh_queue():
    """
    Background job that polls for pending refresh requests and processes them.
    Runs every 5 seconds.
    States: 0=pending, 1=processing, 2=completed, 3=error
    """
    global scraper
    try:
        async with get_db() as db:
            from database import RefreshLogDB
            from sqlalchemy import select

            # Find pending requests (state=0)
            result = await db.session.execute(
                select(RefreshLogDB)
                .where(RefreshLogDB.state == 0)
                .order_by(RefreshLogDB.created_at)
                .limit(5)  # Process up to 5 at a time
            )
            pending_requests = result.scalars().all()

            if not pending_requests:
                return  # Nothing to process

            for request in pending_requests:
                try:
                    # Mark as processing (state=1)
                    request.state = 1
                    await db.session.commit()

                    # Scrape fresh data
                    events = await scraper.scrape_details_via_api([request.reference], None)

                    if events and len(events) > 0:
                        event = events[0]
                        # Save to database
                        await db.save_event(event)

                        # Mark as completed (state=2)
                        request.state = 2
                        request.result_lance = event.lance_atual
                        request.result_message = "Atualizado com sucesso"
                        request.processed_at = datetime.utcnow()
                        await db.session.commit()

                        add_dashboard_log(f"🔄 Refresh: {request.reference} → {request.result_lance}€", "success")
                    else:
                        # Event not found
                        request.state = 3  # error
                        request.result_message = "Evento não encontrado"
                        request.processed_at = datetime.utcnow()
                        await db.session.commit()

                except Exception as e:
                    # Mark as error (state=3)
                    request.state = 3
                    request.result_message = str(e)[:500]
                    request.processed_at = datetime.utcnow()
                    await db.session.commit()
                    add_dashboard_log(f"❌ Refresh failed: {request.reference} - {e}", "error")

    except Exception as e:
        log_exception(f"Error in refresh queue processor: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação"""
    global scraper, cache_manager, scheduler

    # Nota: Event loop policy já definida no início do ficheiro

    # Startup
    print("🚀 Iniciando E-Leiloes API...")
    await init_db()

    # Clear pipeline state on startup (clean slate)
    pipeline_state = get_pipeline_state()
    await pipeline_state.stop()
    print("🧹 Pipeline state limpo")

    # Clear X-Monitor history on startup (fresh start each session)
    from xmonitor_history import clear_history
    clear_history()

    scraper = EventScraper()
    cache_manager = CacheManager()

    # Inicializa scheduler para agendamento
    scheduler = AsyncIOScheduler()
    scheduler.start()
    print("⏰ Scheduler iniciado")

    # Auto-start enabled pipelines
    from auto_pipelines import get_auto_pipelines_manager
    pipelines_manager = get_auto_pipelines_manager()

    # Load pipeline state from database (overrides JSON file)
    await pipelines_manager.load_from_database()

    enabled_count = 0
    for pipeline_type, pipeline in pipelines_manager.pipelines.items():
        if pipeline.enabled:
            await pipelines_manager._schedule_pipeline(pipeline_type, scheduler)
            enabled_count += 1
            print(f"  ▶️ Auto-started: {pipeline.name}")
    if enabled_count > 0:
        print(f"🔄 {enabled_count} pipeline(s) auto-started from saved config")

    # Start refresh queue processor (polls every 5 seconds)
    scheduler.add_job(
        process_refresh_queue,
        IntervalTrigger(seconds=5),
        id="refresh_queue_processor",
        replace_existing=True
    )
    print("🔄 Refresh queue processor started (5s interval)")

    # Schedule automatic cleanup jobs
    from cleanup import schedule_cleanup_jobs
    schedule_cleanup_jobs(scheduler)

    print("✅ API pronta!")

    yield

    # Shutdown
    print("👋 Encerrando API...")
    if scheduler:
        scheduler.shutdown()
    if scraper:
        await scraper.close()
    if cache_manager:
        await cache_manager.close()

# API Documentation Tags
tags_metadata = [
    {
        "name": "Health",
        "description": "System health and status monitoring endpoints",
    },
    {
        "name": "Events",
        "description": "Query and manage auction events data",
    },
    {
        "name": "Pipelines",
        "description": "Control data scraping pipelines (X-Monitor, Y-Sync, Z-Watch)",
    },
    {
        "name": "Notifications",
        "description": "Manage notification rules and view triggered notifications",
    },
    {
        "name": "Statistics",
        "description": "View system and data statistics",
    },
    {
        "name": "Cache",
        "description": "Cache management and statistics",
    },
    {
        "name": "Cleanup",
        "description": "Data cleanup and maintenance operations",
    },
    {
        "name": "Admin",
        "description": "Administrative operations (scraping, database management)",
    },
]

app = FastAPI(
    title="E-Leiloes Data API",
    description="""
## API para gestão de dados de leilões do e-leiloes.pt

### Funcionalidades:
- **Scraping automático** de dados de leilões
- **Monitorização em tempo real** de preços e eventos
- **Sistema de notificações** configurável
- **Histórico de preços** completo
- **API pública** para consulta de dados

### Autenticação:
A API usa autenticação HMAC-SHA256 para endpoints protegidos.
Headers necessários: `X-Signature`, `X-Timestamp`

### Rate Limiting:
- 100 requests por minuto por IP
- Headers de resposta: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Window`
    """,
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "E-Leiloes API Support",
        "url": "https://github.com/nunomansilhas/better-e-leiloes",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS - Restrict to allowed origins
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Signature", "X-Timestamp"],  # Allow security headers
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Window"],
)

# Security middleware (Rate Limiting + HMAC Auth)
from security import security_middleware
app.middleware("http")(security_middleware)

# Error handlers for consistent error responses
from error_handlers import setup_error_handlers
setup_error_handlers(app)

# Register modular routers
from routers import cache_router, cleanup_router, metrics_router
app.include_router(cache_router)
app.include_router(cleanup_router)
app.include_router(metrics_router)

# Servir arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============== ENDPOINTS ==============

@app.get("/")
async def root():
    """Página de administração - Scrapers & Tools"""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
async def health():
    """Health check simples"""
    return {"status": "ok"}


# ============== WEBSOCKET FOR REAL-TIME NOTIFICATIONS ==============

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.
    Clients connect here to receive instant notification updates.
    """
    from websocket_manager import notification_ws_manager

    await notification_ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for messages (ping/pong)
            data = await websocket.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await notification_ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await notification_ws_manager.disconnect(websocket)


@app.get("/api/health")
async def health_detailed():
    """
    Health check detalhado com status de todos os serviços.

    Retorna:
    - status: "healthy" | "degraded" | "unhealthy"
    - services: estado de cada serviço (database, redis, pipelines)
    - uptime: tempo desde o início
    - version: versão da API
    """
    import time

    services = {}
    overall_status = "healthy"

    # Database check
    try:
        async with get_db() as db:
            from sqlalchemy import text
            await db.session.execute(text("SELECT 1"))
        services["database"] = {"status": "ok", "type": "mysql"}
    except Exception as e:
        services["database"] = {"status": "error", "error": str(e)}
        overall_status = "unhealthy"

    # Redis check - only if REDIS_URL is configured
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            if cache_manager and cache_manager.redis_client:
                await cache_manager.redis_client.ping()
                services["redis"] = {"status": "ok"}
            else:
                services["redis"] = {"status": "error", "error": "client not initialized"}
                if overall_status == "healthy":
                    overall_status = "degraded"
        except Exception as e:
            services["redis"] = {"status": "error", "error": str(e)}
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        # Redis not configured - this is fine, using memory cache
        services["redis"] = {"status": "disabled", "note": "REDIS_URL not set, using memory cache"}

    # Pipelines check
    try:
        auto_pipelines = get_auto_pipelines_manager()
        status = auto_pipelines.get_status()
        pipelines_status = status.get("pipelines", {})
        active_count = sum(1 for p in pipelines_status.values() if p.get("enabled"))
        services["pipelines"] = {
            "status": "ok",
            "active": active_count,
            "total": len(pipelines_status)
        }
    except Exception as e:
        services["pipelines"] = {"status": "error", "error": str(e)}

    # Scraper check
    services["scraper"] = {
        "status": "running" if scraper and scraper.is_running else "idle",
        "stop_requested": scraper.stop_requested if scraper else False
    }

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": services
    }


@app.get("/api/security/stats")
async def get_security_stats():
    """Get security stats (rate limiting, etc.) - Admin only"""
    from security import rate_limiter, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, WHITELIST_IPS
    return {
        "rate_limiter": rate_limiter.get_stats(),
        "config": {
            "rate_limit_requests": RATE_LIMIT_REQUESTS,
            "rate_limit_window": RATE_LIMIT_WINDOW,
            "whitelist_ips": list(WHITELIST_IPS)
        }
    }


@app.get("/api/security/auth.js")
async def get_auth_script():
    """Serve the frontend authentication helper script"""
    from security import get_frontend_auth_script
    from fastapi.responses import Response
    return Response(
        content=get_frontend_auth_script(),
        media_type="application/javascript"
    )


@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """Get current pipeline state for real-time feedback"""
    pipeline_state = get_pipeline_state()
    state = await pipeline_state.get_state()
    # Use SafeJSONEncoder to handle Pydantic models and dataclasses
    content = json.dumps(state, ensure_ascii=False, cls=SafeJSONEncoder)
    return JSONResponse(content=json.loads(content))


@app.post("/api/pipeline/kill")
async def kill_pipeline():
    """
    KILL SWITCH: Para imediatamente qualquer pipeline em execução.

    Limpa o estado da pipeline e sinaliza paragem ao scraper.
    """
    pipeline_state = get_pipeline_state()

    # Get current state before killing
    state = await pipeline_state.get_state()
    was_active = state.get("active", False)
    stage = state.get("stage")
    stage_name = state.get("stage_name")

    # Stop the scraper - ALWAYS set the flag regardless of is_running
    if scraper:
        scraper.stop_requested = True
        print("🛑 Scraper stop_requested = True")

    # Clear pipeline state
    await pipeline_state.stop()

    add_dashboard_log("🛑 Pipeline KILLED pelo utilizador", "warning")

    return {
        "success": True,
        "message": "Pipeline terminada com sucesso",
        "was_active": was_active,
        "killed_stage": stage,
        "killed_stage_name": stage_name
    }


@app.post("/api/pipeline/test")
async def test_pipeline_feedback(
    items: int = Query(10, description="Número de itens para simular"),
    stage: int = Query(2, description="Stage para simular (1, 2, ou 3)")
):
    """
    TEST ENDPOINT: Simula uma pipeline em execução para testar o feedback.
    Útil para testar o sistema sem precisar do Playwright.
    """
    pipeline_state = get_pipeline_state()

    stage_names = {
        1: "Stage 1 - IDs (Test)",
        2: "Stage 2 - Detalhes (Test)",
        3: "Stage 3 - Imagens (Test)"
    }

    try:
        # Iniciar pipeline
        await pipeline_state.start(
            stage=stage,
            stage_name=stage_names.get(stage, "Test Stage"),
            total=items,
            details={"test": True}
        )

        # Simular processamento
        for i in range(1, items + 1):
            await asyncio.sleep(0.5)  # Simular tempo de processamento

            await pipeline_state.update(
                current=i,
                message=f"Processando item {i}/{items} - TEST-{i:04d}"
            )

        # Completar
        await pipeline_state.complete(
            message=f"✅ Test concluído! {items} itens processados"
        )

        # Parar após delay
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "success": True,
            "message": f"Test pipeline concluída: {items} itens em stage {stage}",
            "stage": stage,
            "items": items
        }

    except Exception as e:
        await pipeline_state.add_error(str(e))
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=str(e))


# ============== AUTOMATIC PIPELINES ENDPOINTS ==============

@app.get("/api/auto-pipelines/status")
async def get_auto_pipelines_status():
    """Get status of all automatic pipelines"""
    auto_pipelines = get_auto_pipelines_manager()
    return JSONResponse(auto_pipelines.get_status())


@app.post("/api/auto-pipelines/{pipeline_type}/toggle")
async def toggle_auto_pipeline(
    pipeline_type: str,
    enabled: bool = Query(..., description="Enable or disable the pipeline")
):
    """
    Enable or disable an automatic pipeline.

    - **pipeline_type**: Type of pipeline (full, prices, info)
    - **enabled**: True to enable, False to disable

    Returns pipeline configuration and next run time if enabled.
    """
    auto_pipelines = get_auto_pipelines_manager()

    try:
        result = await auto_pipelines.toggle_pipeline(
            pipeline_type=pipeline_type,
            enabled=enabled,
            scheduler=scheduler
        )

        add_dashboard_log(
            f"{'🟢 Ativada' if enabled else '🔴 Desativada'} pipeline automática: {pipeline_type}",
            "info"
        )

        return JSONResponse(result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao alterar pipeline: {str(e)}")


@app.get("/api/auto-pipelines/prices/cache-info")
async def get_prices_cache_info():
    """Get Pipeline X cache information (number of cached events)"""
    auto_pipelines = get_auto_pipelines_manager()

    cache_count = len(auto_pipelines._critical_events_cache)
    last_refresh = auto_pipelines._cache_last_refresh

    return JSONResponse({
        "cached_events": cache_count,
        "last_refresh": last_refresh.strftime("%Y-%m-%d %H:%M:%S") if last_refresh else None
    })


# ============== X-MONITOR HISTORY ENDPOINTS ==============

@app.get("/api/xmonitor/history")
async def get_xmonitor_history():
    """Get all X-Monitor history data"""
    from xmonitor_history import get_all_history
    return JSONResponse(get_all_history())


@app.get("/api/xmonitor/history/{reference}")
async def get_xmonitor_event_history(reference: str):
    """Get history for a specific event"""
    from xmonitor_history import get_event_history
    history = get_event_history(reference)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history for event: {reference}")
    return JSONResponse(history)


@app.get("/api/xmonitor/recent")
async def get_xmonitor_recent(limit: int = Query(50, ge=1, le=500)):
    """Get most recent changes across all events"""
    from xmonitor_history import get_recent_changes
    return JSONResponse(get_recent_changes(limit))


@app.get("/api/xmonitor/summary")
async def get_xmonitor_summary():
    """Get summary of all tracked events"""
    from xmonitor_history import get_active_events_summary
    return JSONResponse(get_active_events_summary())


@app.get("/api/xmonitor/stats")
async def get_xmonitor_stats():
    """Get X-Monitor history statistics"""
    from xmonitor_history import get_stats
    return JSONResponse(get_stats())


# ============== NOTIFICATION ENDPOINTS ==============

@app.get("/api/notifications")
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False)
):
    """Get notifications list"""
    async with get_db() as db:
        notifications = await db.get_notifications(limit=limit, unread_only=unread_only)
        return JSONResponse(notifications)


@app.get("/api/notifications/count")
async def get_notifications_count():
    """Get unread notifications count"""
    async with get_db() as db:
        count = await db.get_unread_count()
        return JSONResponse({"unread": count})


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, read: bool = True):
    """Mark a notification as read or unread"""
    async with get_db() as db:
        success = await db.mark_notification_read(notification_id, read=read)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return JSONResponse({"success": True, "read": read})


@app.post("/api/notifications/read-all")
async def mark_all_notifications_read():
    """Mark all notifications as read"""
    async with get_db() as db:
        count = await db.mark_all_notifications_read()
        return JSONResponse({"marked_read": count})


@app.delete("/api/notifications/delete-all")
async def delete_all_notifications():
    """Delete all notifications"""
    async with get_db() as db:
        count = await db.delete_all_notifications()
        return JSONResponse({"deleted": count})


# ============== NOTIFICATION RULES ENDPOINTS ==============

@app.get("/api/notification-rules")
async def get_notification_rules(active_only: bool = Query(False)):
    """Get all notification rules"""
    async with get_db() as db:
        rules = await db.get_notification_rules(active_only=active_only)
        return JSONResponse(rules)


@app.post("/api/notification-rules")
async def create_notification_rule(rule: dict = Body(...)):
    """Create a new notification rule"""
    print(f"📝 Creating notification rule: {rule}")
    required_fields = ["name", "rule_type"]
    for field in required_fields:
        if field not in rule:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    valid_types = ["new_event", "price_change", "ending_soon"]
    if rule["rule_type"] not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type. Must be one of: {valid_types}")

    async with get_db() as db:
        rule_id = await db.create_notification_rule(rule)
        print(f"✅ Rule created with ID: {rule_id}")
        # Invalidate rules cache
        from notification_engine import get_notification_engine
        get_notification_engine().invalidate_cache(rule["rule_type"])
        return JSONResponse({"id": rule_id, "success": True})


@app.put("/api/notification-rules/{rule_id}")
async def update_notification_rule(rule_id: int, updates: dict = Body(...)):
    """Update a notification rule"""
    print(f"📝 Updating rule {rule_id}: {updates}")
    async with get_db() as db:
        success = await db.update_notification_rule(rule_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        # Invalidate all rules cache (rule_type might have changed)
        from notification_engine import get_notification_engine
        get_notification_engine().invalidate_cache()
        return JSONResponse({"success": True})


@app.delete("/api/notification-rules/{rule_id}")
async def delete_notification_rule(rule_id: int):
    """Delete a notification rule"""
    async with get_db() as db:
        success = await db.delete_notification_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        # Invalidate all rules cache
        from notification_engine import get_notification_engine
        get_notification_engine().invalidate_cache()
        return JSONResponse({"success": True})


@app.post("/api/notification-rules/{rule_id}/toggle")
async def toggle_notification_rule(rule_id: int, active: bool = Query(...)):
    """Toggle a notification rule on/off"""
    async with get_db() as db:
        success = await db.update_notification_rule(rule_id, {"active": active})
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        # Invalidate all rules cache
        from notification_engine import get_notification_engine
        get_notification_engine().invalidate_cache()
        return JSONResponse({"success": True, "active": active})


# ============== END AUTOMATIC PIPELINES ENDPOINTS ==============


# ============== FILTER OPTIONS ENDPOINTS ==============

@app.get("/api/filters/subtypes/{tipo_id}")
async def get_subtypes_for_tipo(tipo_id: int):
    """Get available subtypes for a specific event type"""
    async with get_db() as db:
        subtypes = await db.get_subtypes_by_tipo(tipo_id)
        return JSONResponse(subtypes)


@app.get("/api/filters/distritos/{tipo_id}")
async def get_distritos_for_tipo(tipo_id: int):
    """Get available distritos for a specific event type"""
    async with get_db() as db:
        distritos = await db.get_distritos_by_tipo(tipo_id)
        return JSONResponse(distritos)


# ============== END FILTER OPTIONS ENDPOINTS ==============


@app.get("/api/events/{reference}", response_model=EventData)
async def get_event(reference: str):
    """
    Obtém dados de um evento específico por referência.
    
    - **reference**: Referência do evento (ex: NP-2024-12345 ou LO-2024-67890)
    
    Retorna dados completos incluindo GPS, áreas, tipo, etc.
    """
    # Verifica cache primeiro
    cached = await cache_manager.get(reference)
    if cached:
        return cached
    
    # Verifica base de dados
    async with get_db() as db:
        event = await db.get_event(reference)
        if event:
            await cache_manager.set(reference, event)
            return event

    # Evento não existe - retorna 404 (não faz auto-scraping)
    raise HTTPException(status_code=404, detail=f"Evento não encontrado: {reference}")


@app.get("/api/events", response_model=EventListResponse)
async def get_events(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(50, ge=1, le=100000, description="Eventos por página"),
    tipo: Optional[str] = None,
    tipo_evento: Optional[str] = None,
    distrito: Optional[str] = None
):
    """
    Lista eventos com paginação e filtros.

    - **page**: Número da página (começa em 1)
    - **limit**: Quantidade de resultados por página (max 100000)
    - **tipo**: Filtrar por tipo (Apartamento, Moradia, etc)
    - **tipo_evento**: Filtrar por tipo de evento (imovel, movel)
    - **distrito**: Filtrar por distrito
    """
    async with get_db() as db:
        events, total = await db.list_events(
            page=page,
            limit=limit,
            tipo=tipo,
            tipo_evento=tipo_evento,
            distrito=distrito
        )
        
        return EventListResponse(
            events=events,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )


@app.post("/api/scrape/event/{reference}")
async def trigger_scrape_event(reference: str, background_tasks: BackgroundTasks):
    """
    Força re-scraping de um evento específico (atualiza cache).
    Executa em background.
    """
    background_tasks.add_task(scrape_and_update, reference)
    
    return {
        "message": f"Scraping do evento {reference} iniciado em background",
        "reference": reference
    }


@app.post("/api/scrape/all")
async def trigger_scrape_all(
    background_tasks: BackgroundTasks,
    max_pages: int = Query(None, description="Máximo de páginas para scrape (None = todas)")
):
    """
    Inicia scraping de TODOS os eventos (pode demorar horas).
    Executa em background.
    
    ⚠️ Use com cuidado! Pode gerar muitas requests.
    """
    background_tasks.add_task(scrape_all_events, max_pages)
    
    return {
        "message": "Scraping total iniciado em background",
        "max_pages": max_pages or "todas"
    }


@app.get("/api/scrape/status", response_model=ScraperStatus)
async def get_scraper_status():
    """
    Retorna status atual do scraper (eventos processados, erros, etc).
    """
    return scraper.get_status()


@app.post("/api/scrape/stop")
async def stop_scraper():
    """
    Para o scraping em execução.

    Se o scraper estiver a correr, solicita a paragem graceful.
    """
    if not scraper.is_running:
        raise HTTPException(
            status_code=400,
            detail="Scraper não está em execução"
        )

    scraper.stop()

    return {
        "message": "Paragem do scraper solicitada",
        "status": "stopping"
    }


@app.post("/api/scrape/schedule")
async def schedule_scraping(hours: int = Query(..., ge=1, le=24, description="Intervalo em horas (1-24)")):
    """
    Agenda scraping automático a cada X horas.

    - **hours**: Intervalo em horas (1, 3, 6, 12, 24)

    Remove agendamento anterior se existir.
    """
    global scheduled_job_id

    # Remove job anterior se existir
    if scheduled_job_id and scheduler.get_job(scheduled_job_id):
        scheduler.remove_job(scheduled_job_id)
        print(f"🗑️ Agendamento anterior removido")

    # Cria novo job
    trigger = IntervalTrigger(hours=hours)
    job = scheduler.add_job(
        scheduled_scrape_task,
        trigger=trigger,
        id=f"scrape_every_{hours}h",
        name=f"Scraping a cada {hours}h",
        replace_existing=True
    )

    scheduled_job_id = job.id
    next_run = job.next_run_time

    print(f"⏰ Scraping agendado a cada {hours}h. Próxima execução: {next_run}")

    return {
        "message": f"Scraping agendado a cada {hours} hora(s)",
        "interval_hours": hours,
        "next_run": next_run.isoformat() if next_run else None,
        "job_id": scheduled_job_id
    }


@app.delete("/api/scrape/schedule")
async def cancel_scheduled_scraping():
    """
    Cancela o agendamento automático de scraping.
    """
    global scheduled_job_id

    if not scheduled_job_id:
        raise HTTPException(
            status_code=404,
            detail="Não existe agendamento ativo"
        )

    job = scheduler.get_job(scheduled_job_id)
    if not job:
        scheduled_job_id = None
        raise HTTPException(
            status_code=404,
            detail="Job de agendamento não encontrado"
        )

    scheduler.remove_job(scheduled_job_id)
    print(f"🗑️ Agendamento '{scheduled_job_id}' cancelado")
    scheduled_job_id = None

    return {
        "message": "Agendamento cancelado com sucesso"
    }


@app.get("/api/scrape/schedule")
async def get_schedule_info():
    """
    Retorna informação sobre o agendamento ativo (se existir).
    """
    global scheduled_job_id

    if not scheduled_job_id:
        return {
            "scheduled": False,
            "interval_hours": None,
            "next_run": None
        }

    job = scheduler.get_job(scheduled_job_id)
    if not job:
        scheduled_job_id = None
        return {
            "scheduled": False,
            "interval_hours": None,
            "next_run": None
        }

    # Extrai intervalo do trigger
    interval_hours = None
    if hasattr(job.trigger, 'interval'):
        interval_seconds = job.trigger.interval.total_seconds()
        interval_hours = int(interval_seconds / 3600)

    return {
        "scheduled": True,
        "interval_hours": interval_hours,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        "job_id": job.id
    }


# ============== MULTI-STAGE SCRAPING ENDPOINTS ==============

@app.post("/api/scrape/stage1/ids")
async def scrape_stage1_ids(
    tipo: Optional[int] = Query(None, ge=1, le=6, description="1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo"),
    save_to_db: bool = Query(True, description="Guardar na base de dados")
):
    """
    STAGE 1: Scrape apenas IDs e valores básicos da listagem (rápido).

    AGORA COM INSERÇÃO NA BD: Guarda eventos básicos na BD com referência e valores.

    - **tipo**: 1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos
    - **max_pages**: Máximo de páginas por tipo
    - **save_to_db**: Se True, guarda eventos na BD (default: True)

    Retorna lista de IDs com valores básicos.
    Ideal para descobrir rapidamente o que existe e popular a BD.
    """
    pipeline_state = get_pipeline_state()
    collected_ids = []  # Store IDs as they're collected

    try:
        add_dashboard_log("🔍 STAGE 1: A obter IDs...", "info")

        # Iniciar pipeline state
        tipo_str = "Imóveis" if tipo == 1 else "Móveis" if tipo == 2 else "Todos"
        await pipeline_state.start(
            stage=1,
            stage_name=f"Stage 1 - IDs ({tipo_str})",
            total=0,  # Será atualizado conforme scraping
            details={"tipo": tipo, "max_pages": max_pages, "ids": [], "types_done": 0}
        )

        # Callback to update pipeline state as each type completes
        async def on_type_complete(tipo_nome: str, count: int, totals: dict):
            nonlocal collected_ids
            types_done = len(totals)
            total_ids = sum(totals.values())
            await pipeline_state.update(
                total=total_ids,
                message=f"✓ {tipo_nome}: {count} IDs",
                details={
                    "types_done": types_done,
                    "total_ids": total_ids,
                    "totals_by_type": totals
                }
            )

        ids = await scraper.scrape_ids_only(tipo=tipo, max_pages=max_pages, on_type_complete=on_type_complete)
        collected_ids = ids

        # Store all IDs in pipeline state for frontend access
        await pipeline_state.update(
            total=len(ids),
            message=f"{len(ids)} IDs recolhidos",
            details={"ids": ids, "total_ids": len(ids)}
        )

        # Guardar na BD se solicitado
        saved_count = 0
        if save_to_db:
            await pipeline_state.update(message=f"Guardando {len(ids)} eventos na BD...")

            async with get_db() as db:
                for idx, item in enumerate(ids, 1):
                    try:
                        # Cria evento básico com apenas referência e valores
                        from models import EventDetails

                        event = EventData(
                            reference=item['reference'],
                            tipoEvento=item.get('tipo', 'imovel'),
                            valores=item.get('valores', ValoresLeilao()),
                            detalhes=EventDetails(
                                tipo=item.get('tipo', 'N/A'),
                                subtipo='N/A'
                            ),
                            # Campos vazios serão preenchidos no Stage 2
                            descricao=None,
                            observacoes=None,
                            imagens=[]
                        )

                        await db.save_event(event)
                        await cache_manager.set(event.reference, event)
                        saved_count += 1

                        # Atualizar progresso
                        await pipeline_state.update(
                            current=idx,
                            message=f"Guardando {idx}/{len(ids)} - {item['reference']}"
                        )

                    except Exception as e:
                        log_error(f"Erro ao guardar {item['reference']}", e)
                        await pipeline_state.add_error(f"Erro ao guardar {item['reference']}: {e}")
                        continue

            add_dashboard_log(f"💾 {saved_count} eventos guardados na BD", "success")

        add_dashboard_log(f"✅ Stage 1 completo: {len(ids)} IDs recolhidos", "success")

        # Marcar como completo
        await pipeline_state.complete(
            message=f"✅ {len(ids)} IDs recolhidos{', ' + str(saved_count) + ' guardados' if save_to_db else ''}"
        )

        # Parar pipeline após pequeno delay para UI mostrar
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "stage": 1,
            "total_ids": len(ids),
            "saved_to_db": saved_count if save_to_db else 0,
            "ids": ids,
            "message": f"Stage 1 completo: {len(ids)} IDs recolhidos{', ' + str(saved_count) + ' guardados na BD' if save_to_db else ''}"
        }

    except Exception as e:
        msg = f"❌ Erro no Stage 1: {str(e)}"
        add_dashboard_log(msg, "error")
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/smart/new-events")
async def scrape_smart_new_events(
    tipo: Optional[int] = Query(None, ge=1, le=6, description="1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo")
):
    """
    SCRAPE INTELIGENTE: Identifica automaticamente eventos novos.

    Compara IDs scraped com os já existentes na BD e retorna apenas os novos.

    - **tipo**: 1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos
    - **max_pages**: Máximo de páginas por tipo

    Retorna apenas IDs de eventos que ainda não estão na base de dados.
    """
    try:
        add_dashboard_log("🧠 SCRAPE INTELIGENTE: A identificar eventos novos...", "info")

        # 1. Scrape todos os IDs disponíveis
        all_ids_data = await scraper.scrape_ids_only(tipo=tipo, max_pages=max_pages)
        all_references = [item['reference'] for item in all_ids_data]
        add_dashboard_log(f"📊 Total de eventos encontrados: {len(all_references)}", "info")

        # 2. Obter IDs já existentes na BD
        async with get_db() as db:
            existing_references = await db.get_all_references()

        existing_set = set(existing_references)
        add_dashboard_log(f"💾 Eventos já na BD: {len(existing_references)}", "info")

        # 3. Identificar novos eventos
        new_ids_data = [item for item in all_ids_data if item['reference'] not in existing_set]
        new_count = len(new_ids_data)

        if new_count > 0:
            add_dashboard_log(f"✨ {new_count} eventos novos identificados!", "success")
        else:
            add_dashboard_log("✅ Nenhum evento novo. BD está atualizada.", "success")

        return {
            "total_scraped": len(all_references),
            "already_in_db": len(existing_references),
            "new_events": new_count,
            "new_ids": new_ids_data,
            "message": f"Smart Scraping: {new_count} eventos novos de {len(all_references)} totais"
        }

    except Exception as e:
        msg = f"❌ Erro no scrape inteligente: {str(e)}"
        add_dashboard_log(msg, "error")
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/stage2/details")
async def scrape_stage2_details(
    references: List[str] = Query(..., description="Lista de referências para scrape"),
    save_to_db: bool = Query(True, description="Guardar na base de dados")
):
    """
    STAGE 2: Scrape detalhes completos via API oficial (RÁPIDO!)

    Usa a API interna do e-leiloes.pt para obter dados JSON estruturados.
    Muito mais rápido que HTML scraping.

    - **references**: Lista de referências (ex: ["LO-2024-001", "NP-2024-002"])
    - **save_to_db**: Se True, guarda eventos na BD

    Retorna eventos com todos os detalhes incluindo URLs de imagens.
    """
    pipeline_state = get_pipeline_state()

    try:
        # Iniciar pipeline state
        await pipeline_state.start(
            stage=2,
            stage_name="Stage 2 - API (Fast!)",
            total=len(references),
            details={"save_to_db": save_to_db, "mode": "api"}
        )

        # Progress callback for real-time UI updates
        async def on_progress(current, total, ref):
            await pipeline_state.update(
                current=current,
                message=f"🚀 API: {current}/{total} - {ref}"
            )

        # Use API-based scraping (MUCH FASTER!)
        events = await scraper.scrape_details_via_api(references, on_progress)

        # Save to DB if requested
        if save_to_db and events:
            async with get_db() as db:
                for event in events:
                    await db.save_event(event)
                    await cache_manager.set(event.reference, event)

        # Marcar como completo
        await pipeline_state.complete(
            message=f"✅ {len(events)} eventos via API{' e guardados' if save_to_db else ''}"
        )

        # Parar pipeline após pequeno delay para UI mostrar
        await asyncio.sleep(1)
        await pipeline_state.stop()

        return {
            "stage": 2,
            "mode": "api",
            "total_requested": len(references),
            "total_scraped": len(events),
            "events": [event.model_dump() for event in events],
            "saved_to_db": save_to_db,
            "message": f"Stage 2 completo: {len(events)} eventos via API {'e guardados' if save_to_db else ''}"
        }

    except Exception as e:
        msg = f"Erro no Stage 2: {str(e)}"
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/stage2/api")
async def scrape_stage2_via_api(
    references: List[str] = Query(..., description="Lista de referências para scrape"),
    save_to_db: bool = Query(True, description="Guardar na base de dados")
):
    """
    STAGE 2 VIA API: Scrape detalhes usando a API interna do e-leiloes.pt (MUITO MAIS RÁPIDO!)

    Esta versão usa a API descoberta em /api/eventos/{reference} que retorna
    dados JSON estruturados, eliminando a necessidade de parsing HTML.

    - **references**: Lista de referências (ex: ["LO-2024-001", "NP-2024-002"])
    - **save_to_db**: Se True, guarda eventos na BD em tempo real

    Retorna eventos com todos os detalhes incluindo imagens (URLs já inclusas na API).
    """
    pipeline_state = get_pipeline_state()
    scraped_count = 0

    try:
        # Iniciar pipeline state
        await pipeline_state.start(
            stage=2,
            stage_name="Stage 2 - API (Fast!)",
            total=len(references),
            details={"save_to_db": save_to_db, "mode": "api"}
        )

        # Progress callback
        async def on_progress(current, total, ref):
            nonlocal scraped_count
            scraped_count = current
            await pipeline_state.update(
                current=current,
                message=f"🚀 API: {current}/{total} - {ref}"
            )

        # Use API-based scraping
        events = await scraper.scrape_details_via_api(references, on_progress)

        # Save to DB if requested
        if save_to_db:
            async with get_db() as db:
                for event in events:
                    await db.save_event(event)
                    await cache_manager.set(event.reference, event)

        # Mark as complete
        await pipeline_state.complete(
            message=f"✅ {len(events)} eventos via API{' e guardados' if save_to_db else ''}"
        )

        # Small delay for UI
        await asyncio.sleep(1)
        await pipeline_state.stop()

        return {
            "stage": 2,
            "mode": "api",
            "total_requested": len(references),
            "total_scraped": len(events),
            "events": [event.model_dump() for event in events],
            "saved_to_db": save_to_db,
            "message": f"Stage 2 (API) completo: {len(events)} eventos processados {'e guardados' if save_to_db else ''}"
        }

    except Exception as e:
        msg = f"Erro no Stage 2 (API): {str(e)}"
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/stage3/images")
async def scrape_stage3_images(
    references: List[str] = Query(..., description="Lista de referências para scrape"),
    update_db: bool = Query(True, description="Atualizar eventos na BD com imagens")
):
    """
    STAGE 3: Scrape apenas imagens para lista de IDs.

    - **references**: Lista de referências
    - **update_db**: Se True, atualiza eventos existentes na BD com imagens

    Retorna mapa {reference: [image_urls]}.
    """
    pipeline_state = get_pipeline_state()
    progress_counter = {"count": 0}

    try:
        # Iniciar pipeline state
        await pipeline_state.start(
            stage=3,
            stage_name="Stage 3 - Imagens",
            total=len(references),
            details={"update_db": update_db}
        )

        # Callback para atualizar progresso durante o scraping
        async def on_images_progress(ref: str, images: List[str]):
            progress_counter["count"] += 1
            await pipeline_state.update(
                current=progress_counter["count"],
                message=f"Scraping {progress_counter['count']}/{len(references)} - {ref} ({len(images)} imagens)"
            )

        images_map = await scraper.scrape_images_by_ids(references, on_images_scraped=on_images_progress)

        # Atualiza eventos na BD se solicitado
        updated_count = 0
        if update_db:
            await pipeline_state.update(message=f"Atualizando {len(images_map)} eventos na BD...")

            async with get_db() as db:
                for idx, (ref, images) in enumerate(images_map.items(), 1):
                    # Busca evento existente
                    event = await db.get_event(ref)
                    if event:
                        # Atualiza imagens
                        event.imagens = images
                        event.updated_at = datetime.utcnow()
                        await db.save_event(event)
                        await cache_manager.set(ref, event)
                        updated_count += 1

                        # Atualizar progresso
                        await pipeline_state.update(
                            current=idx,
                            message=f"Atualizando {idx}/{len(images_map)} - {ref} ({len(images)} imagens)"
                        )

        # Marcar como completo
        await pipeline_state.complete(
            message=f"✅ {len(images_map)} eventos processados{', ' + str(updated_count) + ' atualizados' if update_db else ''}"
        )

        # Parar pipeline após pequeno delay para UI mostrar
        await asyncio.sleep(2)
        await pipeline_state.stop()

        return {
            "stage": 3,
            "total_requested": len(references),
            "total_scraped": len(images_map),
            "images_map": images_map,
            "updated_db": update_db,
            "message": f"Stage 3 completo: {len(images_map)} eventos processados"
        }

    except Exception as e:
        msg = f"Erro no Stage 3: {str(e)}"
        await pipeline_state.add_error(msg)
        await pipeline_state.stop()
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/scrape/pipeline")
async def scrape_full_pipeline(
    background_tasks: BackgroundTasks,
    tipo: Optional[int] = Query(None, ge=1, le=6, description="1=Imóveis, 2=Veículos, 3=Direitos, 4=Equipamentos, 5=Mobiliário, 6=Máquinas, None=todos"),
    max_pages: Optional[int] = Query(None, ge=1, description="Máximo de páginas por tipo")
):
    """
    PIPELINE COMPLETO: Executa os 3 stages sequencialmente em background.

    1. Stage 1: Scrape IDs (todos os 6 tipos)
    2. Stage 2: Scrape detalhes
    3. Stage 3: Scrape imagens

    Executa em background e guarda tudo na BD.
    """
    # Check if pipeline is already running
    pipeline_state = get_pipeline_state()
    if pipeline_state.is_active:
        raise HTTPException(
            status_code=409,
            detail="Uma pipeline já está em execução. Use Kill Pipeline para parar primeiro."
        )

    background_tasks.add_task(run_full_pipeline, tipo, max_pages)

    return {
        "message": "Pipeline completo iniciado em background",
        "stages": ["Stage 1: IDs", "Stage 2: Detalhes", "Stage 3: Imagens"],
        "tipo": tipo,
        "max_pages": max_pages
    }


@app.delete("/api/cache")
async def clear_cache():
    """
    Limpa todo o cache Redis (se configurado).
    """
    await cache_manager.clear_all()
    return {"message": "Cache limpo com sucesso"}


@app.delete("/api/database")
async def clear_database():
    """
    Apaga TODOS os dados da base de dados (eventos, histórico, notificações, etc).
    ATENÇÃO: Esta operação é irreversível!
    """
    from sqlalchemy import text
    deleted_counts = {}

    async with get_db() as db:
        # Delete events
        result = await db.session.execute(text("DELETE FROM events"))
        deleted_counts["events"] = result.rowcount

        # Delete price history
        try:
            result = await db.session.execute(text("DELETE FROM price_history"))
            deleted_counts["price_history"] = result.rowcount
        except:
            deleted_counts["price_history"] = 0

        # Delete refresh logs
        try:
            result = await db.session.execute(text("DELETE FROM refresh_logs"))
            deleted_counts["refresh_logs"] = result.rowcount
        except:
            deleted_counts["refresh_logs"] = 0

        # Delete notifications
        try:
            result = await db.session.execute(text("DELETE FROM notification_rules"))
            deleted_counts["notifications"] = result.rowcount
        except:
            deleted_counts["notifications"] = 0

        # Delete ALL pipeline states (table name is singular: pipeline_state)
        try:
            result = await db.session.execute(text("DELETE FROM pipeline_state"))
            deleted_counts["pipeline_states"] = result.rowcount
        except:
            deleted_counts["pipeline_states"] = 0

        await db.session.commit()

    # Limpa também o cache
    await cache_manager.clear_all()

    # Reset pipeline states in memory
    pipeline_state = get_pipeline_state()
    await pipeline_state.stop()

    # Reset auto pipelines manager (X-Monitor, Y-Sync, Z-Watch)
    auto_pipelines = get_auto_pipelines_manager()
    for pipeline_name in auto_pipelines.pipelines:
        auto_pipelines.pipelines[pipeline_name].is_running = False
        auto_pipelines.pipelines[pipeline_name].enabled = False

    # Reset scraper state
    if scraper:
        scraper.is_running = False
        scraper.stop_requested = False

    return {
        "message": "Base de dados limpa com sucesso",
        "deleted": deleted_counts
    }


@app.get("/api/database/check")
async def check_database():
    """
    Verifica integridade da base de dados: duplicados e estatísticas.
    """
    from sqlalchemy import func, select
    from database import EventDB

    async with get_db() as db:
        # Total de eventos
        result = await db.session.execute(
            select(func.count()).select_from(EventDB)
        )
        total = result.scalar()

        # Verificar duplicados por reference
        duplicates_result = await db.session.execute(
            select(EventDB.reference, func.count(EventDB.reference).label('cnt'))
            .group_by(EventDB.reference)
            .having(func.count(EventDB.reference) > 1)
        )
        duplicates = duplicates_result.fetchall()

        # Contar eventos únicos
        unique_result = await db.session.execute(
            select(func.count(func.distinct(EventDB.reference)))
        )
        unique_count = unique_result.scalar()

        return {
            "total_rows": total,
            "unique_references": unique_count,
            "duplicate_references": len(duplicates),
            "duplicates": [{"reference": ref, "count": cnt} for ref, cnt in duplicates[:20]]
        }


@app.post("/api/database/cleanup")
async def cleanup_database():
    """
    Remove eventos duplicados, mantendo apenas o mais recente.
    """
    from sqlalchemy import func, select
    from database import EventDB

    async with get_db() as db:
        # Encontrar duplicados
        duplicates_result = await db.session.execute(
            select(EventDB.reference, func.count(EventDB.reference).label('cnt'))
            .group_by(EventDB.reference)
            .having(func.count(EventDB.reference) > 1)
        )
        duplicates = duplicates_result.fetchall()

        removed_count = 0
        for ref, cnt in duplicates:
            # Buscar todos os eventos com este reference, ordenados por updated_at desc
            events_result = await db.session.execute(
                select(EventDB)
                .where(EventDB.reference == ref)
                .order_by(EventDB.updated_at.desc())
            )
            events = events_result.scalars().all()

            # Manter o primeiro (mais recente), remover os outros
            for event in events[1:]:
                await db.session.delete(event)
                removed_count += 1

        await db.session.commit()

        return {
            "message": f"Cleanup concluído: {removed_count} duplicados removidos",
            "duplicates_found": len(duplicates),
            "removed": removed_count
        }


@app.post("/api/database/migrate-tipos")
async def migrate_event_types():
    """
    Migra tipos de evento antigos para o novo formato.

    Conversões:
    - "imovel" -> "imoveis"
    - "movel" -> "veiculos"
    """
    from sqlalchemy import update, select, func
    from database import EventDB

    migrations = {
        "imovel": "imoveis",
        "movel": "veiculos"
    }

    async with get_db() as db:
        total_updated = 0
        details = []

        for old_type, new_type in migrations.items():
            # Contar quantos existem
            count_result = await db.session.execute(
                select(func.count()).select_from(EventDB).where(EventDB.tipo_evento == old_type)
            )
            count = count_result.scalar()

            if count > 0:
                # Atualizar
                await db.session.execute(
                    update(EventDB).where(EventDB.tipo_evento == old_type).values(tipo_evento=new_type)
                )
                total_updated += count
                details.append(f"{old_type} -> {new_type}: {count} eventos")

        await db.session.commit()

        # Estatísticas finais por tipo
        stats_result = await db.session.execute(
            select(EventDB.tipo_evento, func.count(EventDB.tipo_evento))
            .group_by(EventDB.tipo_evento)
        )
        stats = {tipo: count for tipo, count in stats_result.fetchall()}

        return {
            "message": f"Migração concluída: {total_updated} eventos atualizados",
            "migrations": details,
            "current_stats": stats
        }


@app.get("/api/stats")
async def get_stats():
    """
    Estatísticas gerais da base de dados.
    """
    async with get_db() as db:
        stats = await db.get_stats()
        return stats


@app.get("/api/db/stats")
async def get_db_extended_stats():
    """
    Extended database statistics for maintenance dashboard.
    Returns: total, with_content, with_images, null_lance_atual, incomplete, by_type
    """
    async with get_db() as db:
        stats = await db.get_extended_stats()
        return stats


@app.get("/api/refresh/stats")
async def get_refresh_stats():
    """Get refresh request statistics for the last 24 hours"""
    async with get_db() as db:
        stats = await db.get_refresh_stats()
        return stats


@app.post("/api/refresh/{reference}")
async def refresh_single_event(reference: str):
    """
    Refresh a single event's data by scraping the latest info from e-leiloes.pt.
    This is called when user clicks the refresh button on an event.
    """
    try:
        # Scrape fresh data for this single event
        events = await scraper.scrape_details_via_api([reference], None)

        if not events:
            return JSONResponse(
                {"success": False, "message": "Event not found on source"},
                status_code=404
            )

        event = events[0]

        # Save to database
        async with get_db() as db:
            await db.save_event(event)

            # Log the refresh
            from database import RefreshLogDB
            session = db.session
            refresh_log = RefreshLogDB(reference=reference, refresh_type='price')
            session.add(refresh_log)
            await session.commit()

        # Update cache
        await cache_manager.set(reference, event)

        return {
            "success": True,
            "reference": reference,
            "lance_atual": event.valores.lanceAtual if event.valores else 0,
            "data_fim": event.datas.dataFim.isoformat() if event.datas and event.datas.dataFim else None
        }

    except Exception as e:
        log_error(f"Error refreshing event {reference}", e)
        return JSONResponse(
            {"success": False, "message": str(e)},
            status_code=500
        )


@app.get("/api/dashboard/ending-soon")
async def get_events_ending_soon(hours: int = 24, limit: int = 1000, include_terminated: bool = True, terminated_hours: int = 120):
    """Get events ending within the next X hours + recently terminated events"""
    async with get_db() as db:
        events = await db.get_events_ending_soon(hours=hours, limit=limit, include_terminated=include_terminated, terminated_hours=terminated_hours)
        return JSONResponse(events)


@app.get("/api/dashboard/activity")
async def get_recent_activity():
    """Get recent activity stats for dashboard"""
    async with get_db() as db:
        activity = await db.get_recent_activity()
        return JSONResponse(activity)


@app.get("/api/dashboard/stats-by-distrito")
async def get_stats_by_distrito(limit: int = 5):
    """Get event counts by distrito with breakdown by type"""
    async with get_db() as db:
        stats = await db.get_stats_by_distrito(limit=limit)
        return JSONResponse(stats)


@app.get("/api/dashboard/recent-bids")
async def get_recent_bids(limit: int = 30, hours: int = 24):
    """Get recent price changes from database (last 24h by default)"""
    from price_history import get_recent_changes
    bids = await get_recent_changes(limit=limit, hours=hours)

    # Add ativo status from database for each event
    if bids:
        async with get_db() as db:
            references = [b["reference"] for b in bids]
            # Get ativo and data_fim status for all references
            from sqlalchemy import select
            from database import EventDB
            result = await db.session.execute(
                select(EventDB.reference, EventDB.ativo, EventDB.data_fim)
                .where(EventDB.reference.in_(references))
            )
            event_info = {row.reference: {"ativo": row.ativo, "data_fim": row.data_fim} for row in result}

            # Add ativo and data_fim to each bid
            for bid in bids:
                info = event_info.get(bid["reference"], {})
                bid["ativo"] = info.get("ativo", True)
                # Include data_fim as ISO string for frontend to check expiration locally
                data_fim = info.get("data_fim")
                bid["data_fim"] = data_fim.isoformat() if data_fim else None

    return JSONResponse(bids)


@app.get("/api/dashboard/price-history/{reference}")
async def get_price_history(reference: str):
    """Get complete price history for a specific event"""
    from price_history import get_event_history
    history = await get_event_history(reference)
    return JSONResponse(history)


@app.get("/api/dashboard/price-history-stats")
async def get_price_history_stats():
    """Get statistics about price history tracking"""
    from price_history import get_stats
    stats = await get_stats()
    return JSONResponse(stats)


@app.get("/api/dashboard/recent-price-changes")
async def get_recent_price_changes(limit: int = 30, hours: int = 24):
    """Get recent price changes from the database"""
    from price_history import get_recent_changes
    changes = await get_recent_changes(limit=limit, hours=hours)
    return JSONResponse(changes)


@app.get("/api/dashboard/recent-events")
async def get_recent_events(limit: int = 20, days: int = 7):
    """Get recently scraped events (sorted by scraped_at DESC)"""
    from sqlalchemy import select
    from database import EventDB
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=days)

    async with get_db() as db:
        result = await db.session.execute(
            select(EventDB)
            .where(EventDB.scraped_at >= cutoff)
            .where(EventDB.cancelado == False)
            .where(EventDB.terminado == False)
            .order_by(EventDB.scraped_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()

        return JSONResponse([{
            "reference": e.reference,
            "titulo": e.titulo,
            "tipo": e.tipo,
            "capa": e.capa,
            "distrito": e.distrito,
            "concelho": e.concelho,
            "valor_minimo": e.valor_minimo,
            "lance_atual": e.lance_atual,
            "valor_base": e.valor_base,
            "data_fim": e.data_fim.isoformat() if e.data_fim else None,
            "data_inicio": e.data_inicio.isoformat() if e.data_inicio else None,
            "scraped_at": e.scraped_at.isoformat() if e.scraped_at else None
        } for e in events])


@app.get("/api/volatile/{reference}")
async def get_volatile_data(reference: str):
    """
    Get live volatile data (lanceAtual, dataFim) directly from e-leiloes.pt API.
    Fast - no browser required!
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
            api_url = f"https://www.e-leiloes.pt/api/eventos/{reference}"
            response = await client.get(api_url)

            if response.status_code == 200:
                data = response.json()
                item = data.get('item', {})

                if item:
                    data_fim = None
                    try:
                        if item.get('dataFim'):
                            data_fim = item['dataFim']
                    except:
                        pass

                    return {
                        "reference": reference,
                        "lanceAtual": item.get('lanceAtual', 0),
                        "dataFim": data_fim
                    }

            raise HTTPException(status_code=404, detail=f"Event not found: {reference}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch from e-leiloes.pt: {str(e)}")


@app.get("/api/test/eventos-mais-recentes")
async def test_eventos_mais_recentes():
    """
    Test endpoint to check EventosMaisRecentes API response.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
            api_url = "https://www.e-leiloes.pt/api/EventosMaisRecentes/"

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.e-leiloes.pt/',
                'Origin': 'https://www.e-leiloes.pt'
            }

            response = await client.get(api_url, headers=headers)

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response.json() if response.status_code == 200 else response.text[:500]
            }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/db/fix-nulls")
async def fix_null_lance_atual():
    """
    Fix all NULL lance_atual values to 0.
    """
    async with get_db() as db:
        count = await db.fix_null_lance_atual()
        return {"fixed": count, "message": f"Corrigidos {count} eventos com lance_atual NULL"}


@app.get("/api/db/incomplete")
async def get_incomplete_events():
    """
    Get references of events without content (for re-scraping).
    """
    async with get_db() as db:
        refs = await db.get_references_without_content()
        return {"count": len(refs), "references": refs}


@app.get("/api/db/no-images")
async def get_events_without_images():
    """
    Get references of events without images (for re-scraping).
    """
    async with get_db() as db:
        refs = await db.get_references_without_images()
        return {"count": len(refs), "references": refs}


@app.post("/api/db/update-prices")
async def update_prices_batch(background_tasks: BackgroundTasks):
    """
    Trigger price update for all events.
    Uses the discovered e-leiloes.pt API for fast price updates!
    """
    if scraper.is_running:
        raise HTTPException(status_code=409, detail="Scraper já em execução")

    async def update_prices_task():
        pipeline_state = get_pipeline_state()
        try:
            add_dashboard_log("💰 Iniciando atualização de preços via API...", "info")

            async with get_db() as db:
                # Get all references
                refs = await db.get_all_references()

            if not refs:
                add_dashboard_log("⚠️ Nenhum evento na BD para atualizar", "warning")
                return

            await pipeline_state.start(
                stage=0,
                stage_name="Atualizar Preços (API)",
                total=len(refs)
            )

            # Progress callback
            async def on_progress(current, total, ref):
                await pipeline_state.update(
                    current=current,
                    message=f"💰 {ref}: a verificar..."
                )

            # Scrape prices via API (FAST!)
            results = await scraper.scrape_volatile_via_api(refs, on_progress)

            # Update database
            updated = 0
            async with get_db() as db:
                for result in results:
                    if result.get('lanceAtual') is not None:
                        success = await db.update_event_price(
                            result['reference'],
                            result['lanceAtual'],
                            result.get('dataFim')
                        )
                        if success:
                            updated += 1

            await pipeline_state.complete(f"Preços atualizados: {updated}/{len(refs)}")
            add_dashboard_log(f"✅ Atualização de preços concluída: {updated}/{len(refs)}", "success")

        except Exception as e:
            await pipeline_state.add_error(str(e))
            add_dashboard_log(f"❌ Erro na atualização de preços: {e}", "error")
        finally:
            await pipeline_state.stop()

    background_tasks.add_task(update_prices_task)
    return {"message": "Atualização de preços iniciada em background"}


@app.get("/api/logs")
async def get_logs():
    """
    Retorna os logs recentes do scraping e limpa o buffer.
    Este endpoint é chamado pelo dashboard console para mostrar logs em tempo real.
    """
    logs_to_return = []

    with log_lock:
        # Copy all logs
        logs_to_return = list(log_buffer)
        # Clear buffer after reading
        log_buffer.clear()

    return {"logs": logs_to_return}


@app.get("/api/logs/stream")
async def stream_logs():
    """
    Server-Sent Events (SSE) endpoint para logs em tempo real.
    Conecta a este endpoint para receber logs instantaneamente.

    Formato do evento:
    {
        "message": "Log message",
        "level": "info|success|warning|error",
        "timestamp": "2025-01-01T12:00:00"
    }
    """
    async def log_stream():
        queue = asyncio.Queue()
        log_sse_clients.add(queue)

        try:
            # Send connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to log stream'})}\n\n"

            while True:
                try:
                    log_entry = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps({'type': 'log', **log_entry})}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            log_sse_clients.discard(queue)

    return StreamingResponse(
        log_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/pipeline-history")
async def get_pipeline_history(limit: int = Query(20, ge=1, le=50)):
    """
    Retorna o histórico de execuções de pipelines.

    - **limit**: Número máximo de entradas (1-50)

    Retorna lista de execuções com:
    - pipeline: tipo da pipeline
    - status: "started" | "completed" | "error"
    - timestamp: quando executou
    - details: informações adicionais
    """
    with pipeline_history_lock:
        history = list(pipeline_history)

    # Return most recent first
    history.reverse()
    return {"history": history[:limit], "total": len(history)}


# ============== BACKGROUND TASKS ==============

async def scrape_and_update(reference: str):
    """Scrape um evento e atualiza BD + cache"""
    try:
        event_data = await scraper.scrape_event(reference)
        
        async with get_db() as db:
            await db.save_event(event_data)
        
        await cache_manager.set(reference, event_data)
        
        log_info(f"Evento {reference} atualizado")
    except Exception as e:
        log_error(f"Erro ao atualizar {reference}", e)


async def scrape_all_events(max_pages: Optional[int] = None):
    """Scrape todos os eventos do site"""
    try:
        print(f"🚀 Iniciando scraping total (max_pages={max_pages})...")

        all_events = await scraper.scrape_all_events(max_pages=max_pages)

        async with get_db() as db:
            for event in all_events:
                await db.save_event(event)
                await cache_manager.set(event.reference, event)

        log_info(f"Scraping total concluído: {len(all_events)} eventos")

    except Exception as e:
        log_error("Erro no scraping total", e)


async def scheduled_scrape_task():
    """
    Task agendada para scraping automático.
    Usa a mesma lógica de scrape_all_events mas é chamada pelo scheduler.
    """
    if scraper.is_running:
        print("⚠️ Scraping já em execução. Pulando execução agendada.")
        return

    print(f"⏰ Iniciando scraping agendado às {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await scrape_all_events(max_pages=None)


async def run_full_pipeline(tipo: Optional[int], max_pages: Optional[int]):
    """
    Executa o pipeline completo de 3 stages em sequência.

    Stage 1: Scrape IDs → Stage 2: Scrape Detalhes → Stage 3: Scrape Imagens
    """
    pipeline_state = get_pipeline_state()
    start_time = datetime.now()

    # Register pipeline start in history
    add_pipeline_history("full_pipeline", "started", {"tipo": tipo, "max_pages": max_pages})

    try:
        # CRITICAL: Clean pipeline state at start
        await pipeline_state.stop()

        msg = f"🚀 Iniciando pipeline completo (tipo={tipo}, max_pages={max_pages})..."
        print(msg)
        add_dashboard_log(msg, "info")

        # ===== STAGE 1: Scrape IDs =====
        tipo_str = "Imóveis" if tipo == 1 else "Móveis" if tipo == 2 else "Todos"
        await pipeline_state.start(
            stage=1,
            stage_name=f"Stage 1 - IDs ({tipo_str})",
            total=6 if tipo is None else 1,  # Number of types to scrape
            details={"tipo": tipo, "max_pages": max_pages}
        )

        # Set initial message showing "Total: 0"
        await pipeline_state.update(
            current=0,
            total=0,
            message="Total: 0",
            details={"types_done": 0, "total_ids": 0, "breakdown": {}}
        )

        add_dashboard_log("🔍 STAGE 1: SCRAPING IDs", "info")

        # Callback to log progress as each type completes
        type_counter = {"count": 0}

        async def on_type_complete(tipo_nome: str, count: int, totals: dict):
            """Log when each type is complete"""
            type_counter["count"] += 1
            total_ids = sum(totals.values())

            # Build totals string: "Total: X | Imóveis: X | Veículos: X"
            totals_parts = [f"Total: {total_ids}"]
            tipo_names_map = {
                "imoveis": "Imóveis",
                "veiculos": "Veículos",
                "direitos": "Direitos",
                "equipamentos": "Equipamentos",
                "mobiliario": "Mobiliário",
                "maquinas": "Máquinas"
            }
            for tipo_key, tipo_count in totals.items():
                display_name = tipo_names_map.get(tipo_key, tipo_key)
                totals_parts.append(f"{display_name}: {tipo_count}")

            msg = " | ".join(totals_parts)
            add_dashboard_log(f"✓ {tipo_nome}: {count} IDs | {msg}", "info")

            # Update pipeline state - use total_ids for display
            await pipeline_state.update(
                current=total_ids,  # Show total IDs collected
                total=total_ids,    # Same value (we don't know final total)
                message=msg,
                details={"types_done": type_counter["count"], "total_ids": total_ids, "breakdown": totals}
            )

        # Check if scraper was stopped before starting
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline cancelada antes de iniciar", "warning")
            await pipeline_state.stop()
            return

        ids_data = await scraper.scrape_ids_only(
            tipo=tipo,
            max_pages=max_pages,
            on_type_complete=on_type_complete
        )

        references = [item['reference'] for item in ids_data]
        # Mapa de referência -> tipo_evento para o Stage 2
        tipo_map = {item['reference']: item.get('tipo_evento', 'imoveis') for item in ids_data}

        # ===== INSERIR IDs NA BD IMEDIATAMENTE =====
        # Isto garante que o tipo_evento é preservado mesmo se a pipeline for interrompida
        new_count = 0
        async with get_db() as db:
            for item in ids_data:
                ref = item['reference']
                tipo_ev = item.get('tipo_evento', 'imovel')
                was_new = await db.insert_event_stub(ref, tipo_ev)
                if was_new:
                    new_count += 1

        add_dashboard_log(f"💾 {new_count} novos IDs inseridos na BD ({len(references) - new_count} já existiam)", "info")

        # Check if stopped during scraping - but still report what we got
        if scraper.stop_requested:
            if len(references) > 0:
                msg = f"🛑 Pipeline interrompida - {len(references)} IDs recolhidos parcialmente"
                add_dashboard_log(msg, "warning")
                # Update state to show what we collected
                await pipeline_state.update(total=len(references), message=msg)
            else:
                add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False  # Reset flag
            return

        # Update total after scraping
        await pipeline_state.update(total=len(references), message=f"{len(references)} IDs recolhidos")
        await pipeline_state.complete(message=f"✅ Stage 1: {len(references)} IDs recolhidos")

        msg = f"✅ Stage 1: {len(references)} IDs recolhidos"
        print(msg)
        add_dashboard_log(msg, "success")

        if not references:
            msg = "⚠️ Nenhum ID encontrado. Pipeline terminado."
            print(msg)
            add_dashboard_log(msg, "warning")
            await asyncio.sleep(2)
            await pipeline_state.stop()
            return

        # ===== STAGE 2: Scrape Detalhes =====
        # Check if stopped
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        await pipeline_state.start(
            stage=2,
            stage_name="Stage 2 - API (Fast!)",
            total=len(references),
            details={"save_to_db": True, "mode": "api"}
        )

        add_dashboard_log("🚀 STAGE 2: SCRAPING VIA API (FAST!)", "info")

        # Progress callback for real-time UI updates
        async def on_progress(current, total, ref):
            await pipeline_state.update(
                current=current,
                message=f"🚀 API: {current}/{total} - {ref}"
            )

        # Use FAST API scraping - httpx concurrent, ~10x faster!
        events = await scraper.scrape_details_fast(references, on_progress, batch_size=15)

        # Check if stopped during scraping
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        # Save events to database
        if events:
            async with get_db() as db:
                for event in events:
                    await db.save_event(event)
                    await cache_manager.set(event.reference, event)

        await pipeline_state.complete(message=f"✅ Stage 2: {len(events)} eventos via API (com imagens)")

        msg = f"✅ Stage 2: {len(events)} eventos via API (com imagens incluídas)"
        print(msg)
        add_dashboard_log(msg, "success")

        # NOTE: Stage 3 (images) is no longer needed - API includes image URLs!

        # Final message
        msg = f"🎉 PIPELINE COMPLETO! IDs: {len(references)} | Eventos: {len(events)}"
        print(msg)
        add_dashboard_log(msg, "success")

        # Register completion in history
        duration = (datetime.now() - start_time).total_seconds()
        add_pipeline_history("full_pipeline", "completed", {
            "ids": len(references),
            "events": len(events),
            "duration_seconds": round(duration, 1)
        })

        # Delay to show final message, then stop
        await asyncio.sleep(3)
        await pipeline_state.stop()

    except Exception as e:
        msg = f"Erro no pipeline: {e}"
        log_exception(msg)
        add_dashboard_log(f"❌ {msg}", "error")
        await pipeline_state.add_error(msg)

        # Register error in history
        duration = (datetime.now() - start_time).total_seconds()
        add_pipeline_history("full_pipeline", "error", {
            "error": str(e),
            "duration_seconds": round(duration, 1)
        })

        await asyncio.sleep(2)
        await pipeline_state.stop()


# ============== API-BASED PIPELINE (FAST!) ==============

@app.post("/api/pipeline/api")
async def start_api_pipeline(
    background_tasks: BackgroundTasks,
    tipo: Optional[int] = Query(None, description="1=Imóveis, 2=Veículos, etc."),
    max_pages: Optional[int] = Query(None, description="Limite de páginas por tipo")
):
    """
    Pipeline RÁPIDO usando a API oficial do e-leiloes.pt!

    Diferenças do pipeline normal:
    - Stage 2+3 combinados: API retorna detalhes E imagens num só request
    - ~5x mais rápido que HTML scraping
    - Dados mais completos e estruturados
    """
    if scraper.is_running:
        raise HTTPException(status_code=409, detail="Scraper já em execução")

    background_tasks.add_task(run_api_pipeline, tipo, max_pages)

    return {
        "message": "🚀 API Pipeline iniciado!",
        "tipo": tipo,
        "max_pages": max_pages,
        "mode": "api"
    }


async def run_api_pipeline(tipo: Optional[int], max_pages: Optional[int]):
    """
    Pipeline RÁPIDO usando a API oficial do e-leiloes.pt!

    Stage 1: Scrape IDs das listagens (igual ao pipeline normal)
    Stage 2: Usa API para obter TUDO (detalhes + imagens) - SEM Stage 3!
    """
    pipeline_state = get_pipeline_state()
    start_time = datetime.now()
    lock_acquired = False

    # Get auto pipelines manager for mutex lock
    from auto_pipelines import get_auto_pipelines_manager
    pipelines_manager = get_auto_pipelines_manager()

    # Register pipeline start in history
    add_pipeline_history("api_pipeline", "started", {"tipo": tipo, "max_pages": max_pages})

    try:
        # Try to acquire heavy pipeline lock (mutex with Y-Sync, Z-Watch)
        lock_acquired = await pipelines_manager.acquire_heavy_lock("Pipeline API")
        if not lock_acquired:
            msg = "⏸️ Pipeline API não pode correr - outra pipeline pesada em execução"
            print(msg)
            add_dashboard_log(msg, "warning")
            return

        # CRITICAL: Clean pipeline state at start
        await pipeline_state.stop()

        msg = f"🚀 Iniciando API Pipeline (tipo={tipo}, max_pages={max_pages})..."
        print(msg)
        add_dashboard_log(msg, "info")
        add_dashboard_log("💡 Usando API oficial - muito mais rápido!", "info")

        # ===== STAGE 1: Scrape IDs (igual ao pipeline normal) =====
        tipo_str = "Imóveis" if tipo == 1 else "Veículos" if tipo == 2 else "Todos"
        await pipeline_state.start(
            stage=1,
            stage_name=f"Stage 1 - IDs ({tipo_str})",
            total=0,
            details={"tipo": tipo, "max_pages": max_pages, "mode": "api"}
        )

        await pipeline_state.update(
            current=0,
            total=0,
            message="A iniciar recolha de IDs...",
            details={"types_done": 0, "total_ids": 0, "breakdown": {}}
        )

        add_dashboard_log("🔍 STAGE 1: SCRAPING IDs", "info")

        # Track progress across types
        progress_state = {"total": 0, "breakdown": {}, "current_type": ""}

        async def on_page_progress(tipo_nome: str, page_num: int, page_count: int, total_count: int, offset: int):
            """Called after each page - updates total in real-time"""
            # Update running total for current type
            progress_state["current_type"] = tipo_nome
            # Calculate grand total (previous types + current type progress)
            prev_types_total = sum(v for k, v in progress_state["breakdown"].items() if k != tipo_nome)
            grand_total = prev_types_total + total_count

            await pipeline_state.update(
                current=grand_total,
                total=grand_total,
                message=f"🔍 {tipo_nome} - Pág {page_num}: +{page_count} (total: {grand_total})"
            )

        async def on_type_complete(tipo_nome: str, count: int, totals: dict):
            """Called when a type finishes - shows breakdown"""
            progress_state["breakdown"] = totals.copy()
            total_ids = sum(totals.values())
            progress_state["total"] = total_ids

            # Build summary message
            totals_parts = [f"Total: {total_ids}"]
            tipo_names_map = {
                "imoveis": "Imóveis",
                "veiculos": "Veículos",
                "direitos": "Direitos",
                "equipamentos": "Equipamentos",
                "mobiliario": "Mobiliário",
                "maquinas": "Máquinas"
            }
            for tipo_key, tipo_count in totals.items():
                display_name = tipo_names_map.get(tipo_key, tipo_key)
                totals_parts.append(f"{display_name}: {tipo_count}")

            msg = " | ".join(totals_parts)
            add_dashboard_log(f"✓ {tipo_nome}: {count} IDs", "info")

            await pipeline_state.update(
                current=total_ids,
                total=total_ids,
                message=msg,
                details={"total_ids": total_ids, "breakdown": totals}
            )

        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline cancelada antes de iniciar", "warning")
            await pipeline_state.stop()
            return

        ids_data = await scraper.scrape_ids_only(
            tipo=tipo,
            max_pages=max_pages,
            on_type_complete=on_type_complete,
            on_page_progress=on_page_progress
        )

        references = [item['reference'] for item in ids_data]
        tipo_map = {item['reference']: item.get('tipo_evento', 'imoveis') for item in ids_data}

        # BATCH INSERT - muito mais rápido!
        await pipeline_state.update(
            message=f"💾 A guardar {len(references)} IDs na BD (batch)...",
            details={"phase": "saving_ids"}
        )

        # Mapeamento tipo_evento (string) para tipo_id (int)
        tipo_str_to_id = {
            'imoveis': 1, 'veiculos': 2, 'equipamentos': 3,
            'mobiliario': 4, 'maquinas': 5, 'direitos': 6,
            'imovel': 1, 'movel': 2  # Legacy compatibility
        }

        # Preparar lista para batch insert
        batch_items = [
            {
                'reference': item['reference'],
                'tipo_id': tipo_str_to_id.get(item.get('tipo_evento', 'imoveis'), 1)
            }
            for item in ids_data
        ]

        async with get_db() as db:
            new_count = await db.insert_event_stubs_batch(batch_items)

        add_dashboard_log(f"💾 {new_count} novos IDs inseridos ({len(references) - new_count} já existiam)", "info")

        if scraper.stop_requested:
            if len(references) > 0:
                msg = f"🛑 Pipeline interrompida - {len(references)} IDs recolhidos parcialmente"
                add_dashboard_log(msg, "warning")
                await pipeline_state.update(total=len(references), message=msg)
            else:
                add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        # Stage 1 complete - log and prepare for Stage 2
        msg = f"✅ Stage 1 completo: {len(references)} IDs ({new_count} novos)"
        print(msg)
        add_dashboard_log(msg, "success")
        await pipeline_state.update(
            message=msg,
            current=len(references),
            total=len(references)
        )

        if not references:
            msg = "⚠️ Nenhum ID encontrado. Pipeline terminado."
            print(msg)
            add_dashboard_log(msg, "warning")
            await asyncio.sleep(2)
            await pipeline_state.stop()
            return

        # ===== STAGE 2: Fetch full details via API =====
        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        await pipeline_state.start(
            stage=2,
            stage_name="Stage 2 - Detalhes via API",
            total=len(references),
            details={"save_to_db": True, "mode": "api"}
        )

        add_dashboard_log(f"📡 STAGE 2: A obter detalhes de {len(references)} eventos via API...", "info")

        scraped_count = 0
        success_count = 0

        async def on_progress(current: int, total: int, ref: str):
            nonlocal scraped_count
            scraped_count = current
            pct = int((current / total) * 100) if total > 0 else 0
            await pipeline_state.update(
                current=current,
                message=f"📡 A obter detalhes: {current}/{total} ({pct}%)"
            )

        # Use FAST API scraping - httpx concurrent, ~10x faster than Playwright!
        events = await scraper.scrape_details_fast(references, on_progress, batch_size=15)

        if scraper.stop_requested:
            add_dashboard_log("🛑 Pipeline interrompida pelo utilizador", "warning")
            await pipeline_state.stop()
            scraper.stop_requested = False
            return

        # BATCH SAVE com progresso
        total_events = len(events)

        async def on_db_progress(processed: int, total: int):
            pct = int((processed / total) * 100) if total > 0 else 0
            await pipeline_state.update(
                message=f"💾 A guardar na BD: {processed}/{total} ({pct}%)"
            )

        async with get_db() as db:
            inserted, updated = await db.save_events_batch(
                events,
                chunk_size=50,
                on_progress=on_db_progress
            )
            success_count = inserted + updated

        # Atualizar estado imediatamente após BD save
        await pipeline_state.update(message=f"✅ BD: {inserted} novos + {updated} atualizados")
        add_dashboard_log(f"💾 BD: {inserted} novos + {updated} atualizados", "info")

        # Count images (fotos is a list of FotoItem or None)
        total_images = sum(len(event.fotos) if event.fotos else 0 for event in events)

        # Final message
        duration = (datetime.now() - start_time).total_seconds()
        duration_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{int(duration)}s"

        msg = f"🎉 PIPELINE COMPLETO em {duration_str}! Eventos: {success_count} | Imagens: {total_images}"
        print(msg)
        add_dashboard_log(msg, "success")

        await pipeline_state.update(message=msg)

        # Register completion in history
        add_pipeline_history("api_pipeline", "completed", {
            "ids": len(references),
            "events": success_count,
            "images": total_images,
            "duration_seconds": round(duration, 1)
        })

        # Small delay to show completion message, then stop
        await asyncio.sleep(2)
        await pipeline_state.stop()

    except Exception as e:
        msg = f"Erro no API pipeline: {e}"
        log_exception(msg)
        add_dashboard_log(f"❌ {msg}", "error")
        await pipeline_state.add_error(msg)

        # Register error in history
        duration = (datetime.now() - start_time).total_seconds()
        add_pipeline_history("api_pipeline", "error", {
            "error": str(e),
            "duration_seconds": round(duration, 1)
        })

        await asyncio.sleep(2)
        await pipeline_state.stop()

    finally:
        # Release heavy pipeline lock
        if lock_acquired:
            pipelines_manager.release_heavy_lock("Pipeline API")


# ============== SSE & STREAMING ENDPOINTS ==============

@app.get("/api/events/stream")
async def stream_events(
    limit: int = Query(5000, ge=1, le=5000, description="Max events to stream"),
    tipo_evento: Optional[str] = None,
    distrito: Optional[str] = None
):
    """
    Stream events one by one for progressive loading.
    Each event is sent as a JSON line (NDJSON format).
    Frontend can render each card as it arrives.
    """
    async def event_generator():
        async with get_db() as db:
            events, total = await db.list_events(
                page=1,
                limit=limit,
                tipo_evento=tipo_evento,
                distrito=distrito
            )

            # First, send metadata
            yield json.dumps({"type": "meta", "total": total}) + "\n"

            # Then stream events one by one
            for event in events:
                yield json.dumps({
                    "type": "event",
                    "data": event.model_dump(mode='json')
                }) + "\n"
                # Small delay to allow progressive rendering
                await asyncio.sleep(0.01)

            # Signal end of stream
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.get("/api/live/events")
async def live_price_updates():
    """
    Server-Sent Events (SSE) endpoint for real-time price updates.
    Connect to this endpoint to receive live price changes as they happen.

    Event format:
    {
        "reference": "LO1234567890",
        "old_price": 100.0,
        "new_price": 150.0,
        "time_remaining": "5min",
        "timestamp": "2025-01-01T12:00:00"
    }
    """
    async def event_stream():
        queue = asyncio.Queue()
        sse_clients.add(queue)

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to live price updates'})}\n\n"

            # Keep connection alive and send updates
            while True:
                try:
                    # Wait for update with timeout (for keepalive)
                    update = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(update)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_clients.discard(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============== ERRO HANDLERS ==============

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Recurso não encontrado"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    # Desabilita reload no Windows para evitar conflitos com Playwright
    reload_enabled = False if sys.platform == 'win32' else True
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info"
    )
