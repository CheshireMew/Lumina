"""
Pytest version of ServiceContainer tests

Demonstrates pytest advantages over unittest:
- Less boilerplate
- Cleaner assertions
- Built-in fixtures
- Better parametrization
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.container import ServiceContainer, ServiceNotInitializedError


# ============================================================================
# Basic Tests (compare with unittest version)
# ============================================================================

def test_explicit_container_instances_are_isolated():
    """Independent composition roots must not share registered services."""
    instance1 = ServiceContainer()
    instance2 = ServiceContainer()
    instance1.set_config(MagicMock(name="first"))

    assert instance1 is not instance2
    with pytest.raises(ServiceNotInitializedError):
        instance2.get_config()


def test_service_registration():
    """Cleaner assertions - just use assert"""
    container = ServiceContainer()
    mock_config = MagicMock()
    mock_config.test_attr = "test_value"

    container.set_config(mock_config)
    retrieved = container.get_config()

    # Pytest automatically provides detailed error messages
    assert retrieved is mock_config
    assert retrieved.test_attr == "test_value"


def test_uninitialized_service_error():
    """Testing exceptions with pytest.raises()"""
    container = ServiceContainer()
    with pytest.raises(ServiceNotInitializedError) as exc_info:
        container.get_gateway()
    # Can check the exception message
    assert "Gateway not initialized" in str(exc_info.value)


# ============================================================================
# Parametrized Tests - pytest advantage
# ============================================================================

@pytest.mark.parametrize("service_name,setter_method,getter_method", [
    ("event_bus", "set_event_bus", "get_event_bus"),
    ("config", "set_config", "get_config"),
    ("llm_manager", "set_llm_manager", "get_llm_manager"),
    ("vision", "set_vision", "get_vision"),
    ("tts", "set_tts", "get_tts"),
])
def test_service_registration_parametrized(service_name, setter_method, getter_method):
    """One test definition, multiple cases - much cleaner than writing separate tests"""
    container = ServiceContainer()
    mock_service = MagicMock(name=service_name)

    # Dynamically call setter and getter methods
    setter = getattr(container, setter_method)
    getter = getattr(container, getter_method)

    setter(mock_service)
    assert getter() is mock_service


# ============================================================================
# Parametrized with IDs and custom test names
# ============================================================================

@pytest.mark.parametrize("input_id,expected_valid", [
    ("test.module", True),
    ("my_extension", True),
    ("vendor.module-name", True),
    ("../etc/passwd", False),
    ("module with spaces", False),
    ("module\nwith\nnewlines", False),
], ids=["valid1", "valid2", "valid3", "path_traversal", "spaces", "newlines"])
def test_module_id_validation(input_id, expected_valid):
    """Test with readable test IDs in output"""
    import re
    id_pattern = re.compile(r'^[a-zA-Z0-9_\.\-]+$')
    is_valid = bool(id_pattern.match(input_id))
    assert is_valid == expected_valid


# ============================================================================
# Fixture-based tests
# ============================================================================

def test_with_fixture(mock_container):
    """Using the fixture from conftest.py - no setup needed!"""
    # mock_container is automatically provided by pytest
    assert mock_container is not None

    # Test multiple registrations
    mock_event_bus = MagicMock(name="EventBus")
    mock_config = MagicMock(name="Config")

    mock_container.set_event_bus(mock_event_bus)
    mock_container.set_config(mock_config)

    assert mock_container.get_event_bus() is mock_event_bus
    assert mock_container.get_config() is mock_config


# ============================================================================
# Test grouping with marks
# ============================================================================

@pytest.mark.unit
def test_tool_provider_registry():
    """Tests can be marked and run by category"""
    container = ServiceContainer()
    mock_tool = MagicMock(name="ToolProvider")
    mock_tool.name = "test_tool"

    container.register_tool_provider(mock_tool)
    retrieved = container.get_tool_provider("test_tool")

    assert retrieved is mock_tool


@pytest.mark.unit
@pytest.mark.parametrize("num_tools", [1, 5, 10])
def test_multiple_tools_registration(num_tools):
    """Test with multiple parameters"""
    container = ServiceContainer()
    tools = []

    for i in range(num_tools):
        mock_tool = MagicMock(name=f"Tool{i}")
        mock_tool.name = f"tool{i}"
        container.register_tool_provider(mock_tool)
        tools.append(mock_tool)

    all_tools = container.get_all_tools()
    assert len(all_tools) == num_tools
    assert all_tools == tools


# ============================================================================
# Testing edge cases with parametrize
# ============================================================================

@pytest.mark.parametrize("service_attr,should_be_none", [
    ("process_manager", False),
    ("gateway", False),  # Will raise error
])
def test_optional_vs_required_services(service_attr, should_be_none):
    """Test both optional and required services in one test"""
    container = ServiceContainer()

    if should_be_none:
        # Optional services return None
        result = getattr(container, f"get_{service_attr}")()
        assert result is None
    else:
        # Required services raise error
        with pytest.raises(ServiceNotInitializedError):
            getattr(container, f"get_{service_attr}")()


# ============================================================================
# Skipping tests
# ============================================================================

@pytest.mark.skip(reason="Demonstrating skipped test")
def test_skipped_example():
    """This test will be skipped"""
    assert False


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python 3.8+")
def test_version_specific():
    """Only runs on certain Python versions"""
    import sys
    assert sys.version_info >= (3, 8)


# ============================================================================
# XFail tests - expected to fail
# ============================================================================

@pytest.mark.xfail(reason="Known issue - to be fixed")
def test_known_issue():
    """This test is expected to fail"""
    assert False  # Known failing test


# ============================================================================
# Custom markers
# ============================================================================

@pytest.mark.slow
def test_slow_operation():
    """Marked as slow - can be skipped with pytest -m 'not slow'"""
    import time
    time.sleep(0.1)
    assert True


# ============================================================================
# Exception testing patterns
# ============================================================================

def test_exception_with_match():
    """Test exception messages with pattern matching"""
    container = ServiceContainer()
    with pytest.raises(ServiceNotInitializedError, match="Gateway.*not initialized"):
        container.get_gateway()


# ============================================================================
# Warning testing
# ============================================================================

def test_warnings():
    """Test that code produces expected warnings"""
    import warnings
    warnings.warn("This is a test warning", UserWarning)
    # Can use pytest.warns() context manager to check for warnings


# ============================================================================
# Approximate comparisons (useful for floats)
# ============================================================================

@pytest.mark.parametrize("value,expected,tolerance", [
    (0.1 + 0.2, 0.3, 1e-10),
    (1.0 / 3.0 * 3, 1.0, 1e-10),
])
def test_approximate_comparisons(value, expected, tolerance):
    """Pytest handles float comparisons gracefully"""
    assert value == pytest.approx(expected, abs=tolerance)


# ============================================================================
# Comparison with unittest summary
# ============================================================================

"""
UNITTEST VS PYTEST COMPARISON:

The container tests construct explicit, independent composition roots. They do not
reset hidden class state or call a global singleton accessor.

Advantages:
1. No class inheritance needed
2. No self parameter
3. Cleaner assert statements (just use assert)
4. No need to call print() for feedback
5. Parametrization built-in
6. Fixtures instead of setUp/tearDown
7. Better error messages automatically
"""
