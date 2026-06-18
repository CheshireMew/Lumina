import asyncio
import uuid
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app_config import config as app_settings
from core.interfaces.capability import IWorkerCapability
from core.runtime import runtime_target_for_capability, runtime_target_to_worker_id
from logger_setup import request_id_ctx, session_id_ctx, setup_logger
from services.container import ServiceContainer

from .loader import load_capability, resolve_worker_port
from .types import WorkerRuntimeOptions


class WorkerRuntimeHost:
    def __init__(
        self,
        options: WorkerRuntimeOptions,
        container: ServiceContainer,
    ):
        self.options = options
        self.container = container
        self.logger = setup_logger(f"{options.capability}_server.log")
        self.current_capability: Optional[IWorkerCapability] = None
        self.status_reporter = None

    @property
    def runtime_target(self) -> str:
        return self.options.runtime_target or runtime_target_for_capability(self.options.capability)

    @property
    def listen_port(self) -> int:
        return resolve_worker_port(app_settings, self.options)

    def build_app(self) -> FastAPI:
        app = FastAPI(title=f"Lumina {self.options.capability.upper()} Service")
        self._configure_middleware(app)

        @app.get("/health")
        async def health_check():
            capability_name = self.current_capability.name if self.current_capability else "none"
            return {
                "status": "ok",
                "service": self.options.capability,
                "capability": capability_name,
            }

        @app.on_event("startup")
        async def startup_event():
            await self.startup(app)

        @app.on_event("shutdown")
        async def shutdown_event():
            await self.shutdown(app)

        return app

    def _configure_middleware(self, app: FastAPI):
        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next):
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
            session_id = request.headers.get("X-Session-ID", "-")

            token_rid = request_id_ctx.set(request_id)
            token_sid = session_id_ctx.set(session_id)
            try:
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Session-ID"] = session_id
                return response
            finally:
                request_id_ctx.reset(token_rid)
                session_id_ctx.reset(token_sid)

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
                "electron://altair",
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Provider-ID"],
        )

    async def startup(self, app: FastAPI):
        self.current_capability = load_capability(self.options.capability, self.logger)
        self.logger.info("Loaded capability: %s", self.current_capability.name)

        await self._initialize_capability(app)

        runtime_state_provider = self._start_status_reporter(app)
        await self._start_config_watcher(app)
        await self._start_control_client(app, runtime_state_provider)

    async def shutdown(self, app: FastAPI):
        ws_control_client = getattr(app.state, "ws_control_client", None)
        if ws_control_client:
            await ws_control_client.stop()

        config_watcher = getattr(app.state, "config_watcher", None)
        if config_watcher:
            config_watcher.stop()

        config_watcher_task = getattr(app.state, "config_watcher_task", None)
        if config_watcher_task:
            config_watcher_task.cancel()
            try:
                await config_watcher_task
            except asyncio.CancelledError:
                pass

        if self.status_reporter:
            if asyncio.iscoroutinefunction(self.status_reporter.stop):
                await self.status_reporter.stop()
            else:
                self.status_reporter.stop()

        if self.current_capability:
            await self.current_capability.on_shutdown()

    async def _initialize_capability(self, app: FastAPI):
        self._initialize_container_services()
        app_settings.set_read_only(True)
        self.current_capability.register_routes(app)
        app.state.container = self.container
        await self.current_capability.on_startup(app)

    def _initialize_container_services(self):
        from core.worker_runtimes import WorkerRuntimeRegistry
        from core.events import init_event_bus

        self.container.set_config(app_settings)
        self.container.set_event_bus(init_event_bus())
        self.container.set_worker_runtime_registry(WorkerRuntimeRegistry())

    def _start_status_reporter(self, app: FastAPI):
        from services.reporting.runtime_state_provider import build_runtime_state_provider
        from services.reporting.worker_reporter import WorkerStatusReporter

        worker_id = runtime_target_to_worker_id(self.runtime_target)
        runtime_state_provider = build_runtime_state_provider(
            self.current_capability.get_state_provider(),
        )

        self.status_reporter = WorkerStatusReporter(
            worker_id=worker_id,
            state_provider=runtime_state_provider,
            interval=90,
            host=self.options.host,
            port=self.listen_port,
        )
        self.status_reporter.start()

        app.state.reporter = self.status_reporter
        app.state.worker_id = worker_id
        app.state.runtime_target = self.runtime_target

        self.logger.info(
            "Worker status reporter activated at %s:%s",
            self.options.host,
            self.listen_port,
        )
        return runtime_state_provider

    async def _start_config_watcher(self, app: FastAPI):
        from services.infra.config_watcher import ConfigWatcherService

        watcher = ConfigWatcherService()
        self.container.set_config_watcher(watcher)
        app.state.config_watcher = watcher
        app.state.config_watcher_task = asyncio.create_task(watcher.start())
        self.logger.info("Config watcher activated")

    async def _start_control_client(self, app: FastAPI, runtime_state_provider: Any):
        from services.infra.worker_control_client import WorkerControlClient

        ws_client = WorkerControlClient(
            worker_id=app.state.worker_id,
            worker_type=self.current_capability.name,
            runtime_target=self.runtime_target,
            main_host="127.0.0.1",
            main_port=app_settings.network.memory_port,
            worker_port=self.listen_port,
            heartbeat_interval=15,
            status_provider=runtime_state_provider,
        )

        ws_client.on_config_update(self._handle_config_update)
        ws_client.on_lifecycle(self._handle_lifecycle)
        ws_client.start()

        app.state.ws_control_client = ws_client
        self.logger.info("WebSocket control client activated")

    def _handle_config_update(self, payload):
        self.logger.info("Config update received: %s", payload.section)
        app_settings.reload()

        provider_id = payload.data.get("provider_id") if payload.data else None
        if not provider_id:
            return

        manager = self._get_provider_manager()
        if not manager or not manager.has_driver(provider_id):
            return

        settings = payload.data.get("settings")
        if isinstance(settings, dict):
            for key, value in settings.items():
                manager.update_driver_config(provider_id, key, value)
            return

        key = payload.data.get("key")
        if key is not None:
            manager.update_driver_config(provider_id, key, payload.data.get("value"))

    async def _handle_lifecycle(self, payload):
        self.logger.info("Lifecycle command: %s -> %s", payload.action, payload.target_id)

        manager = self._get_provider_manager()
        if not manager or not manager.has_driver(payload.target_id):
            return

        if payload.action == "disable":
            await manager.disable_provider(payload.target_id)
        elif payload.action == "enable":
            await manager.enable_provider(payload.target_id)

    def _get_provider_manager(self):
        if self.options.capability == "stt" and self.container.has_service("stt"):
            return self.container.get_stt()
        if self.options.capability == "tts" and self.container.has_service("tts"):
            return self.container.get_tts()
        if self.options.capability == "vision" and self.container.has_service("vision"):
            return self.container.get_vision()
        return None
