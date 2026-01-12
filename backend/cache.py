"""
Cache Manager usando Redis (opcional) ou in-memory dict
Enhanced with query caching for frequent operations
"""

from typing import Optional, Any, Callable
import json
import os
import time
import hashlib
from functools import wraps
from models import EventData
from logger import log_info, log_warning

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Cache TTL presets (in seconds)
CACHE_TTL = {
    "event": 3600,          # 1 hour for individual events
    "stats": 300,           # 5 minutes for statistics
    "events_ending": 60,    # 1 minute for events ending soon (real-time data)
    "distritos": 3600,      # 1 hour for distrito list (rarely changes)
    "subtipos": 3600,       # 1 hour for subtipo list
    "query": 120,           # 2 minutes for general query results
}


class CacheManager:
    """
    Enhanced Cache Manager with:
    - Redis support with fallback to memory
    - Query result caching
    - TTL management
    - Cache statistics
    """

    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_cache_ttl = {}  # Store expiry times for memory cache
        self._stats = {"hits": 0, "misses": 0, "sets": 0}

        # Tenta conectar ao Redis se disponível
        if REDIS_AVAILABLE:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    self.redis_client = redis.from_url(
                        redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        socket_timeout=5,
                        socket_connect_timeout=5,
                    )
                    log_info("Redis conectado")
                except Exception as e:
                    log_warning(f"Redis não disponível, usando cache em memória: {e}")

        if not self.redis_client:
            log_info("Usando cache em memória")
    
    async def get(self, reference: str) -> Optional[EventData]:
        """Busca no cache"""
        key = f"event:{reference}"
        
        if self.redis_client:
            try:
                data = await self.redis_client.get(key)
                if data:
                    return EventData.model_validate_json(data)
            except:
                pass
        
        # Fallback para memória
        if key in self.memory_cache:
            return EventData.model_validate(self.memory_cache[key])
        
        return None
    
    async def set(self, reference: str, event: EventData, ttl: int = 3600):
        """Guarda no cache (TTL em segundos)"""
        key = f"event:{reference}"
        value = event.model_dump_json()

        if self.redis_client:
            try:
                await self.redis_client.setex(key, ttl, value)
                return
            except:
                pass

        # Fallback para memória
        self.memory_cache[key] = event.model_dump()

    async def invalidate(self, reference: str):
        """Remove um evento do cache (invalida)"""
        key = f"event:{reference}"

        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except:
                pass

        # Remove da memória também
        self.memory_cache.pop(key, None)

    async def clear_all(self):
        """Limpa todo o cache"""
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
            except:
                pass
        
        self.memory_cache.clear()
    
    async def close(self):
        """Fecha conexão Redis"""
        if self.redis_client:
            await self.redis_client.close()

    # ============== Query Caching ==============

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a unique cache key from prefix and parameters"""
        # Sort kwargs for consistent key generation
        param_str = json.dumps(kwargs, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{param_hash}"

    def _is_memory_cache_valid(self, key: str) -> bool:
        """Check if memory cache entry is still valid"""
        if key not in self.memory_cache_ttl:
            return False
        return time.time() < self.memory_cache_ttl[key]

    async def get_cached(self, key: str) -> Optional[Any]:
        """Get cached value by key (for query results)"""
        if self.redis_client:
            try:
                data = await self.redis_client.get(key)
                if data:
                    self._stats["hits"] += 1
                    return json.loads(data)
            except Exception:
                pass

        # Fallback to memory cache
        if key in self.memory_cache and self._is_memory_cache_valid(key):
            self._stats["hits"] += 1
            return self.memory_cache[key]

        self._stats["misses"] += 1
        return None

    async def set_cached(self, key: str, value: Any, ttl: int = None):
        """Set cached value with TTL"""
        ttl = ttl or CACHE_TTL["query"]
        self._stats["sets"] += 1

        if self.redis_client:
            try:
                await self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass

        # Fallback to memory cache
        self.memory_cache[key] = value
        self.memory_cache_ttl[key] = time.time() + ttl

    async def get_stats_cached(self) -> Optional[dict]:
        """Get cached database stats"""
        return await self.get_cached("query:stats")

    async def set_stats_cached(self, stats: dict):
        """Cache database stats"""
        await self.set_cached("query:stats", stats, CACHE_TTL["stats"])

    async def get_events_ending_cached(self, hours: int) -> Optional[list]:
        """Get cached events ending soon"""
        key = f"query:events_ending:{hours}"
        return await self.get_cached(key)

    async def set_events_ending_cached(self, hours: int, events: list):
        """Cache events ending soon"""
        key = f"query:events_ending:{hours}"
        await self.set_cached(key, events, CACHE_TTL["events_ending"])

    async def get_distritos_cached(self, tipo_id: int) -> Optional[list]:
        """Get cached distritos list"""
        key = f"query:distritos:{tipo_id}"
        return await self.get_cached(key)

    async def set_distritos_cached(self, tipo_id: int, distritos: list):
        """Cache distritos list"""
        key = f"query:distritos:{tipo_id}"
        await self.set_cached(key, distritos, CACHE_TTL["distritos"])

    async def get_subtipos_cached(self, tipo_id: int) -> Optional[list]:
        """Get cached subtipos list"""
        key = f"query:subtipos:{tipo_id}"
        return await self.get_cached(key)

    async def set_subtipos_cached(self, tipo_id: int, subtipos: list):
        """Cache subtipos list"""
        key = f"query:subtipos:{tipo_id}"
        await self.set_cached(key, subtipos, CACHE_TTL["subtipos"])

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all cache keys matching pattern"""
        if self.redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            except Exception:
                pass

        # Memory cache - remove matching keys
        keys_to_remove = [k for k in self.memory_cache.keys() if pattern.replace("*", "") in k]
        for key in keys_to_remove:
            self.memory_cache.pop(key, None)
            self.memory_cache_ttl.pop(key, None)

    async def invalidate_query_cache(self):
        """Invalidate all query caches (after data changes)"""
        await self.invalidate_pattern("query:*")

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "using_redis": self.redis_client is not None
        }

    async def cleanup_expired_memory_cache(self):
        """Clean up expired entries from memory cache"""
        now = time.time()
        expired_keys = [k for k, exp in self.memory_cache_ttl.items() if exp < now]
        for key in expired_keys:
            self.memory_cache.pop(key, None)
            self.memory_cache_ttl.pop(key, None)
        return len(expired_keys)
