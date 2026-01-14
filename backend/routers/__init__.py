"""
API Routers Package
Modular organization of API endpoints
"""

from fastapi import APIRouter

# Re-export routers for easy import
from .health import router as health_router
from .cache_router import router as cache_router
from .cleanup_router import router as cleanup_router
from .metrics_router import router as metrics_router
from .ai_tips_router import router as ai_tips_router
from .vehicle_router import router as vehicle_router

__all__ = ['health_router', 'cache_router', 'cleanup_router', 'metrics_router', 'ai_tips_router', 'vehicle_router']
