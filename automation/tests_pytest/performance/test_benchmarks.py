"""
Performance and benchmark tests for Lumina

These tests measure performance characteristics and detect regressions.
Run with: pytest tests_pytest/performance/ -v --benchmark-only
"""
import sys
from pathlib import Path
import pytest
import time
from unittest.mock import MagicMock, AsyncMock
import asyncio

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

# Try to import pytest-benchmark
try:
    import pytest_benchmark
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False


# ============================================================================
# Micro-benchmarks
# ============================================================================

@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="pytest-benchmark not installed")
@pytest.mark.benchmark
def test_container_initialization_performance(benchmark):
    """Benchmark ServiceContainer initialization"""
    from services.container import ServiceContainer

    def init_container():
        ServiceContainer._instance = None
        return ServiceContainer()

    result = benchmark(init_container)
    assert result is not None


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="pytest-benchmark not installed")
@pytest.mark.benchmark
def test_mock_llm_call_performance(benchmark):
    """Benchmark mock LLM call overhead"""
    mock_llm = MagicMock()
    mock_llm.get_parameters = MagicMock(return_value={"temperature": 0.7})

    result = benchmark(mock_llm.get_parameters)
    assert result["temperature"] == 0.7


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="pytest-benchmark not installed")
@pytest.mark.benchmark
def test_message_creation_performance(benchmark):
    """Benchmark message dict creation"""
    def create_message():
        return {
            "role": "user",
            "content": "Test message content",
            "timestamp": "2024-01-20T00:00:00",
            "metadata": {}
        }

    result = benchmark(create_message)
    assert result["role"] == "user"


# ============================================================================
# Performance Assertions (without pytest-benchmark)
# ============================================================================

@pytest.mark.performance
def test_container_init_is_fast():
    """Ensure container initialization completes quickly"""
    from services.container import ServiceContainer

    start = time.perf_counter()
    for _ in range(100):
        ServiceContainer._instance = None
        container = ServiceContainer()
    elapsed = time.perf_counter() - start

    # 100 initializations should complete in less than 100ms
    assert elapsed < 0.1, f"Container initialization too slow: {elapsed:.3f}s for 100 iterations"


@pytest.mark.performance
def test_message_list_operations():
    """Test message list operation performance"""
    messages = [{"role": "user", "content": f"Message {i}"} for i in range(1000)]

    start = time.perf_counter()
    # Simulate common operations
    filtered = [m for m in messages if m["role"] == "user"]
    last_10 = messages[-10:]
    elapsed = time.perf_counter() - start

    assert elapsed < 0.01, f"List operations too slow: {elapsed:.4f}s"
    assert len(filtered) == 1000
    assert len(last_10) == 10


@pytest.mark.performance
@pytest.mark.anyio
async def test_async_mock_performance():
    """Test async mock operation performance"""
    mock_llm = AsyncMock()

    async def mock_stream():
        for _ in range(10):
            yield "chunk"

    mock_llm.chat_completion = AsyncMock(return_value=mock_stream())

    start = time.perf_counter()
    await mock_llm.chat_completion()
    elapsed = time.perf_counter() - start

    assert elapsed < 0.1, f"Async mock too slow: {elapsed:.4f}s"


# ============================================================================
# Memory Usage Tests
# ============================================================================

@pytest.mark.performance
def test_memory_list_growth():
    """Test that memory lists don't grow unbounded"""
    import tracemalloc

    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Simulate adding many memories
    memories = []
    for i in range(1000):
        memories.append({
            "id": f"mem_{i}",
            "content": f"Memory content {i}" * 10,
            "embedding": [0.0] * 512
        })

    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Calculate memory growth
    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats)

    # Should use less than 50MB for 1000 memories
    assert total_growth < 50 * 1024 * 1024, f"Memory usage too high: {total_growth / 1024 / 1024:.2f}MB"


# ============================================================================
# Concurrency Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.anyio
async def test_concurrent_chat_requests():
    """Test handling multiple concurrent chat requests"""
    async def mock_chat_request(request_id):
        await asyncio.sleep(0.01)  # Simulate processing
        return f"Response {request_id}"

    start = time.perf_counter()
    tasks = [mock_chat_request(i) for i in range(50)]
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    assert len(results) == 50
    # 50 concurrent requests should complete in under 1 second
    assert elapsed < 1.0, f"Concurrent requests too slow: {elapsed:.2f}s"


@pytest.mark.performance
def test_thread_safety():
    """Test that container is thread-safe under concurrent access"""
    import threading
    from services.container import ServiceContainer

    ServiceContainer._instance = None
    container = ServiceContainer()
    errors = []

    def access_container(thread_id):
        try:
            for _ in range(100):
                container.get_config()
        except Exception as e:
            errors.append((thread_id, e))

    threads = [threading.Thread(target=access_container, args=(i,)) for i in range(10)]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start

    assert len(errors) == 0, f"Thread safety issues: {errors}"
    # Should complete quickly
    assert elapsed < 1.0, f"Threaded access too slow: {elapsed:.2f}s"


# ============================================================================
# Scaling Tests
# ============================================================================

@pytest.mark.performance
def test_message_history_scaling():
    """Test that message processing scales linearly with history size"""
    import time

    def process_messages(count):
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(count)]
        # Simulate message processing
        return [m for m in messages if m["role"] == "user"]

    sizes = [10, 100, 1000, 5000]
    times = []

    for size in sizes:
        start = time.perf_counter()
        process_messages(size)
        elapsed = time.perf_counter() - start
        times.append((size, elapsed))

    # Check that growth is roughly linear (not exponential)
    # Each 10x increase should take roughly 10x time (allowing 20x variance)
    for i in range(len(times) - 1):
        size1, time1 = times[i]
        size2, time2 = times[i + 1]
        ratio = (size2 / size1)
        time_ratio = (time2 / time1) if time1 > 0 else 1
        # Allow 30x time increase for 10x data size (some overhead is okay)
        assert time_ratio < ratio * 3, f"Non-linear scaling detected: {size1}->{size2} took {time_ratio:.1f}x time"


# ============================================================================
# Serialization Performance
# ============================================================================

@pytest.mark.performance
def test_json_serialization_performance():
    """Test JSON serialization speed"""
    import json

    data = {
        "messages": [{"role": "user", "content": f"Message {i}"} for i in range(100)],
        "metadata": {"key": "value" * 50}
    }

    start = time.perf_counter()
    serialized = json.dumps(data)
    deserialized = json.loads(serialized)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.01, f"JSON serialization too slow: {elapsed:.4f}s"
    assert deserialized == data


# ============================================================================
# Cache Performance
# ============================================================================

@pytest.mark.performance
def test_cache_hit_rate():
    """Test that caching provides performance benefits"""
    from functools import lru_cache

    @lru_cache(maxsize=128)
    def expensive_computation(x):
        # Simulate expensive computation
        return sum(i * x for i in range(1000))

    # First call - cache miss
    start = time.perf_counter()
    result1 = expensive_computation(5)
    time_miss = time.perf_counter() - start

    # Second call - cache hit
    start = time.perf_counter()
    result2 = expensive_computation(5)
    time_hit = time.perf_counter() - start

    # Cache hit should be at least 100x faster
    assert time_hit < time_miss / 100, f"Cache not effective: hit={time_hit:.6f}s, miss={time_miss:.6f}s"
    assert result1 == result2


# ============================================================================
# Performance Regression Tests
# ============================================================================

@pytest.mark.performance
def test_plugin_discovery_performance():
    """Test that plugin discovery scales well"""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create many plugin directories
        for i in range(100):
            plugin_dir = os.path.join(tmpdir, f"plugin_{i}")
            os.makedirs(plugin_dir)
            with open(os.path.join(plugin_dir, "manifest.yaml"), 'w') as f:
                f.write(f"id: plugin_{i}\nname: Plugin {i}\n")

        # Time the discovery
        start = time.perf_counter()
        plugins_found = []
        for root, dirs, files in os.walk(tmpdir):
            if "manifest.yaml" in files:
                plugins_found.append(root)
        elapsed = time.perf_counter() - start

        assert len(plugins_found) == 100
        # Discovery should be fast even with many plugins
        assert elapsed < 0.5, f"Plugin discovery too slow: {elapsed:.2f}s for 100 plugins"


# ============================================================================
# Installation Instructions
# ============================================================================

"""
PERFORMANCE TESTING NOTES:

1. Install pytest-benchmark for accurate benchmarks:
   pip install pytest-benchmark

2. Run benchmarks:
   pytest tests_pytest/performance/ -v --benchmark-only

3. Compare runs:
   pytest tests_pytest/performance/ -v --benchmark-only --benchmark-autosave
   pytest tests_pytest/performance/ -v --benchmark-only --benchmark-compare=FILE

4. Generate histogram:
   pytest tests_pytest/performance/ -v --benchmark-only --benchmark-histogram

5. Performance marks:
   Use @pytest.mark.performance to tag performance tests
   Run with: pytest -m performance -v
"""
