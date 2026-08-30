import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("WorkerLauncher")


def stream_worker_output(stream, prefix: str) -> None:
    try:
        for line in iter(stream.readline, b""):
            decoded = line.decode("utf-8", errors="replace").strip()
            if not decoded:
                continue
            print(f"[{prefix}] {decoded}", flush=True)
    except ValueError:
        pass
    except Exception as e:
        logger.error(f"[{prefix}] Log Stream Error: {e}")
    finally:
        stream.close()


class WorkerLauncher:
    def __init__(self, worker_runtime_registry, base_dir: Optional[Path] = None):
        if worker_runtime_registry is None:
            raise ValueError("WorkerLauncher requires WorkerRuntimeRegistry")

        self.base_dir = base_dir or Path(__file__).parent.parent
        self.worker_runtime_registry = worker_runtime_registry

    def build_launch_config(
        self,
        worker_id: str,
        script_name: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> Optional[Dict]:
        entry_path = Path(script_name)
        if entry_path.is_absolute():
            env = os.environ.copy()
            env["LUMINA_SERVICE_NAME"] = worker_id
            self._apply_runtime_environment(worker_id, env)
            self.refresh_worker_token(worker_id, env)

            command = [str(entry_path)]
            if entry_path.suffix.lower() == ".py":
                command = [sys.executable, str(entry_path)]
            if args:
                command.extend(args)

            return {
                "cmd": command,
                "env": env,
                "cwd": cwd or str(entry_path.parent),
                "script_name": script_name,
                "display_name": entry_path.name,
            }

        if getattr(sys, "frozen", False):
            env = os.environ.copy()
            env["LUMINA_SERVICE_NAME"] = worker_id
            self._apply_runtime_environment(worker_id, env)
            self.refresh_worker_token(worker_id, env)

            return {
                "cmd": [sys.executable, *(args or [])],
                "env": env,
                "cwd": str(Path(sys.executable).parent),
                "script_name": script_name,
                "display_name": Path(sys.executable).name,
            }

        script_path = self.base_dir / script_name
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return None

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.base_dir)
        env["LUMINA_SERVICE_NAME"] = worker_id
        self._apply_runtime_environment(worker_id, env)
        self.refresh_worker_token(worker_id, env)

        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        return {
            "cmd": cmd,
            "env": env,
            "cwd": str(self.base_dir),
            "script_name": script_name,
            "display_name": script_name,
        }

    def _apply_runtime_environment(self, worker_id: str, env: Dict[str, str]) -> None:
        env["LUMINA_PARENT_PID"] = str(os.getpid())
        if not worker_id.startswith("worker:"):
            return

        capability = worker_id.split(":", 1)[1]
        definition = self.worker_runtime_registry.runtime_for_capability(capability)
        if not definition:
            return

        runtime_roots: list[Path] = []
        snapshot = self.worker_runtime_registry.resolve(definition.id)
        if snapshot and snapshot.status == "ready" and snapshot.root_dir:
            runtime_roots.append(snapshot.root_dir)
            if snapshot.source_name == "bundled":
                env["LUMINA_RESOURCES_DIR"] = str(snapshot.root_dir.parent.parent)
            env["LUMINA_WORKER_RUNTIME_ID"] = definition.id
            env["LUMINA_WORKER_RUNTIME_DIR"] = str(snapshot.root_dir)
            env[f"LUMINA_{capability.upper()}_RUNTIME_DIR"] = str(snapshot.root_dir)
            models_dir = snapshot.root_dir / "data" / "models"
            env[f"LUMINA_{capability.upper()}_MODELS_DIR"] = str(models_dir)

        voiceprint = self.worker_runtime_registry.resolve("voiceprint-runtime")
        if voiceprint and voiceprint.status == "ready" and voiceprint.root_dir:
            runtime_roots.append(voiceprint.root_dir)
            env["LUMINA_VOICEPRINT_RUNTIME_DIR"] = str(voiceprint.root_dir)

        driver_roots = [
            str(root / "provider_drivers")
            for root in runtime_roots
            if (root / "provider_drivers").exists()
        ]
        if driver_roots:
            existing_pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = os.pathsep.join(
                [str(root) for root in runtime_roots]
                + ([existing_pythonpath] if existing_pythonpath else [])
            )

    def refresh_worker_token(self, worker_id: str, env: Dict[str, str]) -> None:
        from security.tokens import TokenManager

        env["LUMINA_WORKER_TOKEN"] = TokenManager.create_token(
            worker_id,
            scopes=["worker.control"],
            ttl_minutes=1440,
            scope="worker",
        )

    def launch(self, worker_id: str, launch_config: Dict) -> subprocess.Popen:
        proc = subprocess.Popen(
            launch_config["cmd"],
            env=launch_config["env"],
            cwd=launch_config["cwd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        t_out = threading.Thread(
            target=stream_worker_output,
            args=(proc.stdout, worker_id),
            daemon=True,
        )
        t_out.start()
        return proc
