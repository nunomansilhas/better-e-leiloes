"""
Tests for Cache System
"""

import pytest
import time
import asyncio


class TestCacheManager:
    """Tests for CacheManager class"""

    @pytest.mark.asyncio
    async def test_set_and_get_cached(self, cache_manager):
        """Test basic set and get operations"""
        await cache_manager.set_cached("test:key", {"value": 123})
        result = await cache_manager.get_cached("test:key")
        assert result == {"value": 123}

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache_manager):
        """Test that missing keys return None"""
        result = await cache_manager.get_cached("nonexistent:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_stats_tracking(self, cache_manager):
        """Test that cache stats are tracked"""
        # Initial state
        stats = cache_manager.get_cache_stats()
        initial_hits = stats["hits"]
        initial_misses = stats["misses"]

        # Cause a miss
        await cache_manager.get_cached("miss:1")

        # Cause a hit
        await cache_manager.set_cached("hit:1", {"data": True})
        await cache_manager.get_cached("hit:1")

        stats = cache_manager.get_cache_stats()
        assert stats["hits"] == initial_hits + 1
        assert stats["misses"] == initial_misses + 1

    @pytest.mark.asyncio
    async def test_cache_ttl_expiry(self, cache_manager):
        """Test that cached items expire after TTL"""
        # Set with very short TTL
        await cache_manager.set_cached("expire:test", {"data": True}, ttl=1)

        # Should exist immediately
        result = await cache_manager.get_cached("expire:test")
        assert result is not None

        # Wait for expiry
        await asyncio.sleep(1.5)

        # Should be expired
        result = await cache_manager.get_cached("expire:test")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_entries(self, cache_manager):
        """Test cleanup of expired memory cache entries"""
        # Add expired entry directly
        cache_manager.memory_cache["old:entry"] = {"data": "old"}
        cache_manager.memory_cache_ttl["old:entry"] = time.time() - 100  # Already expired

        count = await cache_manager.cleanup_expired_memory_cache()
        assert count >= 1
        assert "old:entry" not in cache_manager.memory_cache


class TestDistritosCaching:
    """Tests for distrito-specific caching"""

    @pytest.mark.asyncio
    async def test_set_and_get_distritos(self, cache_manager):
        """Test distrito list caching"""
        distritos = ["Lisboa", "Porto", "Faro", "Évora"]
        await cache_manager.set_distritos_cached(1, distritos)

        result = await cache_manager.get_distritos_cached(1)
        assert result == distritos

    @pytest.mark.asyncio
    async def test_distritos_different_tipo_ids(self, cache_manager):
        """Test that different tipo_ids have separate caches"""
        await cache_manager.set_distritos_cached(1, ["Lisboa"])
        await cache_manager.set_distritos_cached(2, ["Porto"])

        result1 = await cache_manager.get_distritos_cached(1)
        result2 = await cache_manager.get_distritos_cached(2)

        assert result1 == ["Lisboa"]
        assert result2 == ["Porto"]


class TestSubtiposCaching:
    """Tests for subtipo-specific caching"""

    @pytest.mark.asyncio
    async def test_set_and_get_subtipos(self, cache_manager):
        """Test subtipo list caching"""
        subtipos = ["Apartamento", "Moradia", "Terreno"]
        await cache_manager.set_subtipos_cached(1, subtipos)

        result = await cache_manager.get_subtipos_cached(1)
        assert result == subtipos


class TestEventsEndingCaching:
    """Tests for events ending soon caching"""

    @pytest.mark.asyncio
    async def test_set_and_get_events_ending(self, cache_manager):
        """Test events ending soon caching"""
        events = [
            {"reference": "LO-123", "titulo": "Event 1"},
            {"reference": "NP-456", "titulo": "Event 2"}
        ]
        await cache_manager.set_events_ending_cached(24, events)

        result = await cache_manager.get_events_ending_cached(24)
        assert result == events

    @pytest.mark.asyncio
    async def test_events_ending_different_hours(self, cache_manager):
        """Test that different hour windows have separate caches"""
        await cache_manager.set_events_ending_cached(12, [{"id": 1}])
        await cache_manager.set_events_ending_cached(24, [{"id": 2}])

        result12 = await cache_manager.get_events_ending_cached(12)
        result24 = await cache_manager.get_events_ending_cached(24)

        assert result12 != result24


class TestCacheInvalidation:
    """Tests for cache invalidation"""

    @pytest.mark.asyncio
    async def test_invalidate_query_cache(self, cache_manager):
        """Test invalidation of all query caches"""
        # Set multiple query caches
        await cache_manager.set_cached("query:stats", {"total": 100})
        await cache_manager.set_cached("query:other", {"data": True})
        await cache_manager.set_cached("event:123", {"title": "Test"})  # Not a query

        # Invalidate query caches
        await cache_manager.invalidate_query_cache()

        # Query caches should be gone
        assert await cache_manager.get_cached("query:stats") is None
        assert await cache_manager.get_cached("query:other") is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_manager):
        """Test pattern-based invalidation"""
        await cache_manager.set_cached("test:a", {"a": 1})
        await cache_manager.set_cached("test:b", {"b": 2})
        await cache_manager.set_cached("other:c", {"c": 3})

        await cache_manager.invalidate_pattern("test:*")

        assert await cache_manager.get_cached("test:a") is None
        assert await cache_manager.get_cached("test:b") is None


class TestCacheKeyGeneration:
    """Tests for cache key generation"""

    def test_generate_cache_key_consistent(self, cache_manager):
        """Test that same params generate same key"""
        key1 = cache_manager._generate_cache_key("prefix", a=1, b=2)
        key2 = cache_manager._generate_cache_key("prefix", a=1, b=2)
        assert key1 == key2

    def test_generate_cache_key_order_independent(self, cache_manager):
        """Test that param order doesn't affect key"""
        key1 = cache_manager._generate_cache_key("prefix", a=1, b=2)
        key2 = cache_manager._generate_cache_key("prefix", b=2, a=1)
        assert key1 == key2

    def test_generate_cache_key_different_params(self, cache_manager):
        """Test that different params generate different keys"""
        key1 = cache_manager._generate_cache_key("prefix", a=1)
        key2 = cache_manager._generate_cache_key("prefix", a=2)
        assert key1 != key2


class TestStatsCaching:
    """Tests for database stats caching"""

    @pytest.mark.asyncio
    async def test_set_and_get_stats(self, cache_manager):
        """Test database stats caching"""
        stats = {
            "total": 1000,
            "active": 500,
            "by_type": {1: 300, 2: 200}
        }
        await cache_manager.set_stats_cached(stats)

        result = await cache_manager.get_stats_cached()
        assert result == stats


class TestCacheTTLPresets:
    """Tests for TTL preset configuration"""

    def test_ttl_presets_exist(self):
        """Test that all required TTL presets are defined"""
        from cache import CACHE_TTL
        required = ["event", "stats", "events_ending", "distritos", "subtipos", "query"]
        for key in required:
            assert key in CACHE_TTL, f"Missing TTL preset: {key}"

    def test_ttl_presets_are_positive(self):
        """Test that all TTL values are positive"""
        from cache import CACHE_TTL
        for key, value in CACHE_TTL.items():
            assert value > 0, f"TTL for {key} should be positive"

    def test_events_ending_has_short_ttl(self):
        """Test that events_ending has appropriately short TTL"""
        from cache import CACHE_TTL
        assert CACHE_TTL["events_ending"] <= 120  # Max 2 minutes for real-time data
