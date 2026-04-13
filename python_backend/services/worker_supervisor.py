import asyncio
import logging
import time
from enum import Enum
from typing import Dict, Optional

from .worker_launcher import WorkerLauncher

logger = logging.getLogger("WorkerSupervisor")


class RestartPolicy(str, Enum):
    ALWAYS = "always"
    ON_FAILURE = "on_failure"
    NEVER = "never"


class WorkerProcess:
    def __init__(
        self,
        process,
        start_time: float,
        policy: RestartPolicy = RestartPolicy.ALWAYS,
        launch_config: Optional[Dict] = None,
    ):
        self.process = process
        self.start_time = start_time
        self.last_heartbeat = start_time
        self.is_external = False
        self.policy = policy
        self.launch_config = launch_config or {}
        self.restart_count = 0
        self.next_restart_time = 0.0
        self.is_dead = False


class WorkerSupervisor:
    def __init__(
        self,
        workers: Dict[str, object],
        shutdown_event: asyncio.Event,
        launcher: WorkerLauncher,
    ):
        self.workers = workers
        self.shutdown_event = shutdown_event
        self.launcher = launcher
        self._task = None

    async def start(self) -> None:
        if self._task:
            return
        self._task = asyncio.create_task(self._supervisor_loop())
        logger.info("Supervisor activated.")

    async def _supervisor_loop(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                now = time.time()
                for worker_id in list(self.workers.keys()):
                    worker = self.workers.get(worker_id)
                    if not isinstance(worker, WorkerProcess):
                        continue

                    if worker.is_dead:
                        if now >= worker.next_restart_time:
                            await self.restart_worker(worker_id, worker)
                        continue

                    if worker.process:
                        ret = worker.process.poll()
                        if ret is not None:
                            self._schedule_restart(worker_id, worker, ret, now)
            except Exception as e:
                logger.error(f"Supervisor Loop Error: {e}")

            await asyncio.sleep(1.0)

    def _schedule_restart(
        self,
        worker_id: str,
        worker: WorkerProcess,
        return_code: int,
        now: float,
    ) -> None:
        logger.warning(f"Worker {worker_id} exited with code {return_code}")
        if worker.policy == RestartPolicy.NEVER:
            logger.info(f"Worker {worker_id} policy is NEVER. Removing.")
            self.workers.pop(worker_id, None)
            return

        worker.is_dead = True
        worker.restart_count += 1
        backoff = min(30, 2 ** (worker.restart_count - 1))
        worker.next_restart_time = now + backoff
        logger.info(
            f"Worker {worker_id} scheduled for restart in {backoff}s "
            f"(Attempt {worker.restart_count})"
        )

    async def restart_worker(self, worker_id: str, worker: WorkerProcess) -> None:
        try:
            launch_config = worker.launch_config
            if not launch_config.get("cmd"):
                logger.error(f"Cannot restart {worker_id}: Missing launch config")
                self.workers.pop(worker_id, None)
                return

            logger.info(f"Restarting Worker {worker_id}...")
            self.launcher.refresh_worker_token(worker_id, launch_config["env"])
            proc = self.launcher.launch(worker_id, launch_config)

            worker.process = proc
            worker.is_dead = False
            logger.info(f"Worker {worker_id} restarted (PID: {proc.pid})")
        except Exception as e:
            logger.error(f"Restart failed for {worker_id}: {e}")
            worker.next_restart_time = time.time() + 30
