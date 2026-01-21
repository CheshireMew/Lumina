
import psutil
import time
import random
import logging
import sys

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [CHAOS] - %(message)s')
logger = logging.getLogger("ChaosMonkey")

TARGETS = ["stt_server", "tts_server"]

def kill_random_worker():
    """
    Finds running worker processes and kills one at random.
    """
    logger.info(f"🐍 Chaos Monkey waking up... Hunt targets: {TARGETS}")
    
    candidates = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline:
                # Backend Launcher pattern: python backend_launcher.py stt_server ...
                cmd_str = " ".join(cmdline)
                for target in TARGETS:
                    if "backend_launcher.py" in cmd_str and target in cmd_str:
                        candidates.append((proc, target))
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    if not candidates:
        logger.info("❌ No targets found. Are workers running?")
        return

    # Pick one
    victim, name = random.choice(candidates)
    
    logger.warning(f"🔫 POW! Killing {name} (PID: {victim.pid})")
    try:
        victim.kill()
        logger.info(f"💀 {name} is dead.")
    except Exception as e:
        logger.error(f"Failed to kill {name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--loop":
        logger.info("Loop Mode: Killing every 30s")
        while True:
            kill_random_worker()
            time.sleep(30)
    else:
        kill_random_worker()
