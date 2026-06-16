"""
Tests demonstrating pytest fixture usage

Shows how to use fixtures for cleaner, more reusable test code.
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


# ============================================================================
# Using Fixtures from conftest.py
# ============================================================================

def test_using_container_fixture(mock_container):
    """Fixture is automatically injected - no setup needed!"""
    # mock_container comes from conftest.py
    assert mock_container is not None

    # Use it directly
    mock_config = MagicMock()
    mock_container.set_config(mock_config)
    assert mock_container.get_config() is mock_config


def test_using_multiple_fixtures(mock_container, mock_llm_manager):
    """Multiple fixtures can be combined"""
    mock_container._llm_manager = mock_llm_manager

    params = mock_llm_manager.get_parameters()
    assert "temperature" in params


def test_using_factory_fixture(chat_message_factory):
    """Factory fixtures create test data on demand"""
    # Create a single message
    msg = chat_message_factory.create(role="user", content="Hello")
    assert msg["role"] == "user"
    assert msg["content"] == "Hello"

    # Create a conversation
    conv = chat_message_factory.create_conversation(count=5)
    assert len(conv) == 5


# ============================================================================
# Fixture Scope - session vs function vs module
# ============================================================================

@pytest.fixture(scope="function")
def function_scoped_data():
    """Created fresh for each test"""
    return {"counter": 0}


@pytest.fixture(scope="module")
def module_scoped_data():
    """Shared across tests in this module"""
    return {"shared": "value"}


def test_function_scope_1(function_scoped_data):
    """Each test gets a fresh copy"""
    function_scoped_data["counter"] = 1
    assert function_scoped_data["counter"] == 1


def test_function_scope_2(function_scoped_data):
    """This test gets a new instance - counter is back to 0"""
    assert function_scoped_data["counter"] == 0
    function_scoped_data["counter"] = 2


def test_module_scope(module_scoped_data):
    """Uses shared data"""
    assert module_scoped_data["shared"] == "value"


# ============================================================================
# Fixture Yield for Cleanup
# ============================================================================

@pytest.fixture
def temp_resource():
    """Fixture with setup and cleanup"""
    # Setup
    resource = {"data": "test", "active": True}
    yield resource
    # Cleanup (runs after test)
    resource["active"] = False


def test_with_cleanup(temp_resource):
    """Test uses the resource"""
    assert temp_resource["active"] is True
    # After test, fixture cleanup runs automatically


# ============================================================================
# Parametrized Fixtures
# ============================================================================

@pytest.fixture(params=["openai", "anthropic", "ollama"])
def llm_provider(request):
    """Fixture that runs test for each provider"""
    return {
        "name": request.param,
        "endpoint": f"https://api.{request.param}.com/v1"
    }


def test_with_parametrized_fixture(llm_provider):
    """This test runs 3 times, once for each provider"""
    assert llm_provider["name"] in ["openai", "anthropic", "ollama"]
    assert "endpoint" in llm_provider


# ============================================================================
# Fixture Composition - Using Fixtures in Fixtures
# ============================================================================

@pytest.fixture
def configured_container(mock_container, mock_llm_manager):
    """Compose multiple fixtures into one"""
    mock_container._llm_manager = mock_llm_manager
    mock_container._config = MagicMock()
    return mock_container


def test_fixture_composition(configured_container):
    """Get a fully configured container in one fixture"""
    assert configured_container._llm_manager is not None
    assert configured_container._config is not None


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest.fixture
async def async_resource():
    """Async fixture for async tests"""
    await asyncio.sleep(0.01)  # Simulate async setup
    yield {"async_data": "test"}
    await asyncio.sleep(0.01)  # Simulate async cleanup


@pytest.mark.anyio
async def test_with_async_fixture(async_resource):
    """Async test using async fixture"""
    assert async_resource["async_data"] == "test"


# ============================================================================
# Using Mock Servers
# ============================================================================

@pytest.mark.anyio
async def test_with_mock_llm_server(mock_llm_server):
    """Test with a real (but mock) HTTP server"""
    import httpx

    # Server is already running from the fixture
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{mock_llm_server.base_url}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Hello"}]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


# ============================================================================
# Using Data Generators
# ============================================================================

def test_with_data_generator(generate_test_user_input):
    """Use data generator fixture"""
    text = generate_test_user_input()
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.parametrize("count", [1, 5, 10])
def test_generate_multiple_memories(memory_factory, count):
    """Generate multiple items using factory"""
    memories = memory_factory.create_batch(count)
    assert len(memories) == count
    for memory in memories:
        assert "id" in memory
        assert "content" in memory


# ============================================================================
# Skipping Based on Fixture Return
# ============================================================================

@pytest.fixture
def conditional_feature():
    """Fixture that determines if a feature is available"""
    return False  # Simulate feature not available


@pytest.fixture
def skip_if_feature_missing(conditional_feature):
    """Skip test if feature is not available"""
    if not conditional_feature:
        pytest.skip("Feature not available")


def test_conditional(skip_if_feature_missing):
    """This test will be skipped"""
    assert False  # Never runs


# ============================================================================
# Fixture with Request Object
# ============================================================================

@pytest.fixture
def check_test_name(request):
    """Fixture can access test metadata"""
    return {
        "name": request.node.name,
        "markers": [m.name for m in request.node.iter_markers()]
    }


def test_metadata(check_test_name):
    """Test can access its own name and markers"""
    assert "test_metadata" in check_test_name["name"]


# ============================================================================
# Summary of Fixture Benefits
# ============================================================================

"""
PYTEST FIXTURE BENEFITS:

1. Reusability:
   - Define once, use everywhere
   - No more repetitive setUp/tearDown

2. Dependency Injection:
   - Fixtures are automatically injected
   - Just list them as parameters

3. Composition:
   - Fixtures can use other fixtures
   - Build complex fixtures from simple ones

4. Scopes:
   - function: fresh for each test
   - module: shared across module
   - session: shared across all tests

5. Cleanup:
   - Use yield for setup/cleanup
   - Runs even if test fails

6. Parametrization:
   - Fixtures can be parametrized
   - Test runs multiple times with different values

EXAMPLE COMPARISON:

Unittest:
---------
class TestChat(unittest.TestCase):
    def setUp(self):
        self.container = ServiceContainer()
        self.mock_llm = MagicMock()
        self.mock_soul = MagicMock()

    def test_example(self):
        # Use self.container, self.mock_llm, etc.
        pass

Pytest:
-------
def test_example(mock_container, mock_llm_manager, mock_soul_service):
    # Fixtures automatically injected
    pass
"""
