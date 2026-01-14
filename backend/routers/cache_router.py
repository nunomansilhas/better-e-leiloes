"""
Cache Management Router
Endpoints for cache monitoring and control
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/cache", tags=["Cache"])


@router.get("/stats")
async def get_cache_stats():
    """
    Get cache statistics.

    Returns:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - hit_rate_percent: Cache hit rate percentage
    - memory_cache_size: Number of items in memory cache
    - using_redis: Whether Redis is being used
    """
    # Import here to avoid circular imports
    from main import cache_manager

    if cache_manager:
        return cache_manager.get_cache_stats()

    return {
        "error": "Cache manager not initialized",
        "hits": 0,
        "misses": 0,
        "hit_rate_percent": 0,
        "memory_cache_size": 0,
        "using_redis": False
    }


@router.post("/clear")
async def clear_cache():
    """
    Clear all cache entries.
    Use with caution - will impact performance temporarily.
    """
    from main import cache_manager

    if cache_manager:
        await cache_manager.clear_all()
        return {"success": True, "message": "Cache cleared successfully"}

    return {"success": False, "message": "Cache manager not initialized"}


@router.post("/invalidate/queries")
async def invalidate_query_cache():
    """
    Invalidate query cache only.
    Useful after bulk data operations.
    """
    from main import cache_manager

    if cache_manager:
        await cache_manager.invalidate_query_cache()
        return {"success": True, "message": "Query cache invalidated"}

    return {"success": False, "message": "Cache manager not initialized"}


@router.post("/cleanup")
async def cleanup_expired_cache():
    """
    Clean up expired entries from memory cache.
    Only affects memory cache, Redis handles expiry automatically.
    """
    from main import cache_manager

    if cache_manager:
        count = await cache_manager.cleanup_expired_memory_cache()
        return {
            "success": True,
            "message": f"Cleaned up {count} expired entries"
        }

    return {"success": False, "message": "Cache manager not initialized"}
