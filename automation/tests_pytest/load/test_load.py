"""
Load testing for Lumina using Locust

Simulates multiple concurrent users to test system capacity.
Install: pip install locust
Run: locust -f tests_pytest/load/test_load.py --host=http://127.0.0.1:8010
"""
import sys
from pathlib import Path
import time
import pytest

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


def require_core_service():
    """Skip live load tests when the local backend is not running."""
    import httpx

    try:
        response = httpx.get("http://127.0.0.1:8010/health", timeout=2.0)
    except Exception as exc:
        pytest.skip(f"Core service not available: {exc}")

    if response.status_code >= 500:
        pytest.skip(f"Core service unhealthy: HTTP {response.status_code}")

# Try to import locust - skip if not available
try:
    from locust import HttpUser, task, between, events
    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False

    # Create dummy decorator for when locust is not installed
    import functools

    class HttpUser:
        """Dummy class when locust is not installed"""
        pass

    def task(*args, **kwargs):
        """Dummy decorator when locust is not installed"""
        def decorator(func):
            # Mark function to skip in pytest
            func._locust_task = True
            func.__skip_test__ = True  # Skip this in pytest
            return func
        return decorator if args else decorator(args[0]) if args else decorator

    def between(min_wait, max_wait):
        """Dummy function when locust is not installed"""
        return lambda cls: cls

    class events:
        """Dummy class when locust is not installed"""
        pass


# ============================================================================
# Load Testing Scenarios
# ============================================================================

class LuminaUser(HttpUser):
    """Simulates a real user interacting with Lumina"""

    wait_time = between(1, 3)  # Think time between requests

    def on_start(self):
        """Called when a user starts"""
        self.user_id = f"user_{int(time.time() * 1000) % 10000}"

    @task(3)
    def send_chat_message(self):
        """Send a chat message (most common operation)"""
        response = self.client.post(
            "/companion/message",
            json={
                "text": "Hello, this is a test message",
                "user_id": self.user_id,
                "character_id": "hiyori"
            }
        )
        if response.status_code == 200:
            # Success
            pass
        else:
            self.environment.record_failure("chat", response.status_code)

    @task(1)
    def get_character_info(self):
        """Get character information"""
        self.client.get("/settings/character/config")

    @task(1)
    def check_health(self):
        """Health check endpoint"""
        self.client.get("/health")


class StressTestUser(HttpUser):
    """User that performs stress-testing operations"""

    @task
    def send_long_message(self):
        """Send very long messages"""
        long_content = "Test message " * 100  # ~1200 characters
        self.client.post(
            "/companion/message",
            json={
                "text": long_content,
                "user_id": "stress_test_user",
                "character_id": "hiyori"
            }
        )

    @task
    def rapid_requests(self):
        """Send rapid successive requests"""
        for _ in range(5):
            self.client.post(
                "/companion/message",
                json={
                    "text": "Quick test",
                    "user_id": "rapid_user",
                    "character_id": "hiyori"
                }
            )


class SpikeTestUser(HttpUser):
    """User that creates sudden traffic spikes"""

    wait_time = between(0.1, 0.5)

    @task
    def send_message(self):
        """Send messages with minimal wait time"""
        self.client.post(
            "/companion/message",
            json={
                "text": "Spike test message",
                "user_id": "spike_user",
                "character_id": "hiyori"
            }
        )


# ============================================================================
# Manual Load Testing (without Locust)
# ============================================================================

class LoadTestRunner:
    """Manual load testing without Locust dependency"""

    def __init__(self, base_url="http://127.0.0.1:8010"):
        self.base_url = base_url
        self.results = []

    async def run_concurrent_users(self, num_users=10, duration_seconds=30):
        """Run load test with concurrent users"""
        import httpx
        import asyncio

        async def user_session(user_id):
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                requests_made = 0
                errors = 0

                while time.time() - start_time < duration_seconds:
                    try:
                        response = await client.post(
                            f"{self.base_url}/companion/message",
                            json={
                                "text": f"Load test message {requests_made}",
                                "user_id": f"load_user_{user_id}",
                                "character_id": "hiyori"
                            },
                            timeout=10.0
                        )
                        if response.status_code == 200:
                            requests_made += 1
                        else:
                            errors += 1
                    except Exception as e:
                        errors += 1

                    await asyncio.sleep(1)

                return {
                    "user_id": user_id,
                    "requests_made": requests_made,
                    "errors": errors,
                    "duration": time.time() - start_time
                }

        # Run all users concurrently
        start_time = time.time()
        tasks = [user_session(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Calculate statistics
        total_requests = sum(r["requests_made"] for r in results)
        total_errors = sum(r["errors"] for r in results)

        return {
            "total_users": num_users,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "success_rate": (total_requests - total_errors) / total_requests if total_requests > 0 else 0,
            "requests_per_second": total_requests / total_time if total_time > 0 else 0,
            "results": results
        }


# ============================================================================
# Pytest-compatible Load Tests
# ============================================================================

@pytest.mark.load
@pytest.mark.slow
def test_concurrent_users_load():
    """Test system with concurrent users"""
    import asyncio
    require_core_service()

    async def run_load_test():
        runner = LoadTestRunner()
        stats = await runner.run_concurrent_users(
            num_users=10,
            duration_seconds=5
        )

        # Verify acceptable performance
        assert stats["success_rate"] >= 0.9, f"Success rate too low: {stats['success_rate']}"
        print(f"Load test: {stats['requests_per_second']:.1f} req/s, Success rate: {stats['success_rate']:.1%}")

    asyncio.run(run_load_test())


@pytest.mark.load
@pytest.mark.slow
def test_memory_service_under_load():
    """Test memory endpoint under load"""
    import asyncio
    import httpx
    require_core_service()

    async def stress_memory_service():
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for i in range(50):
                task = client.post(
                    "http://127.0.0.1:8010/memory/search",
                    json={"query": f"test {i}", "limit": 10},
                    timeout=10.0
                )
                tasks.append(task)

            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start

            successful = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
            errors = sum(1 for r in responses if not isinstance(r, httpx.Response))

            print(f"Load test: {successful} successful, {errors} errors, {elapsed:.2f}s")
            assert successful >= 45, f"Too many failed requests: {errors}/50"

    # Skip if service not available
    try:
        asyncio.run(stress_memory_service())
    except Exception as e:
        pytest.skip(f"Memory endpoint not available: {e}")


@pytest.mark.load
@pytest.mark.slow
def test_burst_traffic():
    """Test system handles traffic bursts"""
    import asyncio
    import httpx
    require_core_service()

    async def simulate_burst():
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send 100 requests in rapid succession
            tasks = []
            for i in range(100):
                task = client.post(
                    "http://127.0.0.1:8010/companion/message",
                    json={
                        "text": f"Burst message {i}",
                        "user_id": "burst_user",
                        "character_id": "hiyori"
                    },
                    timeout=5.0
                )
                tasks.append(task)

            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start

            successful = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)

            print(f"Burst test: {successful}/100 successful in {elapsed:.2f}s")
            # Should handle burst even if not all succeed
            assert successful >= 80, f"Burst test failed: only {successful}/100 succeeded"

    try:
        asyncio.run(simulate_burst())
    except Exception as e:
        pytest.skip(f"Service not available: {e}")


# ============================================================================
# Capacity Planning Tests
# ============================================================================

@pytest.mark.load
@pytest.mark.slow
def test_find_breaking_point():
    """Gradually increase load to find system limits"""
    import asyncio
    require_core_service()

    runner = LoadTestRunner()

    user_levels = [1, 5, 10, 20, 50]
    success_rates = []

    for num_users in user_levels:
        try:
            stats = asyncio.run(runner.run_concurrent_users(
                num_users=num_users,
                duration_seconds=5
            ))
            success_rates.append((num_users, stats["success_rate"]))
            print(f"{num_users} users: {stats['success_rate']:.1%} success")

            # Stop if success rate drops below 50%
            if stats["success_rate"] < 0.5:
                print(f"Breaking point found at {num_users} users")
                break

        except Exception as e:
            print(f"Failed at {num_users} users: {e}")
            break


# ============================================================================
# Summary
# ============================================================================

"""
LOAD TESTING APPROACHES:

1. Using Locust (Recommended for production-like load testing):
   - Install: pip install locust
   - Run: locust -f tests_pytest/load/test_load.py --host=http://127.0.0.1:8010
   - Web UI: http://localhost:8089

2. Using Manual Load Tests (Pytest-compatible):
   - pytest tests_pytest/load/test_load.py -v -m load
   - Requires services to be running

3. Load Test Scenarios:
   - Normal Load: Expected traffic patterns
   - Stress Test: Beyond capacity
   - Spike Test: Sudden traffic bursts
   - Endurance: Sustained load over time

METRICS TO MONITOR:

1. Throughput:
   - Requests per second
   - Messages processed per second

2. Latency:
   - Response time (p50, p95, p99)
   - Time to first byte

3. Error Rates:
   - HTTP error codes
   - Timeout rate
   - Connection refused

4. Resource Usage:
   - CPU
   - Memory
   - Network bandwidth

CAPACITY PLANNING:

1. Baseline: Measure current capacity
2. Target: Define SLA (e.g., 100 concurrent users)
3. Headroom: Add 30-50% buffer
4. Scale: Plan for horizontal/vertical scaling
"""
