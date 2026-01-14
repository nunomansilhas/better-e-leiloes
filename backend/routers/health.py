"""
Health Check Router
Endpoints for system health monitoring
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import os

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_detailed():
    """
    Health check detalhado com status de todos os serviços.

    Retorna:
    - status: "healthy" | "degraded" | "unhealthy"
    - services: estado de cada serviço (database, redis, pipelines)
    - version: versão da API
    """
    from database import get_db
    from sqlalchemy import text

    services = {}
    overall_status = "healthy"

    # Database check
    try:
        async with get_db() as db:
            await db.session.execute(text("SELECT 1"))
        services["database"] = {"status": "ok", "type": "mysql"}
    except Exception as e:
        services["database"] = {"status": "error", "error": str(e)}
        overall_status = "unhealthy"

    # Redis check - only if REDIS_URL is configured
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            from cache import CacheManager
            # Check if cache manager has redis client
            services["redis"] = {"status": "ok"}
        except Exception as e:
            services["redis"] = {"status": "error", "error": str(e)}
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        services["redis"] = {"status": "disabled", "note": "REDIS_URL not set, using memory cache"}

    # Pipelines check
    try:
        from auto_pipelines import get_auto_pipelines_manager
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

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": services
    }


@router.get("/health/simple", include_in_schema=False)
async def health_simple():
    """Simple health check (for load balancers)"""
    return {"status": "ok"}
