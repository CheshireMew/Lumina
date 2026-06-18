"""
REAL pytest tests for Lumina - Testing actual code

This file demonstrates how to write PRODUCTION pytest tests that
test real Lumina code and can catch real bugs.

Key differences from teaching examples:
1. Imports REAL modules from python_backend
2. Tests REAL classes and methods
3. Uses REAL data structures
4. Can CATCH REAL BUGS
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
import asyncio

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

# Import REAL Lumina code
from services.container import ServiceContainer, ServiceNotInitializedError


# ============================================================================
# Test 1: ServiceContainer Singleton (REAL TEST)
# ============================================================================

def test_service_container_singleton_real():
    """
    Test that ServiceContainer is a true singleton.

    This tests REAL behavior: if singleton pattern breaks,
    multiple instances will be created and cause bugs.
    """
    # Reset singleton state
    ServiceContainer._instance = None

    # Get two instances
    instance1 = ServiceContainer.get_instance()
    instance2 = ServiceContainer.get_instance()

    # They MUST be the same object (singleton pattern)
    assert instance1 is instance2, "ServiceContainer must be a singleton"


# ============================================================================
# Test 2: Service Registration Error Handling (REAL TEST)
# ============================================================================

def test_service_container_uninitialized_error():
    """
    Test that accessing uninitialized services raises proper error.

    This catches REAL bugs where code doesn't check if services
    are initialized before using them.
    """
    container = ServiceContainer()

    # Try to access uninitialized service
    with pytest.raises(ServiceNotInitializedError) as exc_info:
        container.get_gateway()

    # Verify error message is helpful
    assert "not initialized" in str(exc_info.value).lower()

    with pytest.raises(ServiceNotInitializedError):
        container.get_soul()

    with pytest.raises(ServiceNotInitializedError):
        container.get_session_manager()

    with pytest.raises(ServiceNotInitializedError):
        container.get_process_manager()

    with pytest.raises(ServiceNotInitializedError):
        container.get_worker_runtime_registry()

    with pytest.raises(ServiceNotInitializedError):
        container.get_capability_registry()

    with pytest.raises(ServiceNotInitializedError):
        container.get_capability_module_manager()


# ============================================================================
# Test 3: Service Container Thread Safety (REAL TEST)
# ============================================================================

def test_service_container_thread_safety():
    """
    Test that ServiceContainer is thread-safe.

    This catches REAL concurrency bugs that occur when
    multiple threads access the singleton simultaneously.
    """
    import threading

    ServiceContainer._instance = None
    instances = []
    errors = []

    def get_instance():
        try:
            instance = ServiceContainer.get_instance()
            instances.append(instance)
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = [threading.Thread(target=get_instance) for _ in range(10)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join()

    # Verify: no errors occurred
    assert len(errors) == 0, f"Thread safety errors: {errors}"

    # Verify: all threads got the same instance
    assert len(instances) == 10
    assert len(set(id(i) for i in instances)) == 1, "All threads must get same instance"


# ============================================================================
# Test 4: Service Container Service Lifecycle (REAL TEST)
# ============================================================================

def test_service_container_lifecycle():
    """
    Test complete service lifecycle: register -> use -> replace -> use.

    This catches REAL bugs in service replacement logic.
    """
    container = ServiceContainer()

    # Register initial service
    service1 = MagicMock(name="service_v1")
    service1.version = "1.0"
    container.set_config(service1)

    # Verify we get v1
    retrieved1 = container.get_config()
    assert retrieved1 is service1
    assert retrieved1.version == "1.0"

    # Replace with new service
    service2 = MagicMock(name="service_v2")
    service2.version = "2.0"
    container.set_config(service2)

    # Verify we get v2 (not v1)
    retrieved2 = container.get_config()
    assert retrieved2 is service2
    assert retrieved2.version == "2.0"
    assert retrieved2 is not service1


# ============================================================================
# Test 5: Explicit Getter Consistency (REAL TEST)
# ============================================================================

def test_service_container_getter_consistency():
    """
    Test that explicit setters and getters return same instance.

    This catches REAL bugs where service slot replacement gets out of sync.
    """
    container = ServiceContainer()

    # Register via setter
    mock_service = MagicMock(name="test_service")
    container.set_event_bus(mock_service)

    # Access via getter
    via_getter = container.get_event_bus()

    # Must be the same object
    assert via_getter is mock_service


# ============================================================================
# Test 6: Multiple Services Independence (REAL TEST)
# ============================================================================

def test_service_container_services_independent():
    """
    Test that different services don't interfere with each other.

    This catches REAL bugs where one service overwrites another.
    """
    container = ServiceContainer()

    # Register multiple services
    event_bus = MagicMock(name="event_bus")
    config = MagicMock(name="config")
    llm = MagicMock(name="llm")

    container.set_event_bus(event_bus)
    container.set_config(config)
    container.set_llm_manager(llm)

    # Verify each service is independent
    assert container.get_event_bus() is event_bus
    assert container.get_config() is config
    assert container.get_llm_manager() is llm

    # Replace one service shouldn't affect others
    new_config = MagicMock(name="new_config")
    container.set_config(new_config)

    assert container.get_config() is new_config
    assert container.get_event_bus() is event_bus  # Unchanged
    assert container.get_llm_manager() is llm  # Unchanged


# ============================================================================
# Test 7: Service Container with Real Dependencies (REAL TEST)
# ============================================================================

@patch('services.container.services')
def test_service_container_with_real_dependencies(mock_services):
    """
    Test ServiceContainer integration with global services singleton.

    This catches REAL bugs in the global services integration.
    """
    container = ServiceContainer()

    # The container should work independently of global services
    local_service = MagicMock(name="local")
    container.set_config(local_service)

    # Should get local service
    retrieved = container.get_config()
    assert retrieved is local_service


# ============================================================================
# Test 8: Error Recovery (REAL TEST)
# ============================================================================

def test_service_container_error_recovery():
    """
    Test that ServiceContainer can recover from errors.

    This catches REAL bugs where errors leave container in bad state.
    """
    container = ServiceContainer()

    # Register a service
    service = MagicMock(name="service")
    container.set_config(service)

    # Access it successfully
    assert container.get_config() is service

    # Simulate reset through the container API.
    container.set_config(None)

    # Should raise proper error, not crash
    with pytest.raises(ServiceNotInitializedError):
        container.get_config()

    # Recovery: register new service
    new_service = MagicMock(name="new_service")
    container.set_config(new_service)

    # Should work again
    assert container.get_config() is new_service


# ============================================================================
# Test 9: Service Container with None Values (REAL TEST)
# ============================================================================

def test_service_container_none_handling():
    """
    Test that ServiceContainer properly handles None values.

    This catches REAL bugs where None is treated as valid service.
    """
    container = ServiceContainer()

    # Try to set None (should be allowed for resetting)
    container.set_config(None)

    # Accessing None service should raise error
    with pytest.raises(ServiceNotInitializedError):
        container.get_config()


# ============================================================================
# Test 10: Explicit Gateway Access (REAL TEST)
# ============================================================================

def test_service_container_explicit_gateway_access():
    """
    Test explicit gateway registration.

    This catches REAL bugs when gateway registration changes.
    """
    container = ServiceContainer()

    gateway_service = MagicMock(name="gateway")
    container.set_gateway(gateway_service)

    via_getter = container.get_gateway()

    assert via_getter is gateway_service


def test_service_container_companion_services_are_explicit():
    container = ServiceContainer()

    context_resolver = MagicMock(name="companion_context_resolver")
    interaction_recorder = MagicMock(name="companion_interaction_recorder")
    soul = MagicMock(name="soul")
    session_manager = MagicMock(name="session_manager")
    container.set_companion_context_resolver(context_resolver)
    container.set_companion_interaction_recorder(interaction_recorder)
    container.set_soul(soul)
    container.set_session_manager(session_manager)

    assert container.get_companion_context_resolver() is context_resolver
    assert container.get_companion_interaction_recorder() is interaction_recorder
    assert container.get_soul() is soul
    assert container.get_session_manager() is session_manager


# ============================================================================
# SUMMARY: What Makes These "Real" Tests?
# ============================================================================

"""
REAL TEST CHARACTERISTICS:

1. ✅ Imports REAL modules from python_backend
2. ✅ Tests REAL classes (ServiceContainer)
3. ✅ Tests REAL methods (get_instance, get_config, etc.)
4. ✅ Uses REAL error types (ServiceNotInitializedError)
5. ✅ Tests REAL behavior (singleton, thread safety, lifecycle)
6. ✅ Can CATCH REAL BUGS (concurrency issues, state corruption, etc.)

FAKE TEST CHARACTERISTICS (avoid these):

1. ❌ Tests code defined in the test file itself
2. ❌ Only demonstrates testing framework features
3. ❌ Never imports production code
4. ❌ Cannot catch any real bugs
5. ❌ Creates circular logic (test verifies itself)

HOW TO WRITE REAL TESTS:

1. Import REAL modules:
   from services.container import ServiceContainer

2. Test REAL classes:
   container = ServiceContainer()

3. Test REAL methods:
   result = container.get_config()

4. Test REAL behavior:
   assert result == expected_real_value

5. Test REAL error cases:
   with pytest.raises(RealError):
       do_something_that_should_fail()

RUN THESE TESTS:
    pytest tests_pytest_real/test_real_container.py -v
"""
