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
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Plugin-ID"],
        )

    async def startup(self, app: FastAPI):
        self.current_capability = load_capability(self.options.capability, self.logger)
        self.logger.info("Loaded capability: %s", self.current_capability.name)

        self._initialize_sdk()
        await self._initialize_capability(app)
        await self._start_worker_plugin_kernel()

        runtime_state_provider = self._start_status_reporter(app)
        await self._start_plugin_sync(app)
        await self._start_config_watcher(app)
        await self._start_control_client(app, runtime_state_provider)

    async def shutdown(self, app: FastAPI):
        ws_control_client = getattr(app.state, "ws_control_client", None)
        if ws_control_client:
            await ws_control_client.stop()

        if self.status_reporter:
            if asyncio.iscoroutinefunction(self.status_reporter.stop):
                await self.status_reporter.stop()
            else:
                self.status_reporter.stop()

        if self.current_capability:
            await self.current_capability.on_shutdown()

    def _initialize_sdk(self):
        try:
            from lumina import lumina

            lumina._initialize(self.container)
            self.logger.info("Lumina SDK initialized in worker mode")
        except Exception as exc:
            self.logger.warning("SDK initialization skipped: %s", exc)

    async def _initialize_capability(self, app: FastAPI):
        app_settings.set_read_only(True)
        self.container.config = app_settings
        self.current_capability.register_routes(app)
        app.state.container = self.container
        await self.current_capability.on_startup(app)

    async def _start_worker_plugin_kernel(self):
        try:
            from services.system_plugin_manager import SystemPluginManager

            worker_plugin_manager = SystemPluginManager(
                container=self.container,
                runtime_target=self.runtime_target,
            )
            await worker_plugin_manager.start()
            self.container.system_plugin_manager = worker_plugin_manager
            self.logger.info("Worker plugin kernel initialized")
        except Exception as exc:
            self.logger.warning("Worker plugin kernel init failed: %s", exc)

    def _start_status_reporter(self, app: FastAPI):
        from services.reporting.runtime_state_provider import build_runtime_state_provider
        from services.reporting.worker_reporter import WorkerStatusReporter

        worker_id = runtime_target_to_worker_id(self.runtime_target)
        runtime_state_provider = build_runtime_state_provider(
            self.current_capability.get_state_provider(),
            container=self.container,
        )

        self.status_reporter = WorkerStatusReporter(
            worker_id=worker_id,
            main_port=app_settings.network.memory_port,
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

    async def _start_plugin_sync(self, app: FastAPI):
        try:
            from services.plugin_state_sync import PluginStateSync

            manager = self.container.system_plugin_manager or getattr(
                self.container,
                self.current_capability.name,
                None,
            )
            if not manager:
                self.logger.warning(
                    "No plugin controller available for runtime %s; plugin sync skipped",
                    self.runtime_target,
                )
                return

            sync_service = PluginStateSync(
                manager,
                worker_id=app.state.worker_id,
                expected_target=self.runtime_target,
                reporter=self.status_reporter,
            )
            self.container.plugin_sync = sync_service
            app.state.sync_task = asyncio.create_task(sync_service.start())
            self.logger.info("Distributed plugin state sync started")
        except Exception as exc:
            self.logger.error("Failed to start plugin sync: %s", exc, exc_info=True)

    async def _start_config_watcher(self, app: FastAPI):
        try:
            from services.infra.config_watcher import ConfigWatcherService

            watcher = ConfigWatcherService()
            self.container.set_config_watcher(watcher)
            app.state.config_watcher_task = asyncio.create_task(watcher.start())
            self.logger.info("Config watcher activated")
        except Exception as exc:
            self.logger.error("Failed to start config watcher: %s", exc)

    async def _start_control_client(self, app: FastAPI, runtime_state_provider: Any):
        try:
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
        except Exception as exc:
            self.logger.warning(
                "WebSocket control client failed; falling back to HTTP: %s",
                exc,
            )

    def _handle_config_update(self, payload):
        self.logger.info("Config update received: %s", payload.section)
        app_settings.reload()

        plugin_id = payload.data.get("plugin_id") if payload.data else None
        manager = getattr(self.container, self.current_capability.name, None)
        if not plugin_id or not manager:
            return

        drivers = getattr(manager, "drivers", {})
        driver = drivers.get(plugin_id) if isinstance(drivers, dict) else None
        if not driver or not hasattr(driver, "config"):
            return

        settings = payload.data.get("settings")
        if isinstance(settings, dict):
            driver.config.update(settings)
            return

        key = payload.data.get("key")
        if key is not None:
            driver.config[key] = payload.data.get("value")

    async def _handle_lifecycle(self, payload):
        self.logger.info("Lifecycle command: %s -> %s", payload.action, payload.target_id)

        plugin_manager = self.container.system_plugin_manager
        if plugin_manager and plugin_manager.get_manifest(payload.target_id):
            if payload.action == "disable":
                await plugin_manager.disable_plugin(payload.target_id)
            elif payload.action == "enable":
                await plugin_manager.enable_plugin(payload.target_id)
            return

        manager = getattr(self.container, self.current_capability.name, None)
        if not manager:
            return
        if payload.action == "disable" and hasattr(manager, "disable_plugin"):
            await manager.disable_plugin(payload.target_id)
        elif payload.action == "enable" and hasattr(manager, "enable_plugin"):
            await manager.enable_plugin(payload.target_id)
