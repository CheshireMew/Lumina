"""Export Lumina's OpenAPI schema without starting a backend process."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "python_backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    from logger_setup import request_id_ctx, setup_logger
    from core.api.app_factory import create_app
    from services.container import ServiceContainer

    app = create_app(
        setup_logger("openapi_export.log"),
        request_id_ctx,
        ServiceContainer(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
