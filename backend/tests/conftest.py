"""
Pytest Configuration and Fixtures
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator

# Load environment before importing app modules
from dotenv import load_dotenv
load_dotenv()


# ============== Event Loop ==============

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============== Database Fixtures ==============

@pytest.fixture(scope="session")
async def db_engine():
    """Database engine for testing"""
    from database import engine
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session():
    """Database session for each test"""
    from database import async_session_maker, DatabaseManager
    async with async_session_maker() as session:
        yield DatabaseManager(session)


# ============== Cache Fixtures ==============

@pytest.fixture
def cache_manager():
    """Fresh cache manager for each test"""
    from cache import CacheManager
    cache = CacheManager()
    yield cache


@pytest.fixture
async def clean_cache(cache_manager):
    """Cache manager with clean state"""
    await cache_manager.clear_all()
    yield cache_manager
    await cache_manager.clear_all()


# ============== API Client Fixtures ==============

@pytest.fixture
async def api_client():
    """Async HTTP client for API testing"""
    import httpx
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10) as client:
        yield client


@pytest.fixture
def test_event_data():
    """Sample event data for testing"""
    return {
        "reference": "TEST-123456",
        "titulo": "Test Event",
        "tipo_id": 1,
        "tipo": "Imóvel",
        "subtipo": "Apartamento",
        "distrito": "Lisboa",
        "concelho": "Lisboa",
        "lance_atual": 50000.00,
        "valor_base": 75000.00,
        "cancelado": False,
        "terminado": False
    }


@pytest.fixture
def test_notification_rule():
    """Sample notification rule for testing"""
    return {
        "name": "Test Rule",
        "rule_type": "price_change",
        "active": True,
        "tipos": [1],
        "distritos": ["Lisboa"],
        "preco_min": 10000,
        "preco_max": 100000
    }


# ============== Markers ==============

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "api: marks tests that require running API")
