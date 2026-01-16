
import sys
import os
import logging

# Setup Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, '..', 'python_backend')
sys.path.append(backend_dir)

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugVoiceprint")

try:
    print("[-] Attempting to import VoiceprintManager...")
    from plugins.system.voiceprint.manager import VoiceprintManager
    print("[+] Import Successful!")
    
    print("[-] Instantiating Manager...")
    manager = VoiceprintManager()
    print(f"[+] Instantiated. ID: {manager.id}, Name: {manager.name}")
    
    print("[-] Checking dependencies...")
    from plugins.drivers.voiceauth.sherpa_cam_driver import SherpaCAMDriver
    print("[+] Driver Import Successful!")

except ImportError as e:
    print(f"[!] Import Error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"[!] General Error: {e}")
    import traceback
    traceback.print_exc()
