"""
Pytest configuration and shared fixtures for Lumina testing
"""
import sys
import os
import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# ============================================================================
# Path Configuration
# ============================================================================

AUTOMATION_ROOT = Path(__file__).parent
PROJECT_ROOT = AUTOMATION_ROOT.parent
PYTHON_BACKEND = PROJECT_ROOT / "python_backend"

# Add to path
sys.path.insert(0, str(PYTHON_BACKEND))
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def generate_test_user_input():
    from automation.fixtures.data_generators import generate_test_user_input

    return generate_test_user_input


@pytest.fixture
def chat_message_factory():
    from automation.fixtures.factories import ChatMessageFactory

    return ChatMessageFactory


@pytest.fixture
def memory_factory():
    from automation.fixtures.factories import MemoryFactory

    return MemoryFactory


@pytest.fixture
def provider_factory():
    from automation.fixtures.factories import ProviderFactory

    return ProviderFactory


@pytest.fixture
def soul_profile_factory():
    from automation.fixtures.factories import SoulProfileFactory

    return SoulProfileFactory


@pytest.fixture
def llm_response_factory():
    from automation.fixtures.factories import LLMResponseFactory

    return LLMResponseFactory


@pytest.fixture
async def mock_http_server():
    from automation.fixtures.mock_servers import MockHTTPServer

    server = MockHTTPServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_llm_server():
    from automation.fixtures.mock_servers import MockLLMServer

    server = MockLLMServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_memory_server():
    from automation.fixtures.mock_servers import MockMemoryServer

    server = MockMemoryServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def all_mock_servers(mock_llm_server, mock_memory_server):
    return {
        "llm": mock_llm_server,
        "memory": mock_memory_server,
        "llm_url": mock_llm_server.base_url,
        "memory_url": mock_memory_server.base_url,
    }


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_container():
    """Provide a mocked ServiceContainer"""
    from services.container import ServiceContainer
    container = ServiceContainer()

    # Add common mocks
    container.set_config(MagicMock())
    container.set_event_bus(MagicMock())
    container.set_llm_manager(MagicMock())
    container.set_gateway(MagicMock())

    return container


@pytest.fixture(scope="function")
def services(mock_container):
    """Alias for mock_container for convenience"""
    return mock_container


@pytest.fixture(scope="function")
def reset_container():
    """Compatibility fixture for tests that need a clean local container."""
    yield


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Mock LLM Manager with common methods"""
    manager = MagicMock()
    manager.get_driver = AsyncMock()
    manager.get_parameters = MagicMock(return_value={
        "temperature": 0.7,
        "max_tokens": 2000
    })
    manager.get_model_name = MagicMock(return_value="test-model")
    return manager


@pytest.fixture
def mock_soul_service():
    """Mock Soul Service with profile data"""
    soul = MagicMock()
    soul.profile = {
        "personality": {"pad_model": {}},
        "state": {"energy_level": 100},
        "relationship": {"level": 0}
    }
    soul.load_character_config = MagicMock(return_value={"soul_evolution_enabled": False})
    return soul


@pytest.fixture
def mock_llm_driver():
    """Mock LLM driver with streaming response"""
    driver = AsyncMock()

    async def mock_stream():
        yield "Hello"
        yield " World"

    driver.chat_completion = AsyncMock(return_value=mock_stream())
    return driver


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def temp_db_path():
    """Provide a temporary database file path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture(scope="function")
def mock_memory_driver():
    """Mock memory database driver"""
    driver = MagicMock()
    driver._db = MagicMock()
    driver._db.query = MagicMock(return_value=[])
    driver._db.close = AsyncMock()
    return driver


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
async def async_http_client():
    """Provide async HTTP client for integration tests"""
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def service_urls():
    """Provide service endpoint URLs"""
    return {
        "core": "http://127.0.0.1:8010",
        "stt": "http://127.0.0.1:8765",
        "tts": "http://127.0.0.1:8766"
    }


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user_input():
    """Sample user input for chat tests"""
    return {
        "user_input": "Hello, how are you?",
        "user_id": "test_user_001",
        "character_id": "hiyori"
    }


@pytest.fixture
def sample_message_history():
    """Sample message history"""
    return [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "How are you?"}
    ]


@pytest.fixture
def sample_memory_data():
    """Sample memory/test data"""
    return {
        "id": "mem_001",
        "content": "Test memory content",
        "embedding": [0.1] * 512,
        "metadata": {"source": "test", "timestamp": "2024-01-20"}
    }


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set up event loop policy for Windows"""
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# ============================================================================
# Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")


@pytest.fixture(autouse=True)
def reset_singletons():
    """Keep the legacy fixture name without mutating production classes."""
    yield


# ============================================================================
# Skipif Conditions
# ============================================================================

skip_if_no_services = pytest.mark.skipif(
    True,  # Set to False when running with services
    reason="Services not running. Use 'pytest -m integration' when services are up."
)


def check_service_running(port: int) -> bool:
    """Check if a service is running on the given port"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add 'slow' marker to tests that take > 1 second (heuristic)
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.integration)

        # Add 'integration' to backend tests
        if "backend" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add 'unit' to core/services tests
        if any(x in str(item.fspath) for x in ["core", "services", "provider_drivers"]):
            item.add_marker(pytest.mark.unit)


def pytest_report_header(config):
    """Add custom header to pytest output"""
    return [
        f"Lumina Test Suite",
        f"Project Root: {PROJECT_ROOT}",
        f"Python Backend: {PYTHON_BACKEND}",
    ]
