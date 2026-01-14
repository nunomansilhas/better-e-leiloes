"""
Prometheus Metrics Router
Endpoints for metrics and monitoring
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Monitoring"])


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Scrape this endpoint with Prometheus to collect application metrics.
    Default scrape interval: 15s

    Example prometheus.yml config:
    ```yaml
    scrape_configs:
      - job_name: 'eleiloes'
        static_configs:
          - targets: ['localhost:8000']
    ```
    """
    from metrics import get_metrics_response
    return get_metrics_response()


@router.get("/api/metrics/summary")
async def metrics_summary():
    """
    Human-readable metrics summary.

    Returns key metrics in JSON format for dashboard display.
    """
    from prometheus_client import REGISTRY
    from database import get_db, engine

    # Get current metric values
    metrics = {
        "requests": {},
        "database": {},
        "cache": {},
        "pipelines": {},
        "events": {}
    }

    try:
        # Database pool stats
        pool = engine.pool
        metrics["database"] = {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin()
        }
    except Exception:
        pass

    try:
        # Cache stats
        from main import cache_manager
        if cache_manager:
            stats = cache_manager.get_cache_stats()
            metrics["cache"] = stats
    except Exception:
        pass

    try:
        # Pipeline status
        from auto_pipelines import get_auto_pipelines_manager
        pm = get_auto_pipelines_manager()
        status = pm.get_status()
        metrics["pipelines"] = {
            name: {
                "enabled": p.get("enabled", False),
                "is_running": p.get("is_running", False),
                "runs_count": p.get("runs_count", 0)
            }
            for name, p in status.get("pipelines", {}).items()
        }
    except Exception:
        pass

    try:
        # Events count
        async with get_db() as db:
            from sqlalchemy import select, func
            from database import EventDB

            total = await db.session.scalar(select(func.count()).select_from(EventDB))
            active = await db.session.scalar(
                select(func.count()).select_from(EventDB).where(EventDB.terminado == False)
            )
            metrics["events"] = {
                "total": total or 0,
                "active": active or 0,
                "terminated": (total or 0) - (active or 0)
            }
    except Exception:
        pass

    return metrics


@router.post("/api/metrics/update")
async def update_metrics():
    """
    Manually trigger metrics update.

    Updates event counts and other database-derived metrics.
    """
    from database import get_db
    from metrics import update_events_metrics, update_cache_metrics
    from main import cache_manager

    try:
        async with get_db() as db:
            await update_events_metrics(db)

        if cache_manager:
            update_cache_metrics(cache_manager)

        return {"success": True, "message": "Metrics updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}
