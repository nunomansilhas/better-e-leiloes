"""
Prometheus Metrics Module
Exposes application metrics for monitoring
"""

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
from functools import wraps


# ============== Application Info ==============

APP_INFO = Info('eleiloes_app', 'E-Leiloes API application info')
APP_INFO.info({
    'version': '2.0.0',
    'name': 'E-Leiloes Data API'
})


# ============== Request Metrics ==============

REQUEST_COUNT = Counter(
    'eleiloes_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'eleiloes_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'eleiloes_http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint']
)


# ============== Database Metrics ==============

DB_QUERY_COUNT = Counter(
    'eleiloes_db_queries_total',
    'Total database queries',
    ['operation']  # select, insert, update, delete
)

DB_QUERY_LATENCY = Histogram(
    'eleiloes_db_query_duration_seconds',
    'Database query latency in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

DB_CONNECTION_POOL = Gauge(
    'eleiloes_db_pool_connections',
    'Database connection pool status',
    ['state']  # active, idle, overflow
)


# ============== Events Metrics ==============

EVENTS_TOTAL = Gauge(
    'eleiloes_events_total',
    'Total number of events in database',
    ['status']  # active, terminated, cancelled
)

EVENTS_BY_TYPE = Gauge(
    'eleiloes_events_by_type',
    'Number of events by type',
    ['tipo_id', 'tipo_name']
)

EVENTS_BY_DISTRITO = Gauge(
    'eleiloes_events_by_distrito',
    'Number of events by distrito',
    ['distrito']
)


# ============== Cache Metrics ==============

CACHE_HITS = Counter(
    'eleiloes_cache_hits_total',
    'Total cache hits'
)

CACHE_MISSES = Counter(
    'eleiloes_cache_misses_total',
    'Total cache misses'
)

CACHE_SIZE = Gauge(
    'eleiloes_cache_size',
    'Number of items in cache'
)


# ============== Pipeline Metrics ==============

PIPELINE_RUNS = Counter(
    'eleiloes_pipeline_runs_total',
    'Total pipeline executions',
    ['pipeline_type', 'status']  # x_monitor, y_sync, z_watch | success, error
)

PIPELINE_DURATION = Histogram(
    'eleiloes_pipeline_duration_seconds',
    'Pipeline execution duration',
    ['pipeline_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

PIPELINE_ITEMS_PROCESSED = Counter(
    'eleiloes_pipeline_items_processed_total',
    'Total items processed by pipelines',
    ['pipeline_type']
)

PIPELINE_RUNNING = Gauge(
    'eleiloes_pipeline_running',
    'Whether a pipeline is currently running',
    ['pipeline_type']
)


# ============== Scraper Metrics ==============

SCRAPER_REQUESTS = Counter(
    'eleiloes_scraper_requests_total',
    'Total scraper HTTP requests',
    ['status']  # success, error
)

SCRAPER_EVENTS_SCRAPED = Counter(
    'eleiloes_scraper_events_scraped_total',
    'Total events scraped'
)


# ============== Notifications Metrics ==============

NOTIFICATIONS_SENT = Counter(
    'eleiloes_notifications_sent_total',
    'Total notifications sent',
    ['type']  # new_event, price_change, ending_soon
)

NOTIFICATIONS_PENDING = Gauge(
    'eleiloes_notifications_pending',
    'Number of pending notifications'
)


# ============== Rate Limiting Metrics ==============

RATE_LIMIT_HITS = Counter(
    'eleiloes_rate_limit_hits_total',
    'Total rate limit hits'
)


# ============== Helper Functions ==============

def track_request_time(method: str, endpoint: str):
    """Decorator to track request timing"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=200
                ).inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=500
                ).inc()
                raise
            finally:
                REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(
                    time.time() - start_time
                )
                REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        return wrapper
    return decorator


def track_db_query(operation: str):
    """Context manager to track database query timing"""
    class DBQueryTracker:
        def __init__(self):
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            DB_QUERY_COUNT.labels(operation=operation).inc()
            DB_QUERY_LATENCY.labels(operation=operation).observe(duration)

    return DBQueryTracker()


async def update_events_metrics(db):
    """Update events-related metrics from database"""
    from sqlalchemy import select, func
    from database import EventDB

    try:
        # Total by status
        result = await db.session.execute(
            select(
                func.sum(func.IF(EventDB.terminado == False, 1, 0)).label('active'),
                func.sum(func.IF(EventDB.terminado == True, 1, 0)).label('terminated'),
                func.sum(func.IF(EventDB.cancelado == True, 1, 0)).label('cancelled')
            )
        )
        row = result.first()
        if row:
            EVENTS_TOTAL.labels(status='active').set(row.active or 0)
            EVENTS_TOTAL.labels(status='terminated').set(row.terminated or 0)
            EVENTS_TOTAL.labels(status='cancelled').set(row.cancelled or 0)

        # By type
        tipo_names = {1: 'Imoveis', 2: 'Veiculos', 3: 'Outros', 4: 'Direitos', 5: 'Moveis', 6: 'Unidades'}
        result = await db.session.execute(
            select(EventDB.tipo_id, func.count()).group_by(EventDB.tipo_id)
        )
        for tipo_id, count in result:
            if tipo_id:
                EVENTS_BY_TYPE.labels(
                    tipo_id=str(tipo_id),
                    tipo_name=tipo_names.get(tipo_id, 'Unknown')
                ).set(count)

        # By distrito (top 10)
        result = await db.session.execute(
            select(EventDB.distrito, func.count())
            .where(EventDB.distrito.isnot(None))
            .group_by(EventDB.distrito)
            .order_by(func.count().desc())
            .limit(10)
        )
        for distrito, count in result:
            if distrito:
                EVENTS_BY_DISTRITO.labels(distrito=distrito).set(count)

    except Exception:
        pass  # Metrics update should not break the app


def update_cache_metrics(cache_manager):
    """Update cache-related metrics"""
    stats = cache_manager.get_cache_stats()
    CACHE_SIZE.set(stats.get('memory_cache_size', 0))


def get_metrics_response() -> Response:
    """Generate Prometheus metrics response"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
