import uuid

from fastapi import FastAPI, WebSocket
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app_config import config as app_settings
from routers import gateway
from routers import memory
from routers import soul
from routers import config as config_router
from routers import runtime as runtime_router
from routers import llm_mgmt
from routers import character
from routers import completions
from routers import admin
from routers import debug as debug_router
from routers import vision_routes
from routers import stt_routes
from routers import tts_routes
from routers import metrics as metrics_router
from routers.voiceprint import router as voiceprint_router
from services.container import services as service_instance
from services.infra.worker_control_hub import get_worker_control_hub
from services.lifecycle import lifespan
from services.middleware.metrics_middleware import MetricsMiddleware


RESTRICTED_PREFIXES = [
    "/debug",
    "/llm-mgmt",
    "/admin",
]


def create_app(logger, request_id_ctx) -> FastAPI:
    app = FastAPI(
        title="Lumina Backend API",
        description="Lumina desktop backend",
        version="2.0.0",
        lifespan=lifespan,
    )

    _configure_middleware(app, logger, request_id_ctx)
    _configure_exception_handlers(app, logger)
    _configure_routes(app)
    _mount_capability_resources(app, logger)
    _configure_root(app)
    return app


def _configure_middleware(app: FastAPI, logger, request_id_ctx) -> None:
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        path = request.url.path
        client_host = request.client.host if request.client else ""

        if any(path.startswith(prefix) for prefix in RESTRICTED_PREFIXES):
            if client_host not in ["127.0.0.1", "::1", "localhost"]:
                logger.warning(f"Blocked external access to {path} from {client_host}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access Denied: Localhost only."},
                )

        return await call_next(request)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)

    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1",
            "http://localhost",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "tauri://localhost",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Plugin-ID",
        ],
    )


def _configure_exception_handlers(app: FastAPI, logger) -> None:
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning(f"⚠️ Bad Request on {request.url}: {exc}")
        return JSONResponse(
            status_code=400,
            content={"message": "Bad Request", "detail": str(exc)},
        )

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
        if exc.status_code >= 500 and not app_settings.is_dev:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "message": "Internal Server Error",
                    "detail": "Internal Error",
                },
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": "Error", "detail": exc.detail},
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        logger.warning(f"🚫 Forbidden Access on {request.url}: {exc}")
        return JSONResponse(
            status_code=403,
            content={"message": "Forbidden", "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.critical(f"🔥 Global Panic on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal Server Error",
                "detail": str(exc) if app_settings.is_dev else "Internal Error",
            },
        )


def _configure_routes(app: FastAPI) -> None:
    app.include_router(gateway.router)
    app.include_router(llm_mgmt.router)
    app.include_router(llm_mgmt.models_router)
    app.include_router(completions.router)
    app.include_router(admin.router)
    app.include_router(debug_router.router)
    app.include_router(config_router.router)
    app.include_router(soul.router)
    app.include_router(memory.router, prefix="/memory")
    app.include_router(runtime_router.router)
    app.include_router(voiceprint_router)
    app.include_router(vision_routes.router)
    app.include_router(character.router)
    app.include_router(stt_routes.router)
    app.include_router(tts_routes.router)
    app.include_router(metrics_router.router)

    @app.websocket("/ws/worker-control")
    async def worker_control_websocket(websocket: WebSocket):
        hub = get_worker_control_hub()
        await hub.handle_connection(websocket)


def _mount_capability_resources(app: FastAPI, logger) -> None:
    package_registry = getattr(service_instance, "capability_package_registry", None)
    if not package_registry:
        return

    for route, directory in package_registry.static_mounts():
        route_name = route.strip("/").replace("/", ".")
        app.mount(route, StaticFiles(directory=str(directory)), name=route_name)
        logger.info("Mounted capability resource %s from %s", route, directory)


def _configure_root(app: FastAPI) -> None:
    @app.get("/")
    async def root():
        return {
            "service": "Lumina Backend API",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "config": "/configure, /health",
                "memory": "/memory/add, /memory/search, /memory/search/hybrid, /memory/all",
                "character": "/character/*",
                "soul": "/soul/*",
            },
        }
