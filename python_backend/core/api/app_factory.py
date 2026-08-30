import logging
import uuid

from fastapi import FastAPI, WebSocket
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app_config import config as app_settings
from routers import gateway
from routers import memory
from routers import runtime as runtime_router
from routers import settings_llm
from routers import character
from routers import companion
from routers import vision_routes
from routers import stt_routes
from routers import tts_routes
from routers import metrics as metrics_router
from routers.voiceprint import router as voiceprint_router
from services.lifecycle import lifespan
from services.middleware.metrics_middleware import MetricsMiddleware
from core.api.assets import mount_builtin_assets

logger = logging.getLogger("AppFactory")

def create_app(logger, request_id_ctx, container) -> FastAPI:
    app = FastAPI(
        title="Lumina Backend API",
        description="Lumina desktop backend",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.state.services = container

    _configure_middleware(app, logger, request_id_ctx)
    _configure_exception_handlers(app, logger)
    _configure_routes(app)
    _configure_root(app)
    return app


def _configure_middleware(app: FastAPI, logger, request_id_ctx) -> None:
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
            "X-Provider-ID",
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
    app.include_router(companion.router)
    app.include_router(settings_llm.router)
    app.include_router(settings_llm.models_router)
    app.include_router(memory.router, prefix="/memory")
    app.include_router(runtime_router.router)
    app.include_router(voiceprint_router)
    app.include_router(vision_routes.router)
    app.include_router(character.router)
    app.include_router(stt_routes.router)
    app.include_router(tts_routes.router)
    app.include_router(metrics_router.router)
    mount_builtin_assets(app, logger)

    @app.websocket("/ws/worker-control")
    async def worker_control_websocket(websocket: WebSocket):
        hub = websocket.app.state.services.get_worker_control_hub()
        await hub.handle_connection(websocket)


def _configure_root(app: FastAPI) -> None:
    @app.get("/")
    async def root():
        return {
            "service": "Lumina Backend API",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "runtime": "/runtime/health, /runtime/network, /runtime/capabilities",
                "settings": "/settings/llm/runtime",
                "companion": "/companion/message",
                "memory": "/memory/add, /memory/search, /memory/search/hybrid, /memory/all, /memory/inspection",
                "character": "/settings/character/*",
                "capabilities": "/capabilities/*",
            },
        }
