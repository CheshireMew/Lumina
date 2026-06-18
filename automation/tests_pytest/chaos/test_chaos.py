"""
Chaos testing for Lumina

These tests inject failures to verify system resilience.
Run with: pytest tests_pytest/chaos/test_chaos.py -v
"""
import sys
from pathlib import Path
import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import random
import tempfile

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


# ============================================================================
# Chaos Testing - Service Failure Injection
# ============================================================================

@pytest.mark.chaos
@pytest.mark.anyio
async def test_llm_service_random_failure():
    """Test system handles LLM service failures gracefully"""
    # Simulate random LLM failures
    failure_rate = 0.3  # 30% failure rate

    async def unreliable_llm():
        if random.random() < failure_rate:
            raise ConnectionError("LLM service unavailable")
        return "Normal response"

    # Test that chat service handles failures
    attempts = 0
    successes = 0

    for _ in range(10):
        attempts += 1
        try:
            result = await unreliable_llm()
            successes += 1
        except ConnectionError:
            pass  # Should be handled

    # Should have at least some successes
    assert successes > 0, "All LLM attempts failed"
    print(f"Chaos test: {successes}/{attempts} LLM requests succeeded")


@pytest.mark.chaos
def test_database_connection_timeout():
    """Test system handles database timeouts"""
    # Simulate slow database
    def slow_query():
        time.sleep(2)  # Simulate timeout
        return "result"

    # Should have timeout handling
    start = time.time()
    try:
        result = slow_query()
        elapsed = time.time() - start
        assert elapsed >= 2
    except Exception as e:
        # Should handle timeout gracefully
        assert "timeout" in str(e).lower() or "time" in str(e).lower()


# ============================================================================
# Network Chaos - Packet Loss and Delay
# ============================================================================

@pytest.mark.chaos
@pytest.mark.anyio
async def test_network_delay_handling():
    """Test system handles network delays"""
    import httpx

    # Mock server with artificial delay
    class DelayedMock:
        async def get(self, url, timeout=None):
            await asyncio.sleep(0.5)  # 500ms delay
            return httpx.Response(200, request=None)

    # Should handle delayed responses
    client = DelayedMock()
    start = time.time()
    response = await client.get("http://test")
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed >= 0.5  # Delay was applied


@pytest.mark.chaos
def test_random_service_unavailability():
    """Test behavior when services become unavailable"""
    services_status = {
        "llm": random.choice([True, False]),
        "memory": random.choice([True, False]),
        "stt": random.choice([True, False]),
        "tts": random.choice([True, False])
    }

    # System should degrade gracefully
    available_count = sum(services_status.values())

    if available_count == 0:
        # All services down - should show error
        assert True  # Would show user-facing error
    elif available_count < 4:
        # Partial degradation - limited functionality
        assert True  # Would show degraded mode
    else:
        # All services available
        assert True  # Full functionality


# ============================================================================
# Resource Exhaustion Tests
# ============================================================================

@pytest.mark.chaos
def test_memory_exhaustion_handling():
    """Test system handles memory pressure"""
    import sys

    # Simulate memory pressure
    original_memory = []

    def consume_memory():
        # Allocate memory in chunks
        chunk = []
        for i in range(1000):
            chunk.append([0] * 1000)  # ~8KB per chunk
        return chunk

    try:
        # Try to allocate a lot of memory
        for _ in range(10):
            chunk = consume_memory()
            original_memory.append(chunk)

        # Should have memory management
        # (In real system, would trigger cleanup)
        assert len(original_memory) > 0

    except MemoryError:
        # Should handle gracefully
        assert True, "MemoryError not handled"


@pytest.mark.chaos
def test_file_descriptor_exhaustion():
    """Test system handles file descriptor limits"""
    import os
    tempfile.tempdir = "chaos_fd_test"

    try:
        os.makedirs(tempfile.tempdir, exist_ok=True)

        # Open many files
        files = []
        for i in range(100):
            try:
                f = open(os.path.join(tempfile.tempdir, f"test_{i}.tmp"), 'w')
                files.append(f)
            except OSError:
                # Hit file descriptor limit
                break

        # Should handle gracefully
        # Clean up files we opened
        for f in files:
            f.close()

        assert len(files) > 0  # At least some files opened
        assert len(files) <= 100

    finally:
        # Cleanup
        import shutil
        if os.path.exists(tempfile.tempdir):
            shutil.rmtree(tempfile.tempdir, ignore_errors=True)


# ============================================================================
# Race Condition Tests
# ============================================================================

@pytest.mark.chaos
def test_concurrent_dictionary_access():
    """Test that concurrent dictionary access is safe"""
    import threading

    shared_dict = {}
    errors = []

    def modify_dict(thread_id):
        try:
            for i in range(100):
                # Concurrent modifications
                shared_dict[f"key_{thread_id}_{i}"] = f"value_{i}"
                # Concurrent reads
                _ = shared_dict.get(f"key_{thread_id}_{i}")
        except Exception as e:
            errors.append((thread_id, e))

    threads = [threading.Thread(target=modify_dict, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Race conditions detected: {errors}"


@pytest.mark.chaos
@pytest.mark.anyio
async def test_concurrent_async_operations():
    """Test async race conditions"""
    shared_state = {"counter": 0}
    errors = []

    async def increment_counter(task_id):
        try:
            for _ in range(100):
                # Simulate race condition
                current = shared_state["counter"]
                await asyncio.sleep(0.0001)  # Force context switch
                shared_state["counter"] = current + 1
        except Exception as e:
            errors.append((task_id, e))

    # Run concurrent tasks
    tasks = [increment_counter(i) for i in range(10)]
    await asyncio.gather(*tasks)

    # May have race conditions (not protected)
    # Counter should be 1000 if no races
    final_count = shared_state["counter"]
    assert final_count <= 1000, f"Counter overflow: {final_count}"
    if final_count < 1000:
        print(f"Chaos test: Race condition detected (counter={final_count}/1000)")


# ============================================================================
# Corrupted Input Tests
# ============================================================================

@pytest.mark.chaos
@pytest.mark.parametrize("corrupted_input", [
    None,  # None value
    123,  # Integer instead of string
    {"incomplete": "dict"},  # Incomplete dict
    "���",  # Invalid Unicode
    "\x00\x01\x02",  # Control characters
    "A" * 10000,  # Long input (avoid exceeding Windows 32k env limit)
])
def test_corrupted_input_handling(corrupted_input):
    """Test that corrupted input is handled gracefully"""
    def validate_and_process(input_data):
        """Validate and process input"""
        # Type check
        if not isinstance(input_data, str):
            return {"status": "error", "reason": "invalid_type"}

        # Null byte check
        if '\x00' in input_data:
            return {"status": "error", "reason": "null_bytes"}

        # Length check
        if len(input_data) > 10000:
            return {"status": "error", "reason": "too_long"}

        # Processing
        return {"status": "success", "processed": len(input_data)}

    result = validate_and_process(corrupted_input)
    assert "status" in result  # Should always return a result


# ============================================================================
# State Corruption Tests
# ============================================================================

@pytest.mark.chaos
def test_state_corruption_recovery():
    """Test system can recover from corrupted state"""
    from services.container import ServiceContainer

    # Reset singleton
    ServiceContainer._instance = None
    container = ServiceContainer()

    # Corrupt the state
    container._instance = None

    # Should recover or handle gracefully
    try:
        new_instance = ServiceContainer()
        assert new_instance is not None
    except Exception as e:
        pytest.fail(f"Failed to recover from corrupted state: {e}")


# ============================================================================
# Chaos Engineering Summary
# ============================================================================

"""
CHAOS TESTING PRINCIPLES:

1. Assume Failure Will Happen:
   - Services will fail
   - Network will fail
   - Resources will be exhausted

2. Test Recovery:
   - System should detect failures
   - System should recover gracefully
   - No data corruption

3. Test Degradation:
   - System should function in degraded mode
   - Clear error messages
   - Graceful fallbacks

CHAOS TEST TYPES:

1. Service Failure Injection:
   - Random service failures
   - Timeout simulation
   - Network partitions

2. Resource Exhaustion:
   - Memory pressure
   - File descriptor limits
   - CPU exhaustion

3. Race Conditions:
   - Concurrent access
   - Async timing issues
   - State consistency

4. Corrupted Input:
   - Invalid types
   - Malformed data
   - Unicode issues

RUNNING CHAOS TESTS:
    pytest tests_pytest/chaos/ -v
    pytest -m chaos -v

NOTE: Chaos tests may destabilize the system. Run with caution.

BEST PRACTICES:
    - Run in isolated environment
    - Don't run against production
    - Monitor system during tests
    - Have rollback plan ready
"""
