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

__all__ = ['health_router', 'cache_router', 'cleanup_router', 'metrics_router']
