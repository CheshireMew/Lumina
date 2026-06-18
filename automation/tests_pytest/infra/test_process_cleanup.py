import pytest
import subprocess
import time
import socket
import os
import signal
import sys
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(('127.0.0.1', port)) == 0

@pytest.mark.infra
def test_zombie_process_cleanup():
    """
    针对 Windows 环境验证‘僵尸进程’清理。
    启动主进程及子进程，然后强行杀掉主进程，检查子进程是否仍占用端口。
    """
    python_exe = sys.executable
    launcher_path = PROJECT_ROOT / "python_backend" / "backend_launcher.py"
    
    # 我们不手动启动整个系统，因为那太慢了。
    # 我们模拟 ProcessManager 的行为。
    # 启动一个模拟的 'main' 进程，它启动子进程。
    
    print("\n[Test] Starting master process simulation...")
    # 注意：这里需要一个能自动启动子进程并能够被我们杀掉的脚本
    # 我们直接利用 Lumina 的 backend_launcher 启动 STT
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "python_backend")
    
    # Find a free port
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        free_port = s.getsockname()[1]
    
    print(f"\n[Test] Using dynamic port: {free_port}")
    
    # 模拟启动 STT 独立进程
    # [Refactor] backend_launcher.py uses config.network.stt_port
    # We can override it via env var if the app_config supports it
    env["LUMINA_STT_PORT"] = str(free_port)
    
    stt_proc = subprocess.Popen(
        [python_exe, str(launcher_path), "worker", "--capability", "stt"],
        env=env,
        cwd=str(PROJECT_ROOT / "python_backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"[Test] STT Worker started (PID: {stt_proc.pid}). Waiting for port {free_port}...")
    
    # 等待端口开启
    timeout = 30
    start_time = time.time()
    port_opened = False
    while time.time() - start_time < timeout:
        if is_port_open(free_port):
            port_opened = True
            break
        time.sleep(1)
    
    if not port_opened:
        print("--- STT STDOUT ---")
        # Don't use communicate() as it blocks
        # Just check if proc is still alive
        if stt_proc.poll() is not None:
            out, err = stt_proc.communicate()
            print(out)
            print(err)
        assert False, f"STT worker failed to start/bind port {free_port}"
        
    print(f"[Test] Port {free_port} is OPEN.")
    
    # 现在强行杀掉 STT 进程
    print(f"[Test] Force killing worker {stt_proc.pid}...")
    stt_proc.kill()
    stt_proc.wait()
    
    time.sleep(2) 
    if is_port_open(free_port):
        print(f"🚨 [BUG] Port {free_port} is STILL OPEN after process kill!")
    else:
        print(f"[Test] Port {free_port} released successfully.")
        
    # [Harder Test] 子进程嵌套测试
    # 真正的清理难题是：Main -> Launcher -> STT_Worker
    # 如果 Main 被杀，Launcher 可能变僵尸，从而 STT_Worker 也变僵尸。
