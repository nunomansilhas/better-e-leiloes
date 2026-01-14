"""
API Response Schemas
Pydantic models for API responses (used in OpenAPI documentation)
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============== Generic Responses ==============

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional data payload")

    model_config = {"json_schema_extra": {"example": {"success": True, "message": "Operation completed"}}}


class ErrorDetail(BaseModel):
    """Error detail structure"""
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: ErrorDetail


# ============== Health Responses ==============

class ServiceStatus(BaseModel):
    """Individual service status"""
    status: str = Field(..., description="Service status (ok, error, disabled)")
    error: Optional[str] = Field(None, description="Error message if status is error")
    note: Optional[str] = Field(None, description="Additional information")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    timestamp: str = Field(..., description="ISO timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, ServiceStatus] = Field(..., description="Service statuses")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00",
                "version": "2.0.0",
                "services": {
                    "database": {"status": "ok", "type": "mysql"},
                    "redis": {"status": "disabled", "note": "Using memory cache"},
                    "pipelines": {"status": "ok", "active": 2, "total": 3}
                }
            }
        }
    }


# ============== Cache Responses ==============

class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    hits: int = Field(..., description="Number of cache hits")
    misses: int = Field(..., description="Number of cache misses")
    sets: int = Field(..., description="Number of cache sets")
    hit_rate_percent: float = Field(..., description="Cache hit rate percentage")
    memory_cache_size: int = Field(..., description="Number of items in memory cache")
    using_redis: bool = Field(..., description="Whether Redis is being used")

    model_config = {
        "json_schema_extra": {
            "example": {
                "hits": 150,
                "misses": 30,
                "sets": 50,
                "hit_rate_percent": 83.33,
                "memory_cache_size": 25,
                "using_redis": False
            }
        }
    }


# ============== Cleanup Responses ==============

class CleanupStatsResponse(BaseModel):
    """Cleanup statistics response"""
    old_notifications: int = Field(..., description="Notifications older than retention period")
    old_price_history: int = Field(..., description="Price history older than retention period")
    old_refresh_logs: int = Field(..., description="Refresh logs older than retention period")
    old_terminated_events: int = Field(..., description="Terminated events that can be marked inactive")
    total_cleanable: int = Field(..., description="Total records that can be cleaned")
    config: Dict[str, int] = Field(..., description="Current cleanup configuration")


class CleanupResultResponse(BaseModel):
    """Cleanup operation result"""
    notifications: int = Field(..., description="Deleted notifications")
    price_history: int = Field(..., description="Deleted price history records")
    refresh_logs: int = Field(..., description="Deleted refresh logs")
    inactive_events: int = Field(..., description="Events marked inactive")
    timestamp: str = Field(..., description="Cleanup timestamp")


# ============== Event Responses ==============

class EventSummary(BaseModel):
    """Event summary for lists"""
    reference: str = Field(..., description="Event reference (e.g., LO-123456)")
    titulo: str = Field(None, description="Event title")
    tipo_id: int = Field(None, description="Type ID (1=Imóveis, 2=Veículos, etc.)")
    tipo: str = Field(None, description="Type name")
    subtipo: str = Field(None, description="Subtype name")
    distrito: str = Field(None, description="District")
    lance_atual: float = Field(0, description="Current bid value")
    valor_base: float = Field(None, description="Base value")
    data_fim: str = Field(None, description="End date (ISO format)")
    terminado: bool = Field(False, description="Whether event has ended")

    model_config = {
        "json_schema_extra": {
            "example": {
                "reference": "LO-123456",
                "titulo": "Apartamento T2 em Lisboa",
                "tipo_id": 1,
                "tipo": "Imóvel",
                "subtipo": "Apartamento",
                "distrito": "Lisboa",
                "lance_atual": 125000.00,
                "valor_base": 100000.00,
                "data_fim": "2024-01-20T15:00:00",
                "terminado": False
            }
        }
    }


class EventsEndingSoonResponse(BaseModel):
    """Events ending soon response"""
    events: List[EventSummary] = Field(..., description="List of events")
    count: int = Field(..., description="Total count")
    hours: int = Field(..., description="Time window in hours")


# ============== Pipeline Responses ==============

class PipelineStatus(BaseModel):
    """Individual pipeline status"""
    name: str = Field(..., description="Pipeline name")
    enabled: bool = Field(..., description="Whether pipeline is enabled")
    is_running: bool = Field(..., description="Whether pipeline is currently running")
    interval_hours: float = Field(..., description="Interval between runs")
    last_run: Optional[str] = Field(None, description="Last run timestamp")
    next_run: Optional[str] = Field(None, description="Next scheduled run")
    runs_count: int = Field(0, description="Total number of runs")


class PipelinesStatusResponse(BaseModel):
    """All pipelines status response"""
    pipelines: Dict[str, PipelineStatus] = Field(..., description="Pipeline statuses")
    scheduler_running: bool = Field(..., description="Whether scheduler is active")


# ============== Notification Responses ==============

class NotificationResponse(BaseModel):
    """Notification response"""
    id: int
    notification_type: str = Field(..., description="Type (new_event, price_change, ending_soon)")
    event_reference: str
    event_titulo: Optional[str]
    preco_anterior: Optional[float]
    preco_atual: Optional[float]
    preco_variacao: Optional[float]
    read: bool
    created_at: str


class NotificationRuleResponse(BaseModel):
    """Notification rule response"""
    id: int
    name: str
    rule_type: str
    active: bool
    tipos: Optional[List[int]]
    distritos: Optional[List[str]]
    preco_min: Optional[float]
    preco_max: Optional[float]
    triggers_count: int
    created_at: str


# ============== Statistics Responses ==============

class StatsResponse(BaseModel):
    """General statistics response"""
    total: int = Field(..., description="Total events")
    ativos: int = Field(..., description="Active events")
    inativos: int = Field(..., description="Inactive events")
    with_content: int = Field(..., description="Events with content")
    with_images: int = Field(..., description="Events with images")
    cancelados: int = Field(..., description="Cancelled events")
    by_type: Dict[int, int] = Field(..., description="Events by type ID")


class RecentActivityResponse(BaseModel):
    """Recent activity response"""
    new_events: int = Field(..., description="New events in last 24h")
    ended_events: int = Field(..., description="Ended events in last 24h")
    notifications: int = Field(..., description="Notifications in last 24h")
    price_updates: int = Field(..., description="Price updates in last 24h")
