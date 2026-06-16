import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from memory.core import MemoryService
from memory.factory import MemoryDriverFactory


MEMORY_CONFIG = {
    "provider": "driver.memory.postgres",
    "postgres": {
        "host": "127.0.0.1",
        "port": 5432,
        "user": "lumina",
        "password": "",
        "database": "lumina",
    },
}


@pytest.fixture
def memory_service():
    with patch("memory.factory.MemoryDriverFactory.create_driver") as mock_factory:
        driver = MagicMock()
        driver.id = "driver.memory.test"
        driver.connect = AsyncMock()
        driver.close = AsyncMock()
        driver.create = AsyncMock(return_value="msg_123")
        driver.query = AsyncMock(return_value=[])
        mock_factory.return_value = driver

        svc = MemoryService(driver=driver, character_id="test_char")
        return svc, driver


@pytest.mark.anyio
async def test_memory_service_init(memory_service):
    svc, driver = memory_service

    assert svc.character_id == "test_char"
    assert svc.driver is driver
    assert svc.driver_id == "driver.memory.test"
    assert svc.vector_store.driver is driver


@pytest.mark.anyio
async def test_memory_service_connect_delegates_to_driver(memory_service):
    svc, driver = memory_service

    await svc.connect()

    driver.connect.assert_awaited_once()


@pytest.mark.anyio
async def test_replace_driver_closes_existing_and_syncs_vector_store(memory_service):
    svc, old_driver = memory_service
    next_driver = MagicMock()
    next_driver.id = "driver.memory.next"
    next_driver.close = AsyncMock()

    await svc.replace_driver(next_driver)

    old_driver.close.assert_awaited_once()
    assert svc.driver is next_driver
    assert svc.driver_id == "driver.memory.next"
    assert svc.vector_store.driver is next_driver
    assert svc.available is True


@pytest.mark.anyio
async def test_log_conversation_delegation(memory_service):
    svc, driver = memory_service
    svc.encoder = None

    result = await svc.log_conversation("test_char", "hello world")

    assert result == "msg_123"
    driver.create.assert_awaited_once()
    args, _ = driver.create.call_args
    assert args[0] == "conversation_log"
    assert args[1]["narrative"] == "hello world"


@pytest.mark.anyio
async def test_retrieve_context_flow(memory_service):
    svc, _ = memory_service
    mock_encoder = MagicMock(return_value=[0.1, 0.2])
    svc.set_encoder(mock_encoder)
    svc.search_hybrid = AsyncMock(return_value=[{"content": "memory 1"}, {"content": "memory 2"}])

    context = await svc.retrieve_context("query test", character_id="test_char")

    assert "memory 1" in context
    assert "memory 2" in context
    svc.search_hybrid.assert_awaited_once()


def test_memory_driver_factory_returns_configured_driver_only():
    postgres_driver = MagicMock()
    postgres_driver.id = "driver.memory.postgres"
    postgres_driver.name = "Postgres"
    other_driver = MagicMock()
    other_driver.id = "driver.memory.other"
    other_driver.name = "Other"

    with (
        patch("memory.factory.os.path.exists", return_value=True),
        patch("memory.factory.os.path.isdir", return_value=True),
        patch("memory.factory.os.listdir", return_value=["memory_postgres"]),
        patch(
            "memory.factory.DriverPluginLoader.load_plugins",
            return_value=[other_driver, postgres_driver],
        ),
    ):
        driver = MemoryDriverFactory.create_driver(
            "driver.memory.postgres",
            driver_config=MEMORY_CONFIG,
        )

    assert driver is postgres_driver
    postgres_driver.load_config.assert_called_once_with(MEMORY_CONFIG)


def test_memory_driver_factory_rejects_missing_configured_driver():
    other_driver = MagicMock()
    other_driver.id = "driver.memory.other"
    other_driver.name = "Other"

    with (
        patch("memory.factory.os.path.exists", return_value=True),
        patch("memory.factory.os.path.isdir", return_value=True),
        patch("memory.factory.os.listdir", return_value=["memory_postgres"]),
        patch(
            "memory.factory.DriverPluginLoader.load_plugins",
            return_value=[other_driver],
        ),
    ):
        with pytest.raises(ImportError, match="driver.memory.postgres"):
            MemoryDriverFactory.create_driver("driver.memory.postgres")


def test_memory_service_requires_explicit_driver():
    with pytest.raises(ValueError, match="explicit memory driver"):
        MemoryService(driver=None)
