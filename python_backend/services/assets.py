from __future__ import annotations

import os
from pathlib import Path

from app_config import APP_ROOT


def get_builtin_assets_root() -> Path:
    env_root = os.environ.get("LUMINA_ASSETS_DIR")
    if env_root:
        return Path(env_root).resolve()

    return (APP_ROOT / "public").resolve()


def _normalize_live2d_model(model: str) -> str:
    normalized = model.strip().strip("/\\")
    if not normalized:
        raise ValueError("Live2D model name is required")
    if "/" in normalized or "\\" in normalized or normalized in {".", ".."}:
        raise ValueError("Live2D model name must be a single directory name")
    return normalized


def live2d_model_route(model: str) -> str:
    normalized = _normalize_live2d_model(model)
    return f"/assets/live2d/{normalized}/{normalized}.model3.json"


def cubism_core_route() -> str:
    return "/assets/libs/live2dcubismcore.min.js"


def live2d_renderer_route() -> str:
    return "/assets/libs/pixi-live2d-display-cubism4.min.js"


def absolute_asset_url(base_url: str, route: str) -> str:
    return f"{base_url.rstrip('/')}/{route.lstrip('/')}"


def list_live2d_models() -> list[dict[str, str | None]]:
    live2d_root = get_builtin_assets_root() / "live2d"
    if not live2d_root.exists():
        return []

    models = []
    seen = set()
    for model_path in sorted(live2d_root.rglob("*.model3.json")):
        name = model_path.parent.name
        if name in seen:
            continue
        seen.add(name)
        route = f"/assets/live2d/{model_path.relative_to(live2d_root).as_posix()}"
        models.append(
            {
                "name": name,
                "path": route,
                "type": "live2d",
                "thumbnail": _thumbnail_route(live2d_root, model_path),
                "availability": "ready",
            }
        )
    return models


def _thumbnail_route(root: Path, model_path: Path) -> str | None:
    for candidate in (
        "thumbnail.png",
        "thumbnail.jpg",
        "preview.png",
        "preview.jpg",
        f"{model_path.stem}.png",
        f"{model_path.stem}.jpg",
        "icon.png",
    ):
        thumb_path = model_path.parent / candidate
        if thumb_path.exists():
            return f"/assets/live2d/{thumb_path.relative_to(root).as_posix()}"
    return None
