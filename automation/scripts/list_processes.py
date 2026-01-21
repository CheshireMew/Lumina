
import psutil

print("Scanning for Python processes...")
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline')
        if cmdline and 'python' in proc.info.get('name', '').lower():
            print(f"PID: {proc.info['pid']} | Cmd: {cmdline}")
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
