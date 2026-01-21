import subprocess
import sys
import os
import logging
import asyncio
import time
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger("ProcessManager")

class WorkerProcess:
    def __init__(self, process: subprocess.Popen, start_time: float):
        self.process = process
        self.start_time = start_time
        self.last_heartbeat = start_time
        self.is_external = False

def _check_port_open(port: int, host="127.0.0.1") -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def _check_http_health(port: int, path: str = "/health", host="127.0.0.1", timeout=1.0) -> bool:
    """Standard HTTP Health Probe"""
    import urllib.request
    import urllib.error
    url = f"http://{host}:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

def _stream_output(stream, prefix: str):
    """Helper thread to pipe subprocess output to main logger"""
    try:
        for line in iter(stream.readline, b''):
            decoded = line.decode('utf-8', errors='replace').strip()
            if decoded:
                # Filter out noisy heartbeat/registry logs
                if "POST /plugins/registry" in decoded and "200 OK" in decoded:
                    continue
                if "GET /plugins/slots" in decoded and "200 OK" in decoded:
                    continue
                
                # Use print to avoid double-logging (Main Logger Prefix + Worker Logger Prefix)
                # The worker logs already have timestamps and levels.
                print(f"[{prefix}] {decoded}", flush=True)
    except ValueError:
        pass
    except Exception as e:
        # Keep error logging for the stream itself via the main logger
        logger.error(f"[{prefix}] Log Stream Error: {e}")
    finally:
        stream.close()

class ProcessManager:
    """
    [Architecture 4.0] The Micro-Orchestrator.
    Manages the lifecycle of external worker processes (STT, TTS, etc.).
    [Architecture 5.0] Supports MCP Hybrid Governance (Sync & Async).
    """
    def __init__(self):
        self.workers: Dict[str, Any] = {} # Union[WorkerProcess, MCPClient]
        
        # [Architecture 5.0] Dynamic Service Registry
        # Mapping: service_id -> ServiceDefinition(port, args, env)
        self.registry: Dict[str, dict] = {} 
        self._shutdown_event = asyncio.Event()
        self._managed_scripts: Dict[str, str] = {}

    def register_service_def(self, service_id: str, port: int, script: str = "backend_launcher.py", args: List[str] = None):
        """Define a service for management"""
        self.registry[service_id] = {
            "port": port,
            "script": script,

            "args": args or [],
            "health_path": "/health" # Default standard
        }
        
    def set_health_path(self, service_id: str, path: str):
        if service_id in self.registry:
            self.registry[service_id]["health_path"] = path

    def register_mcp_client(self, client):
        """Register an MCP Client for governance"""
        self.workers[client.name] = client
        logger.info(f"Registered MCP Service: {client.name} (PID: {client.pid})")

    def start_worker(self, worker_id: str, script_name: str = None, args: List[str] = None):
        """
        Starts a worker process using Registry definition or explicit args.
        """
        if self.is_running(worker_id):
            logger.info(f"Worker {worker_id} is already running.")
            return True

        # Resolve Definition from Registry
        service_def = self.registry.get(worker_id)
        
        # Fallback to provided args (Legacy/Manual)
        target_port = service_def["port"] if service_def else None
        target_script = service_def["script"] if service_def else script_name
        target_args = service_def["args"] if service_def else args
        
        if not target_script:
             logger.error(f"Cannot start {worker_id}: No registry definition and no script provided.")
             return False

        # [Architecture 4.0] Hybrid Manual/Auto Mode
        # Check if the service is already running externally using Port Check
        if target_port:
             is_alive = False
             # Prioritize HTTP Probe if we know it serves HTTP
             # (Heuristic: All our backend services are FastAPI, so HTTP check is safer)
             health_path = service_def.get("health_path", "/health") if service_def else "/health"
             
             if _check_http_health(target_port, health_path):
                 is_alive = True
                 logger.info(f"🕵️ Service {worker_id} detected via HTTP Probe ({target_port}{health_path}).")
             elif _check_port_open(target_port):
                 # Fallback to TCP (e.g. Database or raw socket)
                 is_alive = True
                 logger.info(f"🕵️ Service {worker_id} detected via TCP Port {target_port} (HTTP failed).")
             
             if is_alive:
                 fake_worker = WorkerProcess(None, time.time())
                 fake_worker.is_external = True
                 self.workers[worker_id] = fake_worker
                 return True

        try:
            # Resolve script path (Assuming relative to python_backend root)
            base_dir = Path(__file__).parent.parent
            script_path = base_dir / target_script
            
            if not script_path.exists():
                logger.error(f"Script not found: {script_path}")
                return False

            cmd = [sys.executable, str(script_path)]
            if target_args:
                cmd.extend(target_args)

            # Env customization if needed (e.g. inheritance)
            env = os.environ.copy()
            # EnsurePYTHONPATH includes local dir
            env["PYTHONPATH"] = str(base_dir)
            # [Fix] Identity Injection for Loader
            env["LUMINA_SERVICE_NAME"] = worker_id


            logger.info(f"🚀 Spawning Worker: {worker_id} ({script_name})...")
            
            # Use distinct process group on Unix, or creation flags on Windows if needed
            # For now, standard Popen
            proc = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(base_dir),
                # [Observability] Pipe logs to Main Process
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT # Merge stderr into stdout for unified filtering
            )
            
            # Start Log Threads
            import threading
            t_out = threading.Thread(target=_stream_output, args=(proc.stdout, worker_id), daemon=True)
            # t_err is no longer needed as stderr is merged
            t_out.start()
            
            self.workers[worker_id] = WorkerProcess(proc, time.time())
            self._managed_scripts[worker_id] = script_name
            
            logger.info(f"Worker {worker_id} started (PID: {proc.pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start worker {worker_id}: {e}")
            return False

    def stop_worker(self, worker_id: str):
        if worker_id not in self.workers:
            return
        
        logger.info(f"Stopping worker {worker_id}...")
        worker = self.workers[worker_id]
        
        # [Architecture 5.0] Handle Async MCP Clients
        if hasattr(worker, "stop") and asyncio.iscoroutinefunction(worker.stop):
             # We need to run this in the event loop.
             # Since stop_worker is often called synchronously during shutdown,
             # we might need to spawn a task if loop running, or run_until_complete if not.
             try:
                 loop = asyncio.get_running_loop()
                 loop.create_task(worker.stop())
                 logger.info(f"Scheduled Async Stop for {worker_id}")
                 # We assume it will stop, remove from dict immediately to prevent double kill?
                 # Or wait? Ideally wait, but shutdown_all is tricky.
             except RuntimeError:
                 # No loop running?
                 pass
             finally:
                 del self.workers[worker_id]
             return

        # Traditional Sync Worker
        try:
            if getattr(worker, 'is_external', False):
                 logger.warning(f"Worker {worker_id} is external. Cannot stop it via ProcessManager.")
                 # We still remove it from our tracking list in finally block
            elif hasattr(worker, 'process') and worker.process:
                worker.process.terminate()
                try:
                    # Wait for graceful exit
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
        if worker_id not in self.workers:
            return False
            
        worker = self.workers[worker_id]
        
        # External Process Case
        if worker.is_external:
            # Re-verify port status? 
            # If user kills manual process, we should detect it and allow respawn.
            # Re-verify status
            # If registry has definition, use that to resolve port
            svc_def = self.registry.get(worker_id)
            port = None
            health_path = "/health"
            
            if svc_def:
                port = svc_def.get("port")
                health_path = svc_def.get("health_path", "/health")
            else:
                # Fallback Legacy Map
                port_map = {"stt_server": 8765, "tts_server": 8766, "memory": 8010}
                port = port_map.get(worker_id)
            
            if port:
                # Try HTTP first
                if _check_http_health(port, health_path):
                    return True
                # Try TCP fallback (if HTTP fails but port is open, might be starting or non-HTTP)
                if _check_port_open(port):
                    return True
                    
                logger.info(f"External service {worker_id} disappeared from port {port}.")
                del self.workers[worker_id]
                return False
            return True

        # Spawned Process Case
        if not worker.process: return False
        
        proc = worker.process
        
        # Handle asyncio.subprocess.Process (has returncode, no poll)
        if hasattr(proc, 'returncode'):
             # If returncode is set, it exited.
             if proc.returncode is not None:
                 status = proc.returncode
             else:
                 status = None # Still running
        elif hasattr(proc, 'poll'): 
             status = proc.poll()
        else:
             logger.warning(f"Unknown process type in worker {worker_id}: {type(proc)}")
             status = None

        if status is not None:
            # Process has exited
            # Clean up
            logger.info(f"Worker {worker_id} exited with code {status}")
            del self.workers[worker_id]
            return False
        
        return True

    def get_active_workers(self) -> List[str]:
        """
        Get list of active worker IDs.
        Cleans up dead workers safely without mutating dict during iteration.
        """
        # [Fix] Iterate over a copy of keys to avoid RuntimeError
        # when is_running() removes dead workers from self.workers
        worker_ids = list(self.workers.keys())
        
        active = []
        for wid in worker_ids:
            # is_running() may delete from self.workers, but we're iterating over a copy
            if self.is_running(wid):
                active.append(wid)
        
        return active

    async def shutdown_all(self):
        """Graceful shutdown of all managed workers"""
        logger.info("ProcessManager shutting down all workers...")
        ids = list(self.workers.keys())
        for wid in ids:
            self.stop_worker(wid)
