import asyncio
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional

from .health_probe import HealthProbe
from .worker_launcher import WorkerLauncher
from .worker_supervisor import RestartPolicy, WorkerProcess, WorkerSupervisor

logger = logging.getLogger("ProcessManager")


class ProcessManager:
    def __init__(self, worker_runtime_registry):
        if worker_runtime_registry is None:
            raise ValueError("ProcessManager requires WorkerRuntimeRegistry")

        self.workers: Dict[str, Any] = {}
        self.registry: Dict[str, dict] = {}
        self._shutdown_event = asyncio.Event()
        self._managed_scripts: Dict[str, Optional[str]] = {}
        self.worker_runtime_registry = worker_runtime_registry
        self.health_probe = HealthProbe()
        self.launcher = WorkerLauncher(worker_runtime_registry)
        self.supervisor = WorkerSupervisor(
            workers=self.workers,
            shutdown_event=self._shutdown_event,
            launcher=self.launcher,
        )

    async def start_supervisor(self):
        await self.supervisor.start()

    def register_service_def(
        self,
        service_id: str,
        port: int,
        script: str = "backend_launcher.py",
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ):
        self.registry[service_id] = {
            "port": port,
            "script": script,
            "args": args or [],
            "cwd": cwd,
            "health_path": "/health",
        }

    def set_health_path(self, service_id: str, path: str):
        if service_id in self.registry:
            self.registry[service_id]["health_path"] = path

    def start_worker(
        self,
        worker_id: str,
        script_name: Optional[str] = None,
        args: Optional[List[str]] = None,
        policy: RestartPolicy = RestartPolicy.ALWAYS,
    ):
        if self._shutdown_event.is_set():
            logger.info(f"Skip starting {worker_id}: ProcessManager is shutting down.")
            return False

        if not self._is_worker_runtime_ready(worker_id):
            logger.info(f"Skip starting {worker_id}: worker runtime unavailable.")
            return False

        if self.is_running(worker_id):
            logger.info(f"Worker {worker_id} is already running.")
            return True

        service_def = self.registry.get(worker_id)
        target_port = service_def["port"] if service_def else None
        target_script = service_def["script"] if service_def else script_name
        target_args = service_def["args"] if service_def else args
        target_cwd = service_def.get("cwd") if service_def else None

        if not target_script:
            logger.error(
                f"Cannot start {worker_id}: No registry definition and no script provided."
            )
            return False

        if target_port and self._attach_external_if_reachable(
            worker_id,
            target_port,
            service_def.get("health_path", "/health") if service_def else "/health",
        ):
            return True

        if self._shutdown_event.is_set():
            logger.info(f"Skip launching {worker_id}: ProcessManager is shutting down.")
            return False

        try:
            launch_config = self.launcher.build_launch_config(
                worker_id=worker_id,
                script_name=target_script,
                args=target_args,
                cwd=target_cwd,
            )
            if not launch_config:
                return False

            display_name = launch_config.get("display_name", target_script)
            logger.info(f"Spawning Worker: {worker_id} ({display_name})...")
            proc = self.launcher.launch(worker_id, launch_config)

            self.workers[worker_id] = WorkerProcess(
                process=proc,
                start_time=time.time(),
                policy=policy,
                launch_config=launch_config,
            )
            self._managed_scripts[worker_id] = target_script

            logger.info(f"Worker {worker_id} started (PID: {proc.pid})")
            return True
        except Exception as e:
            logger.error(f"Failed to start worker {worker_id}: {e}")
            return False

    def _is_worker_runtime_ready(self, worker_id: str) -> bool:
        if not worker_id.startswith("worker:"):
            return True

        capability = worker_id.split(":", 1)[1]
        definition = self.worker_runtime_registry.runtime_for_capability(capability)
        if not definition:
            return True

        snapshot = self.worker_runtime_registry.resolve(definition.id)
        return bool(snapshot and snapshot.status == "ready" and snapshot.entry_executable is not None)

    def _attach_external_if_reachable(
        self,
        worker_id: str,
        port: int,
        health_path: str,
    ) -> bool:
        is_alive, probe_kind = self.health_probe.is_service_reachable(
            port,
            health_path,
        )
        if not is_alive:
            return False

        if probe_kind == "http":
            logger.info(
                f"Service {worker_id} detected via HTTP Probe ({port}{health_path})."
            )
        else:
            logger.info(
                f"Service {worker_id} detected via TCP Port {port} (HTTP failed)."
            )

        worker = WorkerProcess(None, time.time())
        worker.is_external = True
        self.workers[worker_id] = worker
        return True

    def stop_worker(self, worker_id: str):
        if worker_id not in self.workers:
            return

        logger.info(f"Stopping worker {worker_id}...")
        worker = self.workers[worker_id]

        if hasattr(worker, "stop") and asyncio.iscoroutinefunction(worker.stop):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(worker.stop())
                logger.info(f"Scheduled async stop for {worker_id}")
            except RuntimeError:
                pass
            finally:
                del self.workers[worker_id]
            return

        try:
            if getattr(worker, "is_external", False):
                logger.warning(
                    f"Worker {worker_id} is external. Cannot stop it via ProcessManager."
                )
            elif hasattr(worker, "process") and worker.process:
                worker.process.terminate()
                try:
                    worker.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Worker {worker_id} ignored terminate, killing...")
                    worker.process.kill()
            else:
                logger.warning(f"Worker {worker_id} has no process handle.")
        except Exception as e:
            logger.error(f"Error stopping worker {worker_id}: {e}")
        finally:
            if worker_id in self.workers:
                del self.workers[worker_id]
            logger.info(f"Worker {worker_id} stopped.")

    def is_running(self, worker_id: str) -> bool:
        worker = self.workers.get(worker_id)
        if not worker:
            return False

        if not isinstance(worker, WorkerProcess):
            return True

        if worker.is_external:
            return self._is_external_running(worker_id)

        if not worker.process:
            return False

        status = self._poll_process(worker_id, worker.process)
        if status is not None:
            if worker.policy == RestartPolicy.NEVER:
                logger.info(f"Worker {worker_id} exited with code {status}")
                del self.workers[worker_id]
            return False

        return True

    def _is_external_running(self, worker_id: str) -> bool:
        port, health_path = self._resolve_health_target(worker_id)
        if not port:
            return True

        is_alive, _ = self.health_probe.is_service_reachable(port, health_path)
        if is_alive:
            return True

        logger.info(f"External service {worker_id} disappeared from port {port}.")
        del self.workers[worker_id]
        return False

    def _resolve_health_target(self, worker_id: str) -> tuple[Optional[int], str]:
        service_def = self.registry.get(worker_id)
        if service_def:
            return service_def.get("port"), service_def.get("health_path", "/health")

        return None, "/health"

    def _poll_process(self, worker_id: str, proc) -> Optional[int]:
        if hasattr(proc, "poll"):
            return proc.poll()
        if hasattr(proc, "returncode"):
            return proc.returncode

        logger.warning(f"Unknown process type in worker {worker_id}: {type(proc)}")
        return None

    def get_active_workers(self) -> List[str]:
        active = []
        for worker_id in list(self.workers.keys()):
            if self.is_running(worker_id):
                active.append(worker_id)
        return active

    async def shutdown_all(self):
        logger.info("ProcessManager shutting down all workers...")
        self._shutdown_event.set()
        for worker_id in list(self.workers.keys()):
            self.stop_worker(worker_id)
