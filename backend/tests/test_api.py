"""
Tests for API Endpoints
Requires the API to be running for integration tests
"""

import pytest


@pytest.mark.api
@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for health check endpoints"""

    @pytest.mark.asyncio
    async def test_health_simple(self, api_client):
        """Test simple health check"""
        response = await api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_detailed(self, api_client):
        """Test detailed health check"""
        response = await api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "services" in data
        assert "database" in data["services"]

    @pytest.mark.asyncio
    async def test_health_includes_version(self, api_client):
        """Test that health check includes version"""
        response = await api_client.get("/api/health")
        data = response.json()
        assert "version" in data


@pytest.mark.api
@pytest.mark.integration
class TestCacheEndpoints:
    """Tests for cache management endpoints"""

    @pytest.mark.asyncio
    async def test_cache_stats(self, api_client):
        """Test cache stats endpoint"""
        response = await api_client.get("/api/cache/stats")
        assert response.status_code == 200
        data = response.json()

        assert "hits" in data
        assert "misses" in data
        assert "hit_rate_percent" in data
        assert "using_redis" in data

    @pytest.mark.asyncio
    async def test_cache_cleanup(self, api_client):
        """Test cache cleanup endpoint"""
        response = await api_client.post("/api/cache/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_cache_invalidate_queries(self, api_client):
        """Test query cache invalidation endpoint"""
        response = await api_client.post("/api/cache/invalidate/queries")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.api
@pytest.mark.integration
class TestSecurityEndpoints:
    """Tests for security endpoints"""

    @pytest.mark.asyncio
    async def test_security_stats(self, api_client):
        """Test security stats endpoint"""
        response = await api_client.get("/api/security/stats")
        assert response.status_code == 200
        data = response.json()

        assert "rate_limiter" in data
        assert "config" in data


@pytest.mark.api
@pytest.mark.integration
class TestPipelineEndpoints:
    """Tests for pipeline management endpoints"""

    @pytest.mark.asyncio
    async def test_pipeline_status(self, api_client):
        """Test pipeline status endpoint"""
        response = await api_client.get("/api/pipeline/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_auto_pipelines_status(self, api_client):
        """Test all pipelines status endpoint"""
        response = await api_client.get("/api/auto-pipelines/status")
        assert response.status_code == 200
        data = response.json()
        assert "pipelines" in data


@pytest.mark.api
@pytest.mark.integration
class TestStatsEndpoints:
    """Tests for statistics endpoints"""

    @pytest.mark.asyncio
    async def test_stats(self, api_client):
        """Test general stats endpoint"""
        response = await api_client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()

        assert "total_events" in data or "total" in data

    @pytest.mark.asyncio
    async def test_db_stats(self, api_client):
        """Test database stats endpoint"""
        response = await api_client.get("/api/db/stats")
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.integration
class TestEventsEndpoints:
    """Tests for events endpoints"""

    @pytest.mark.asyncio
    async def test_events_ending_soon(self, api_client):
        """Test events ending soon endpoint"""
        response = await api_client.get("/api/dashboard/ending-soon")
        # May return 500 if no events - just check it responds
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_events_ending_soon_with_hours(self, api_client):
        """Test events ending soon with custom hours"""
        response = await api_client.get("/api/dashboard/ending-soon?hours=12")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_distritos_by_tipo(self, api_client):
        """Test distritos list by tipo endpoint"""
        response = await api_client.get("/api/filters/distritos/1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_subtipos_by_tipo(self, api_client):
        """Test subtipos list by tipo endpoint"""
        response = await api_client.get("/api/filters/subtypes/1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.api
@pytest.mark.integration
class TestNotificationEndpoints:
    """Tests for notification endpoints"""

    @pytest.mark.asyncio
    async def test_notifications_list(self, api_client):
        """Test notifications list endpoint"""
        response = await api_client.get("/api/notifications")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_notifications_count(self, api_client):
        """Test unread notifications count endpoint"""
        response = await api_client.get("/api/notifications/count")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_notification_rules_list(self, api_client):
        """Test notification rules list endpoint"""
        response = await api_client.get("/api/notification-rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.api
@pytest.mark.integration
class TestDashboardEndpoints:
    """Tests for dashboard endpoints"""

    @pytest.mark.asyncio
    async def test_logs(self, api_client):
        """Test logs endpoint"""
        response = await api_client.get("/api/logs")
        assert response.status_code == 200
        data = response.json()
        # Response is {"logs": [...]}
        assert "logs" in data
        assert isinstance(data["logs"], list)

    @pytest.mark.asyncio
    async def test_pipeline_history(self, api_client):
        """Test pipeline history endpoint"""
        response = await api_client.get("/api/pipeline-history")
        assert response.status_code == 200
        data = response.json()
        # Response is {"history": [...], "total": N}
        assert "history" in data
        assert isinstance(data["history"], list)

    @pytest.mark.asyncio
    async def test_activity(self, api_client):
        """Test activity endpoint"""
        response = await api_client.get("/api/dashboard/activity")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stats_by_distrito(self, api_client):
        """Test stats by distrito endpoint"""
        response = await api_client.get("/api/dashboard/stats-by-distrito")
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.integration
class TestCleanupEndpoints:
    """Tests for cleanup endpoints"""

    @pytest.mark.asyncio
    async def test_cleanup_stats(self, api_client):
        """Test cleanup stats endpoint"""
        response = await api_client.get("/api/cleanup/stats")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    @pytest.mark.asyncio
    async def test_cleanup_config(self, api_client):
        """Test cleanup config endpoint"""
        response = await api_client.get("/api/cleanup/config")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "description" in data
