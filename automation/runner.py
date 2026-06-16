
import os
import sys
import subprocess
import time
import json
import re
import requests
import asyncio
import threading
from typing import Dict, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 60  # Startup Timeout
LOG_FILE = os.path.join(PROJECT_ROOT, "automation", "latest_run.log")

class LuminaRunner:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.ports: Dict[str, int] = {}
        self.ready = False
        
    def log(self, msg: str):
        print(f"[Autobot] {msg}")
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(f"{msg}\n")

    def start(self):
        """Spawns the Application and waits for Port Handshake"""
        # Clean Stale Configs to prevent Race Conditions
        paths = [
            os.path.join(PROJECT_ROOT, "Lumina_Data", "config", "ports.json"),
            os.path.join(PROJECT_ROOT, "config", "ports.json"),
            os.path.join(PROJECT_ROOT, "Lumina_Data", "config", "config.yaml"),
            os.path.join(PROJECT_ROOT, "config", "config.yaml") 
        ]
        for p in paths:
             if os.path.exists(p):
                 try:
                     os.remove(p)
                     self.log(f"🧹 Removed stale config: {p}")
                 except:
                     pass

        self.log("🚀 Launching Lumina (npm run dev)...")
        
        # Ensure we are in the root
        cmd = "npm run dev"
        if sys.platform == "win32":
            cmd = "npm.cmd run dev"

        # Start Process with Pipes
        self.process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout to see Python errors
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Monitor Stdout for "Dynamic Ports" JSON or similar markers
        start_time = time.time()
        buffer = ""
        
        # Monitor Stdout in Background Thread
        self.stop_signal = threading.Event()
        
        def pump_logs():
            while not self.stop_signal.is_set():
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        # Process terminated, exit thread
                        break
                    time.sleep(0.1) # Wait a bit before trying again if no line
                    continue
                    
                # Echo and Log
                # Encode/Decode to handle weird chars safely
                safe_line = line.strip()
                if safe_line:
                    try:
                        print(safe_line) # Echo to console for user
                        with open(LOG_FILE, "a", encoding='utf-8') as f:
                            f.write(safe_line + "\n")
                    except Exception as e:
                        # Log the error to stderr or internal log if file writing fails
                        sys.stderr.write(f"Error writing to log file: {e}\n")
                        pass
                
                # Check for Ready Signal (Startup Phase)
                if not self.ready:
                    # Stdout Signal
                    if "[BackendManager] Loaded dynamic ports:" in safe_line:
                        self.log("🔍 Detected Port Configuration Block...")
                        # Regex parsing could go here if needed, but we rely on file now.
                    if "Python Backend started" in safe_line:
                        self.log("✅ Main Process Signal Received")
                        self.ready = True # Signal start loop
                        
        self.log_thread = threading.Thread(target=pump_logs, daemon=True)
        self.log_thread.start()

        # [Refactor] Static Port Definition (Uniform Config)
        self.ports = {
            'memory_port': 8010,
            'stt_port': 8765,
            'tts_port': 8766
        }
        self.log(f"⚡ Using Standard Ports: {self.ports}")

        # Wait for "Python Backend started" Signal from Logs
        start_time = time.time()
        
        while time.time() - start_time < TIMEOUT:
            if self.process.poll() is not None:
                raise RuntimeError("Lumina Process Died Early")
            
            # Wait for pump_logs to set self.ready
            if self.ready:
                break
            time.sleep(0.5)
            
        if not self.ready:
            self.stop()
            raise TimeoutError("Lumina failed to start (Signal not received)")

    # _try_read_connection_file Removed (Config Unification)

    def wait_for_services(self) -> bool:
        """Polls health endpoints until services are up"""
        self.log("⏳ Waiting for Services to come online...")
        services_to_check = [
            ("Memory", self.ports['memory_port']),
            ("STT", self.ports['stt_port']),
            ("TTS", self.ports['tts_port'])
        ]
        
        start_wait = time.time()
        while time.time() - start_wait < 30: # 30s Startup Timeout
            all_up = True
            for name, port in services_to_check:
                try:
                    r = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
                    if r.status_code != 200:
                        all_up = False
                        break
                except:
                    all_up = False
                    break
            
            if all_up:
                self.log("✅ All Services are Online!")
                return True
                
            time.sleep(1)
            
        self.log("❌ Services failed to start within 30s")
        return False

    def run_tests(self):
        """Run the actual regression suite"""
        if not self.ready:
            self.log("⚠️ Cannot run tests: System not ready")
            return

        if not self.wait_for_services():
             self.log("⚠️ Aborting tests due to startup failure")
             return

        self.log("\n🧪 Executing Regression Suite...\n")
        
        failed = 0
        
        # T1: Health Checks
        for service, port in [("Memory", self.ports['memory_port']), ("STT", self.ports['stt_port']), ("TTS", self.ports['tts_port'])]:
            url = f"http://127.0.0.1:{port}/health"
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    self.log(f"[{'PASS'}] {service} Health ({url})")
                else:
                     self.log(f"[{'FAIL'}] {service} Health ({url}) -> {r.status_code}")
                     failed += 1
            except Exception as e:
                self.log(f"[{'FAIL'}] {service} Health ({url}) -> Connection Error")
                failed += 1
                
        # T2: Plugin Registry Check (Async Retry)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # [Fix] Registry is POST-only. Use /list to see loaded plugins.
                # Also removed /api/v1 prefix based on logs showing root mount.
                url = f"http://127.0.0.1:{self.ports['memory_port']}/plugins/list"
                r = requests.get(url, timeout=2)
                data = r.json()
                
                # Check for Voiceprint capability
                # /list returns a dict with plugin IDs as keys or a list? 
                # Assuming list or dict values.
                if isinstance(data, dict) and "plugins" in data:
                     plugins = data["plugins"] # normalized response
                elif isinstance(data, list):
                     plugins = data
                else:
                     plugins = list(data.values()) if isinstance(data, dict) else []

                vp = next((p for p in plugins if isinstance(p, dict) and p.get('id') == 'system.voiceprint'), None)
                
                if vp:
                    self.log(f"[{'PASS'}] Plugin Registry: Voiceprint Found & Enabled ({vp.get('active_in_group', False)})")
                    break
                else:
                    self.log(f"   ... Waiting for Plugins to Load (Attempt {attempt+1}/{max_retries})")
            except:
                pass
            
            time.sleep(2)
        else:
            self.log(f"[{'FAIL'}] Plugin Registry: Voiceprint Timeout after {max_retries*2}s")
            failed += 1
            
        if failed == 0:
            self.log(f"\n✨ All Systems Operational. Regression Passed.")
        else:
            self.log(f"\n🔥 Regression Failed with {failed} errors.")


    def stop(self):
        """Graceful Teardown"""
        self.log("🛑 Stopping runner...")
        if self.process:
            # On Windows, we need to kill the tree to get electron + python
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
            self.log("   Process Tree Killed.")

if __name__ == "__main__":
    runner = LuminaRunner()
    try:
        runner.start()
        runner.run_tests()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        runner.log(f"Fatal Error: {e}")
    finally:
        runner.stop()
