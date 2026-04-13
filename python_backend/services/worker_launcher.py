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
            if "GET /plugins/slots" in decoded and "200 OK" in decoded:
                continue
            print(f"[{prefix}] {decoded}", flush=True)
    except ValueError:
        pass
    except Exception as e:
        logger.error(f"[{prefix}] Log Stream Error: {e}")
    finally:
        stream.close()


class WorkerLauncher:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent

    def build_launch_config(
        self,
        worker_id: str,
        script_name: str,
        args: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        if getattr(sys, "frozen", False):
            env = os.environ.copy()
            env["LUMINA_SERVICE_NAME"] = worker_id
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

    def refresh_worker_token(self, worker_id: str, env: Dict[str, str]) -> None:
        from security.tokens import TokenManager

        env["LUMINA_WORKER_TOKEN"] = TokenManager.create_token(
            worker_id,
            permissions=["worker.control"],
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
