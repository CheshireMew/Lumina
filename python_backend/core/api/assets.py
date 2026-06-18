from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from services.assets import get_builtin_assets_root


def mount_builtin_assets(app: FastAPI, logger) -> None:
    root = get_builtin_assets_root()

    for route, directory in (
        ("/assets/live2d", root / "live2d"),
        ("/assets/libs", root / "libs"),
    ):
        if not directory.exists():
            logger.warning("Builtin asset directory missing for %s: %s", route, directory)
            continue

        route_name = route.strip("/").replace("/", ".")
        app.mount(route, StaticFiles(directory=str(directory)), name=route_name)
        logger.info("Mounted builtin assets %s from %s", route, directory)
