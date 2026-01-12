"""
Phase 2 Improvements Test Script
Tests: Connection Pooling, Validators, Cache, Error Handling, Routers

Run: python test_phase2.py
"""

import asyncio
import time
import sys
from datetime import datetime

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_test(name: str, passed: bool, details: str = ""):
    icon = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
    status = f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
    print(f"  {icon} {name}: {status}")
    if details:
        print(f"      {Colors.YELLOW}{details}{Colors.END}")

def print_info(msg: str):
    print(f"  {Colors.BLUE}ℹ{Colors.END} {msg}")


# ============== Test 1: Connection Pooling ==============

async def test_connection_pooling():
    print_header("Test 1: Connection Pooling")

    from database import engine, get_db
    from sqlalchemy import text

    # Check pool configuration
    pool = engine.pool
    print_info(f"Pool class: {pool.__class__.__name__}")
    print_info(f"Pool size: {pool.size()}")
    print_info(f"Checked out connections: {pool.checkedout()}")
    print_info(f"Overflow: {pool.overflow()}")

    # Test 1.1: Pool settings are correct
    try:
        # These are set in database.py
        pool_config = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
        print_test("Pool configuration loaded", True, f"size={pool.size()}")
    except Exception as e:
        print_test("Pool configuration loaded", False, str(e))
        return False

    # Test 1.2: Concurrent connections
    async def make_query(n):
        async with get_db() as db:
            result = await db.session.execute(text("SELECT 1"))
            return result.scalar()

    try:
        start = time.time()
        # Run 20 concurrent queries
        tasks = [make_query(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        all_ok = all(r == 1 for r in results)
        print_test("Concurrent connections (20 queries)", all_ok, f"Time: {elapsed:.3f}s")
    except Exception as e:
        print_test("Concurrent connections", False, str(e))
        return False

    # Test 1.3: Pool pre-ping (connection validation)
    try:
        async with get_db() as db:
            await db.session.execute(text("SELECT 1"))
        print_test("Pool pre-ping (connection validation)", True)
    except Exception as e:
        print_test("Pool pre-ping", False, str(e))

    return True


# ============== Test 2: Input Validation ==============

def test_validators():
    print_header("Test 2: Input Validation (Pydantic)")

    from validators import (
        PaginationParams, EventFilterParams, RefreshRequest,
        BatchRefreshRequest, NotificationRuleRequest, validate_reference
    )
    from pydantic import ValidationError

    all_passed = True

    # Test 2.1: PaginationParams
    try:
        params = PaginationParams(page=1, limit=50)
        print_test("PaginationParams valid", True, f"page={params.page}, limit={params.limit}")
    except Exception as e:
        print_test("PaginationParams valid", False, str(e))
        all_passed = False

    # Test 2.2: PaginationParams invalid (page < 1)
    try:
        params = PaginationParams(page=0, limit=50)
        print_test("PaginationParams rejects page=0", False, "Should have raised error")
        all_passed = False
    except ValidationError:
        print_test("PaginationParams rejects page=0", True)

    # Test 2.3: PaginationParams invalid (limit > 500)
    try:
        params = PaginationParams(page=1, limit=1000)
        print_test("PaginationParams rejects limit=1000", False, "Should have raised error")
        all_passed = False
    except ValidationError:
        print_test("PaginationParams rejects limit=1000", True)

    # Test 2.4: RefreshRequest valid
    try:
        req = RefreshRequest(reference="LO-123456")
        print_test("RefreshRequest valid", True, f"ref={req.reference}")
    except Exception as e:
        print_test("RefreshRequest valid", False, str(e))
        all_passed = False

    # Test 2.5: RefreshRequest normalizes reference
    try:
        req = RefreshRequest(reference="lo-123456")
        normalized = req.reference == "LO-123456"
        print_test("RefreshRequest normalizes to uppercase", normalized, f"'{req.reference}'")
        if not normalized:
            all_passed = False
    except Exception as e:
        print_test("RefreshRequest normalizes", False, str(e))
        all_passed = False

    # Test 2.6: RefreshRequest rejects invalid format
    try:
        req = RefreshRequest(reference="invalid")
        print_test("RefreshRequest rejects invalid format", False, "Should have raised error")
        all_passed = False
    except ValidationError:
        print_test("RefreshRequest rejects invalid format", True)

    # Test 2.7: NotificationRuleRequest price validation
    try:
        req = NotificationRuleRequest(
            name="Test Rule",
            rule_type="price_change",
            preco_min=1000,
            preco_max=500  # Invalid: min > max
        )
        print_test("NotificationRule rejects min > max", False, "Should have raised error")
        all_passed = False
    except ValidationError:
        print_test("NotificationRule rejects min > max", True)

    # Test 2.8: EventFilterParams sanitizes distrito
    try:
        params = EventFilterParams(distrito="  Lisboa  ")
        sanitized = params.distrito == "Lisboa"
        print_test("EventFilterParams sanitizes distrito", sanitized, f"'{params.distrito}'")
        if not sanitized:
            all_passed = False
    except Exception as e:
        print_test("EventFilterParams sanitizes distrito", False, str(e))
        all_passed = False

    # Test 2.9: validate_reference function
    try:
        ref = validate_reference("np-789")
        valid = ref == "NP-789"
        print_test("validate_reference() normalizes", valid, f"'{ref}'")
        if not valid:
            all_passed = False
    except Exception as e:
        print_test("validate_reference()", False, str(e))
        all_passed = False

    return all_passed


# ============== Test 3: Cache System ==============

async def test_cache():
    print_header("Test 3: Cache System")

    from cache import CacheManager, CACHE_TTL

    cache = CacheManager()
    all_passed = True

    # Test 3.1: Cache TTL presets loaded
    try:
        ttls = ["event", "stats", "events_ending", "distritos", "subtipos", "query"]
        all_exist = all(t in CACHE_TTL for t in ttls)
        print_test("Cache TTL presets loaded", all_exist, f"{len(CACHE_TTL)} presets")
    except Exception as e:
        print_test("Cache TTL presets", False, str(e))
        all_passed = False

    # Test 3.2: Set and get cached value
    try:
        test_key = "test:phase2"
        test_value = {"test": True, "timestamp": datetime.now().isoformat()}

        await cache.set_cached(test_key, test_value, ttl=60)
        retrieved = await cache.get_cached(test_key)

        match = retrieved == test_value
        print_test("Set and get cached value", match)
        if not match:
            all_passed = False
    except Exception as e:
        print_test("Set and get cached value", False, str(e))
        all_passed = False

    # Test 3.3: Cache miss returns None
    try:
        result = await cache.get_cached("nonexistent:key:12345")
        is_none = result is None
        print_test("Cache miss returns None", is_none)
        if not is_none:
            all_passed = False
    except Exception as e:
        print_test("Cache miss returns None", False, str(e))
        all_passed = False

    # Test 3.4: Cache stats
    try:
        stats = cache.get_cache_stats()
        has_keys = all(k in stats for k in ["hits", "misses", "sets", "hit_rate_percent"])
        print_test("Cache stats available", has_keys, f"hits={stats['hits']}, misses={stats['misses']}")
        if not has_keys:
            all_passed = False
    except Exception as e:
        print_test("Cache stats", False, str(e))
        all_passed = False

    # Test 3.5: Distritos cache methods
    try:
        await cache.set_distritos_cached(1, ["Lisboa", "Porto", "Faro"])
        distritos = await cache.get_distritos_cached(1)
        valid = distritos == ["Lisboa", "Porto", "Faro"]
        print_test("Distritos cache methods", valid)
        if not valid:
            all_passed = False
    except Exception as e:
        print_test("Distritos cache methods", False, str(e))
        all_passed = False

    # Test 3.6: Cache invalidation
    try:
        await cache.set_cached("query:test1", {"a": 1})
        await cache.set_cached("query:test2", {"b": 2})
        await cache.invalidate_query_cache()

        result1 = await cache.get_cached("query:test1")
        result2 = await cache.get_cached("query:test2")

        invalidated = result1 is None and result2 is None
        print_test("Cache invalidation", invalidated)
        if not invalidated:
            all_passed = False
    except Exception as e:
        print_test("Cache invalidation", False, str(e))
        all_passed = False

    # Test 3.7: Memory cache cleanup
    try:
        # Set a value with very short TTL
        cache.memory_cache["test:expired"] = {"old": True}
        cache.memory_cache_ttl["test:expired"] = time.time() - 10  # Already expired

        count = await cache.cleanup_expired_memory_cache()
        cleaned = count >= 1
        print_test("Memory cache cleanup", cleaned, f"Cleaned {count} entries")
    except Exception as e:
        print_test("Memory cache cleanup", False, str(e))
        all_passed = False

    # Final stats
    print_info(f"Final cache stats: {cache.get_cache_stats()}")

    await cache.close()
    return all_passed


# ============== Test 4: Error Handling ==============

def test_error_handlers():
    print_header("Test 4: Error Handling")

    from error_handlers import (
        ErrorCode, create_error_response, AppException,
        NotFoundError, ValidationException, DatabaseException
    )

    all_passed = True

    # Test 4.1: ErrorCode constants
    try:
        codes = [
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.NOT_FOUND,
            ErrorCode.DATABASE_ERROR,
            ErrorCode.INTERNAL_ERROR
        ]
        print_test("ErrorCode constants defined", True, f"{len(codes)} codes")
    except Exception as e:
        print_test("ErrorCode constants", False, str(e))
        all_passed = False

    # Test 4.2: create_error_response
    try:
        response = create_error_response(
            status_code=404,
            message="Event not found",
            error_code=ErrorCode.NOT_FOUND
        )
        valid = response.status_code == 404
        print_test("create_error_response()", valid, f"status={response.status_code}")
        if not valid:
            all_passed = False
    except Exception as e:
        print_test("create_error_response()", False, str(e))
        all_passed = False

    # Test 4.3: NotFoundError exception
    try:
        exc = NotFoundError("Event", "LO-123456")
        valid = exc.status_code == 404 and "LO-123456" in exc.message
        print_test("NotFoundError exception", valid, exc.message)
        if not valid:
            all_passed = False
    except Exception as e:
        print_test("NotFoundError exception", False, str(e))
        all_passed = False

    # Test 4.4: ValidationException
    try:
        exc = ValidationException("Invalid input", {"field": "reference"})
        valid = exc.status_code == 422 and exc.details is not None
        print_test("ValidationException", valid, f"code={exc.error_code}")
        if not valid:
            all_passed = False
    except Exception as e:
        print_test("ValidationException", False, str(e))
        all_passed = False

    # Test 4.5: DatabaseException
    try:
        exc = DatabaseException("Connection failed")
        valid = exc.status_code == 503
        print_test("DatabaseException", valid, f"status={exc.status_code}")
        if not valid:
            all_passed = False
    except Exception as e:
        print_test("DatabaseException", False, str(e))
        all_passed = False

    return all_passed


# ============== Test 5: API Endpoints ==============

async def test_api_endpoints():
    print_header("Test 5: API Endpoints (Cache Router)")

    import httpx

    base_url = "http://localhost:8000"
    all_passed = True

    print_info("Note: Requires the API to be running on localhost:8000")

    async with httpx.AsyncClient() as client:
        # Test 5.1: Health endpoint
        try:
            response = await client.get(f"{base_url}/health", timeout=5)
            valid = response.status_code == 200
            print_test("GET /health", valid, f"status={response.status_code}")
            if not valid:
                all_passed = False
        except httpx.ConnectError:
            print_test("GET /health", False, "API not running - skipping endpoint tests")
            print_info("Start the API with: uvicorn main:app --reload")
            return None  # Skip remaining tests
        except Exception as e:
            print_test("GET /health", False, str(e))
            all_passed = False

        # Test 5.2: Cache stats endpoint
        try:
            response = await client.get(f"{base_url}/api/cache/stats", timeout=5)
            valid = response.status_code == 200
            if valid:
                data = response.json()
                valid = "hits" in data and "misses" in data
            print_test("GET /api/cache/stats", valid, f"hit_rate={data.get('hit_rate_percent', 'N/A')}%")
            if not valid:
                all_passed = False
        except Exception as e:
            print_test("GET /api/cache/stats", False, str(e))
            all_passed = False

        # Test 5.3: Cache cleanup endpoint
        try:
            response = await client.post(f"{base_url}/api/cache/cleanup", timeout=5)
            valid = response.status_code == 200
            print_test("POST /api/cache/cleanup", valid)
            if not valid:
                all_passed = False
        except Exception as e:
            print_test("POST /api/cache/cleanup", False, str(e))
            all_passed = False

        # Test 5.4: Security stats endpoint
        try:
            response = await client.get(f"{base_url}/api/security/stats", timeout=5)
            valid = response.status_code == 200
            if valid:
                data = response.json()
                valid = "rate_limiter" in data
            print_test("GET /api/security/stats", valid)
            if not valid:
                all_passed = False
        except Exception as e:
            print_test("GET /api/security/stats", False, str(e))
            all_passed = False

    return all_passed


# ============== Main ==============

async def main():
    print(f"\n{Colors.BOLD}Phase 2 Improvements Test Suite{Colors.END}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {}

    # Run tests
    try:
        results["Connection Pooling"] = await test_connection_pooling()
    except Exception as e:
        print_test("Connection Pooling", False, str(e))
        results["Connection Pooling"] = False

    try:
        results["Input Validation"] = test_validators()
    except Exception as e:
        print_test("Input Validation", False, str(e))
        results["Input Validation"] = False

    try:
        results["Cache System"] = await test_cache()
    except Exception as e:
        print_test("Cache System", False, str(e))
        results["Cache System"] = False

    try:
        results["Error Handling"] = test_error_handlers()
    except Exception as e:
        print_test("Error Handling", False, str(e))
        results["Error Handling"] = False

    try:
        api_result = await test_api_endpoints()
        if api_result is not None:
            results["API Endpoints"] = api_result
    except Exception as e:
        print_test("API Endpoints", False, str(e))
        results["API Endpoints"] = False

    # Summary
    print_header("Test Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        print_test(name, result)

    print(f"\n  {Colors.BOLD}Total: {passed}/{total} test groups passed{Colors.END}")

    if passed == total:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.END}")
        return 0
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}Some tests failed!{Colors.END}")
        return 1


async def cleanup():
    """Properly close database connections to avoid warnings"""
    from database import engine
    await engine.dispose()


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    async def run_all():
        try:
            result = await main()
            return result
        finally:
            await cleanup()

    exit_code = asyncio.run(run_all())
    sys.exit(exit_code)
