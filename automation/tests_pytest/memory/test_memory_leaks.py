"""
Memory leak detection tests for Lumina

These tests help identify memory leaks and resource management issues.
Run with: pytest tests_pytest/memory/test_memory_leaks.py -v
"""
import sys
from pathlib import Path
import pytest
import gc
import tracemalloc
import time
from unittest.mock import MagicMock, AsyncMock
import asyncio

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


# ============================================================================
# Memory Leak Detection Tests
# ============================================================================

@pytest.mark.memory
def test_service_container_no_leak():
    """Test that ServiceContainer doesn't leak memory"""
    from services.container import ServiceContainer

    # Start tracking memory
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create and destroy many containers
    for _ in range(1000):
        ServiceContainer._instance = None
        container = ServiceContainer()
        # Use the container
        mock_config = MagicMock()
        container.set_config(mock_config)
        del container

    # Force garbage collection
    gc.collect()

    # Check memory growth
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Allow some growth (caching) but not excessive
    max_growth = 10 * 1024 * 1024  # 10MB
    assert total_growth < max_growth, f"Memory leak detected: {total_growth / 1024 / 1024:.2f}MB growth"


@pytest.mark.memory
def test_memory_list_operations():
    """Test that list operations don't leak memory"""
    # Start tracking
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Perform many list operations
    data = []
    for i in range(10000):
        item = {
            "id": f"item_{i}",
            "data": "x" * 100,
            "nested": {"key": "value" * 10}
        }
        data.append(item)
        # Process the list
        filtered = [x for x in data if i % 2 == 0]
        del filtered

    del data
    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Should be minimal after cleanup
    assert total_growth < 5 * 1024 * 1024, f"Memory leak: {total_growth / 1024 / 1024:.2f}MB"


@pytest.mark.memory
def test_mock_object_cleanup():
    """Test that mock objects are properly cleaned up"""
    # Start tracking
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create many mock objects
    for _ in range(1000):
        mock = MagicMock()
        mock.method1 = MagicMock()
        mock.method2 = AsyncMock()
        # Use the mock
        mock.method1()
        del mock

    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Mocks should be cleaned up
    assert total_growth < 5 * 1024 * 1024, f"Mock cleanup failed: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Async Memory Leak Tests
# ============================================================================

@pytest.mark.memory
@pytest.mark.asyncio
async def test_async_context_manager_cleanup():
    """Test that async resources are properly cleaned up"""
    # Start tracking
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create many async contexts
    async def async_operation():
        # Simulate async resource usage
        await asyncio.sleep(0.001)
        return {"data": "x" * 100}

    for _ in range(100):
        await async_operation()

    # Force cleanup
    await asyncio.gather(*[asyncio.sleep(0) for _ in range(10)])
    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    assert total_growth < 5 * 1024 * 1024, f"Async memory leak: {total_growth / 1024 / 1024:.2f}MB"


@pytest.mark.memory
@pytest.mark.asyncio
async def test_event_loop_cleanup():
    """Test that event loop doesn't accumulate memory"""
    # Start tracking
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create many async tasks
    for i in range(100):
        await asyncio.sleep(0.001)
        await asyncio.gather(
            asyncio.sleep(0.001),
            asyncio.sleep(0.001),
            asyncio.sleep(0.001)
        )

    # Let event loop clean up
    await asyncio.sleep(0.1)
    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    assert total_growth < 10 * 1024 * 1024, f"Event loop memory leak: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Object Reference Tests
# ============================================================================

@pytest.mark.memory
def test_circular_reference_cleanup():
    """Test that circular references are cleaned up"""
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create circular references
    for _ in range(100):
        obj_a = {"data": "x" * 100}
        obj_b = {"data": "y" * 100}
        obj_a["ref"] = obj_b
        obj_b["ref"] = obj_a

        # Delete one reference
        del obj_a
        del obj_b

    # Force garbage collection
    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Circular references should be collected
    assert total_growth < 5 * 1024 * 1024, f"Circular reference not collected: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Large Object Tests
# ============================================================================

@pytest.mark.memory
def test_large_object_disposal():
    """Test that large objects are properly disposed"""
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create and discard large objects
    for _ in range(10):
        large_obj = {
            "data": "x" * (1024 * 1024)  # 1MB string
        }
        # Use it
        _ = len(large_obj["data"])
        del large_obj

    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Large objects should be disposed
    assert total_growth < 20 * 1024 * 1024, f"Large object not disposed: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Generator Memory Tests
# ============================================================================

@pytest.mark.memory
def test_generator_memory_efficiency():
    """Test that generators don't leak memory"""
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    def data_generator(count):
        """Generate test data"""
        for i in range(count):
            yield {
                "id": i,
                "data": "x" * 100
            }

    # Consume generators
    for _ in range(100):
        result = list(data_generator(100))
        assert len(result) == 100
        del result

    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    assert total_growth < 5 * 1024 * 1024, f"Generator memory leak: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Closure Memory Tests
# ============================================================================

@pytest.mark.memory
def test_closure_memory_leaks():
    """Test that closures don't capture excessive memory"""
    gc.collect()
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create closures with large captured data
    closures = []
    for i in range(100):
        large_data = "x" * 10000
        def closure():
            return len(large_data)  # Capture large_data
        closures.append(closure)

    # Use closures
    for closure in closures:
        result = closure()
        assert result == 10000

    del closures
    gc.collect()

    # Check memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Closures should be garbage collected
    assert total_growth < 10 * 1024 * 1024, f"Closure memory leak: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Memory Profiling Helper
# ============================================================================

@pytest.fixture
def memory_profiler():
    """Fixture for memory profiling during tests"""
    tracemalloc.start()
    yield
    tracemalloc.stop()


@pytest.mark.memory
def test_with_profiling(memory_profiler):
    """Example test with memory profiling"""
    # This test will have detailed memory tracking
    data = []
    for i in range(1000):
        data.append({"id": i, "value": "test" * 10})

    # Get current memory usage
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory: {current / 1024 / 1024:.2f}MB")
    print(f"Peak memory: {peak / 1024 / 1024:.2f}MB")


# ============================================================================
# Summary
# ============================================================================

"""
MEMORY LEAK TESTING NOTES:

1. Using tracemalloc:
   - Tracks memory allocations
   - Compares snapshots
   - Identifies memory growth

2. Common Memory Leak Patterns:
   - Unclosed resources
   - Circular references
   - Global variables growing
   - Caches not being cleared
   - Event handlers not removed
   - Generators not being exhausted

3. Detection Strategies:
   - Run tests multiple times
   - Monitor over time
   - Test with increasing scale
   - Use memory profilers

4. Tools:
   - tracemalloc (standard library)
   - objgraph (visualize references)
   - pympler (detailed profiling)

RUNNING MEMORY TESTS:
    pytest tests_pytest/memory/ -v
    pytest -m memory -v

WITH PROFILING:
    python -m tracemalloc
    pytest tests_pytest/memory/ -v --tracemalloc

VISUALIZE REFERENCES:
    pip install objgraph
    python -c "import objgraph; objgraph.show_growth()"
"""
