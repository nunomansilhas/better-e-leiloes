"""
Tests for Prometheus Metrics Module
"""

import pytest


class TestMetricsModule:
    """Tests for metrics module components"""

    def test_app_info_defined(self):
        """Test that app info metric is defined"""
        from metrics import APP_INFO
        assert APP_INFO is not None

    def test_request_counter_defined(self):
        """Test that request counter is defined"""
        from metrics import REQUEST_COUNT
        assert REQUEST_COUNT is not None

    def test_request_latency_defined(self):
        """Test that request latency histogram is defined"""
        from metrics import REQUEST_LATENCY
        assert REQUEST_LATENCY is not None

    def test_cache_metrics_defined(self):
        """Test that cache metrics are defined"""
        from metrics import CACHE_HITS, CACHE_MISSES, CACHE_SIZE
        assert CACHE_HITS is not None
        assert CACHE_MISSES is not None
        assert CACHE_SIZE is not None

    def test_pipeline_metrics_defined(self):
        """Test that pipeline metrics are defined"""
        from metrics import PIPELINE_RUNS, PIPELINE_DURATION, PIPELINE_RUNNING
        assert PIPELINE_RUNS is not None
        assert PIPELINE_DURATION is not None
        assert PIPELINE_RUNNING is not None

    def test_events_metrics_defined(self):
        """Test that events metrics are defined"""
        from metrics import EVENTS_TOTAL, EVENTS_BY_TYPE, EVENTS_BY_DISTRITO
        assert EVENTS_TOTAL is not None
        assert EVENTS_BY_TYPE is not None
        assert EVENTS_BY_DISTRITO is not None

    def test_db_metrics_defined(self):
        """Test that database metrics are defined"""
        from metrics import DB_QUERY_COUNT, DB_QUERY_LATENCY, DB_CONNECTION_POOL
        assert DB_QUERY_COUNT is not None
        assert DB_QUERY_LATENCY is not None
        assert DB_CONNECTION_POOL is not None


class TestMetricsResponse:
    """Tests for metrics response generation"""

    def test_get_metrics_response(self):
        """Test that metrics response is generated correctly"""
        from metrics import get_metrics_response
        response = get_metrics_response()

        assert response is not None
        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"
        assert response.body is not None

    def test_metrics_response_contains_app_info(self):
        """Test that metrics response contains app info"""
        from metrics import get_metrics_response
        response = get_metrics_response()
        content = response.body.decode()

        assert "eleiloes_app_info" in content

    def test_metrics_response_contains_counters(self):
        """Test that metrics response contains counter metrics"""
        from metrics import get_metrics_response
        response = get_metrics_response()
        content = response.body.decode()

        # These should be defined even if not incremented
        assert "eleiloes_http_requests" in content or "# HELP" in content


class TestDBQueryTracker:
    """Tests for database query tracking"""

    def test_track_db_query_context_manager(self):
        """Test that db query tracker works as context manager"""
        from metrics import track_db_query

        tracker = track_db_query("select")
        assert hasattr(tracker, '__enter__')
        assert hasattr(tracker, '__exit__')

    def test_track_db_query_measures_time(self):
        """Test that db query tracker measures time"""
        from metrics import track_db_query, DB_QUERY_COUNT
        import time

        initial_count = DB_QUERY_COUNT.labels(operation="test")._value.get()

        with track_db_query("test"):
            time.sleep(0.01)

        # Counter should have incremented
        new_count = DB_QUERY_COUNT.labels(operation="test")._value.get()
        assert new_count > initial_count


class TestCacheMetricsTracking:
    """Tests for cache metrics updates"""

    def test_update_cache_metrics(self):
        """Test cache metrics update function"""
        from metrics import update_cache_metrics, CACHE_SIZE
        from cache import CacheManager

        cache = CacheManager()
        # Add some items to cache
        cache.memory_cache["test1"] = "value1"
        cache.memory_cache["test2"] = "value2"

        update_cache_metrics(cache)

        # Cache size should reflect the items
        assert CACHE_SIZE._value.get() >= 2


@pytest.mark.api
@pytest.mark.integration
class TestMetricsEndpoints:
    """Tests for metrics API endpoints"""

    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self, api_client):
        """Test /metrics endpoint returns Prometheus format"""
        response = await api_client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        content = response.text
        assert "# HELP" in content or "eleiloes" in content

    @pytest.mark.asyncio
    async def test_metrics_summary_endpoint(self, api_client):
        """Test /api/metrics/summary endpoint"""
        response = await api_client.get("/api/metrics/summary")
        assert response.status_code == 200

        data = response.json()
        assert "database" in data
        assert "cache" in data
        assert "pipelines" in data

    @pytest.mark.asyncio
    async def test_metrics_update_endpoint(self, api_client):
        """Test /api/metrics/update endpoint"""
        response = await api_client.post("/api/metrics/update")
        assert response.status_code == 200

        data = response.json()
        assert data.get("success") is True


class TestMetricsLabels:
    """Tests for metrics labels"""

    def test_request_count_labels(self):
        """Test that request count has correct labels"""
        from metrics import REQUEST_COUNT

        # Should be able to create labels
        labeled = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200")
        assert labeled is not None

    def test_pipeline_runs_labels(self):
        """Test that pipeline runs has correct labels"""
        from metrics import PIPELINE_RUNS

        labeled = PIPELINE_RUNS.labels(pipeline_type="x_monitor", status="success")
        assert labeled is not None

    def test_events_by_type_labels(self):
        """Test that events by type has correct labels"""
        from metrics import EVENTS_BY_TYPE

        labeled = EVENTS_BY_TYPE.labels(tipo_id="1", tipo_name="Imoveis")
        assert labeled is not None


class TestMetricsIncrement:
    """Tests for metrics increment operations"""

    def test_cache_hit_increment(self):
        """Test cache hit counter increment"""
        from metrics import CACHE_HITS

        initial = CACHE_HITS._value.get()
        CACHE_HITS.inc()
        assert CACHE_HITS._value.get() == initial + 1

    def test_cache_miss_increment(self):
        """Test cache miss counter increment"""
        from metrics import CACHE_MISSES

        initial = CACHE_MISSES._value.get()
        CACHE_MISSES.inc()
        assert CACHE_MISSES._value.get() == initial + 1

    def test_rate_limit_hits_increment(self):
        """Test rate limit hits counter increment"""
        from metrics import RATE_LIMIT_HITS

        initial = RATE_LIMIT_HITS._value.get()
        RATE_LIMIT_HITS.inc()
        assert RATE_LIMIT_HITS._value.get() == initial + 1
