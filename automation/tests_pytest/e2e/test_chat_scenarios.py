"""
End-to-end scenario tests for Lumina companion interactions.

These tests target the companion runtime boundary. They intentionally do not
exercise removed OpenAI-compatible completion, plugin discovery, or multi-
character product flows.
"""
import asyncio
import sys
from pathlib import Path

import httpx
import pytest


PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

SERVICES = {
    "memory": "http://127.0.0.1:8010",
    "stt": "http://127.0.0.1:8010",
    "tts": "http://127.0.0.1:8766",
}


def companion_url() -> str:
    return f"{SERVICES['memory']}/companion/message"


def companion_payload(
    text: str,
    *,
    session_id: int = 0,
    user_id: str | None = None,
    model: str = "gpt-4o-mini",
) -> dict:
    return {
        "text": text,
        "session_id": session_id,
        "user_id": user_id,
        "model": model,
    }


@pytest.mark.e2e
@pytest.mark.anyio
async def test_basic_companion_message_flow():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            companion_url(),
            json=companion_payload("Hello, how are you?"),
        )

        assert response.status_code == 200
        assert response.json()["content"]


@pytest.mark.e2e
@pytest.mark.anyio
async def test_multi_turn_companion_session():
    async with httpx.AsyncClient(timeout=60.0) as client:
        for user_message in [
            "Hi there!",
            "What's your name?",
            "Tell me about yourself",
        ]:
            response = await client.post(
                companion_url(),
                json=companion_payload(user_message, session_id=42),
            )

            assert response.status_code == 200
            assert response.json()["content"]


@pytest.mark.e2e
@pytest.mark.anyio
async def test_companion_memory_retrieval_path():
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(
            companion_url(),
            json=companion_payload(
                "My favorite color is blue",
                session_id=77,
                user_id="e2e_memory_test",
            ),
        )

        response = await client.post(
            companion_url(),
            json=companion_payload(
                "What is my favorite color?",
                session_id=77,
                user_id="e2e_memory_test",
            ),
        )

        assert response.status_code == 200
        assert response.json()["content"]


@pytest.mark.e2e
@pytest.mark.anyio
async def test_companion_rejects_blank_input():
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test_input in ["", "   "]:
            response = await client.post(
                companion_url(),
                json=companion_payload(test_input),
            )

            assert response.status_code == 400


@pytest.mark.e2e
@pytest.mark.anyio
async def test_voice_runtime_health_paths():
    async with httpx.AsyncClient(timeout=60.0) as client:
        stt_health = await client.get(f"{SERVICES['stt']}/health")
        if stt_health.status_code != 200:
            pytest.skip("STT service not available")

        tts_health = await client.get(f"{SERVICES['tts']}/health")
        if tts_health.status_code != 200:
            pytest.skip("TTS service not available")

        assert stt_health.status_code == 200
        assert tts_health.status_code == 200


@pytest.mark.e2e
@pytest.mark.anyio
async def test_concurrent_companion_users():
    async def chat_for_user(user_id: str):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                companion_url(),
                json=companion_payload(
                    "Hello from multiple users!",
                    user_id=user_id,
                ),
            )
            return response.status_code == 200

    user_ids = [f"e2e_concurrent_user_{i}" for i in range(5)]
    results = await asyncio.gather(*[chat_for_user(uid) for uid in user_ids])

    assert all(results), f"Some concurrent requests failed: {results}"


@pytest.mark.e2e
@pytest.mark.anyio
@pytest.mark.slow
async def test_long_companion_session():
    async with httpx.AsyncClient(timeout=120.0) as client:
        responses = []
        for msg in [
            "Let's have a long conversation",
            "Tell me about your hobbies",
            "What do you like to do?",
            "That's interesting",
            "Can you tell me more?",
            "How does that make you feel?",
            "I see",
        ]:
            response = await client.post(
                companion_url(),
                json=companion_payload(msg, session_id=91),
            )
            assert response.status_code == 200
            responses.append(response.json()["content"])

        assert len(responses) == 7
        assert all(responses)


@pytest.mark.e2e
@pytest.mark.anyio
async def test_service_health_endpoints():
    async with httpx.AsyncClient(timeout=10.0) as client:
        health_checks = {}

        for service_name, url in SERVICES.items():
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                health_checks[service_name] = response.status_code == 200
            except Exception:
                health_checks[service_name] = False

        assert health_checks.get("memory", False), "Memory service must be available"


@pytest.fixture(scope="session", autouse=True)
async def verify_services():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{SERVICES['memory']}/health")
            if response.status_code != 200:
                pytest.skip("Memory service not available. Run: npm run dev")
        except Exception:
            pytest.skip("Cannot connect to services. Run: npm run dev")
