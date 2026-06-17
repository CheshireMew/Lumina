from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_capability_resources(app: FastAPI, logger, package_registry) -> None:
    mounted_routes = getattr(app.state, "capability_resource_mounts", set())

    for route, directory in package_registry.static_mounts():
        if route in mounted_routes:
            continue

        route_name = route.strip("/").replace("/", ".")
        app.mount(route, StaticFiles(directory=str(directory)), name=route_name)
        mounted_routes.add(route)
        logger.info("Mounted capability resource %s from %s", route, directory)

    app.state.capability_resource_mounts = mounted_routes
