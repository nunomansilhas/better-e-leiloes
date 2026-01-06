"""
Cache Manager usando Redis (opcional) ou in-memory dict
"""

from typing import Optional
import json
import os
from models import EventData

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """Gerenciador de cache para eventos"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        
        # Tenta conectar ao Redis se disponível
        if REDIS_AVAILABLE:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    self.redis_client = redis.from_url(redis_url)
                    print("✅ Redis conectado")
                except Exception as e:
                    print(f"⚠️ Redis não disponível, usando cache em memória: {e}")
        
        if not self.redis_client:
            print("ℹ️ Usando cache em memória")
    
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
