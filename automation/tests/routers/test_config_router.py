import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from routers.config import health_check
from services.companion.context import CompanionContextResolver


class FakeSoulService:
    def get_active_character_id(self) -> str:
        return "sakura"


@pytest.mark.anyio
async def test_health_check_reports_active_soul_character():
    response = await health_check(context_resolver=CompanionContextResolver(FakeSoulService()))

    assert response == {"status": "healthy", "active_character_id": "sakura"}
