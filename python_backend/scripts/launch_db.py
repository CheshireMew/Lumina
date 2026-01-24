import sys
import subprocess
import time
import base64
import logging
import urllib.request
import urllib.error
import zipfile
import glob
import os
from datetime import datetime
from pathlib import Path

# Add parent to path for config
sys.path.append(str(Path(__file__).parent.parent))
from app_config import config

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("DBLauncher")

SURREAL_EXE = "surreal"
DB_PATH = config.data_root / "database" / "lumina.db"
BACKUP_DIR = config.data_root / "backups"

def perform_backup():
    """Compress current DB state to backups folder"""
    if not DB_PATH.exists():
        logger.info("🆕 No existing database found. Skipping backup.")
        return

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"lumina_backup_{timestamp}.zip"
        
        logger.info(f"📦 Creating backup: {backup_file.name}...")
        
        # Zip the directory
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(DB_PATH):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(DB_PATH.parent)
                    zipf.write(file_path, arcname)
                    
        logger.info("✅ Backup complete.")
        cleanup_backups()
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")

def cleanup_backups(keep=7):
    """Keep only the N most recent backups"""
    try:
        backups = sorted(glob.glob(str(BACKUP_DIR / "*.zip")), key=os.path.getmtime)
        if len(backups) > keep:
            to_remove = backups[:-keep]
            for f in to_remove:
                os.remove(f)
                logger.info(f"🧹 Removed old backup: {Path(f).name}")
    except Exception as e:
        logger.warning(f"Backup cleanup failed: {e}")


def start_process(user, password, port):
    """Start SurrealDB subprocess"""
    cmd = [
        SURREAL_EXE, "start",
        "--user", user,
        "--pass", password,
        "--bind", f"0.0.0.0:{port}",
        "--log", "info",
        "--allow-all",
        f"file://{DB_PATH.as_posix()}"
    ]
    if password == "root" and user == "root":
         # Suppress warning for fallback
         pass
    else:
         logger.info(f"Attempting start with user={user}")
         
    # Hide window on Windows if possible (optional)
    return subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, text=True)

def check_health(port, user, password, retries=5, proc=None):
    """Check if DB is responsive using SQL endpoint"""
    url = f"http://127.0.0.1:{port}/sql"
    headers = {
        "Accept": "application/json",
        "Content-Type": "text/plain",
        "NS": "test", "DB": "test",
        "Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
    }
    # Simple query
    data = "INFO FOR DB;".encode('utf-8')
    
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True
        except urllib.error.HTTPError as e:
            logger.warning(f"Health Check HTTP Error: {e.code} - {e.reason}")
            if e.code == 403 or e.code == 401: # Return explicit failure on Auth error
                return False
        except Exception as e:
            logger.warning(f"Health Check Connection Failed ({type(e).__name__}): {e}")
        
        if i < retries - 1:
            if proc.poll() is not None:
                logger.error(f"Process died unexpectedly with return code {proc.returncode}")
                return False
            time.sleep(1)
            
    logger.error("Health Check timed out.")
    return False

def rotate_password(port, current_user, current_pass, target_user, target_pass):
    """Execute SQL to rotate password"""
    logger.info("🔄 Migrating Root Password...")
    url = f"http://127.0.0.1:{port}/sql"
    headers = {
        "Accept": "application/json",
        "Authorization": "Basic " + base64.b64encode(f"{current_user}:{current_pass}".encode()).decode()
    }
    # DEFINE USER cannot overwrite/update password if exists.
    # Must REMOVE then DEFINE.
    sql = f"REMOVE USER {target_user} ON ROOT; DEFINE USER {target_user} ON ROOT PASSWORD '{target_pass}' ROLES OWNER;"
    
    try:
        req = urllib.request.Request(url, data=sql.encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode('utf-8')
            logger.debug(f"Migration Response: {body}")
            if resp.status == 200:
                # Check for inner error in SurrealDB JSON response
                if "ERR" in body:
                    logger.error(f"Migration Logic Error: {body}")
                    return False
                logger.info("✅ Password Migration SQL Executed.")
                return True
    except Exception as e:
        logger.error(f"❌ Migration Failed: {e}")
    return False

def main():
    target_user = config.memory.root_user
    target_pass = config.memory.root_password
    port = config.network.surreal_port
    
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 0. Auto-Backup
    perform_backup()

    # 1. Try Target Credentials
    logger.info("🟢 Attempt 1: Starting with Configured Credentials...")
    proc = start_process(target_user, target_pass, port)
    
    # Wait a bit to see if it stays up and accepts auth
    if check_health(port, target_user, target_pass, retries=10, proc=proc):
        logger.info("✅ Database started successfully with configured credentials.")
        try:
             proc.wait()
        except KeyboardInterrupt:
             proc.terminate()
        return

    # If we get here, it failed (likely auth or immediate exit)
    logger.warning("⚠️  Configured Check Failed. Terminating process...")
    proc.terminate()
    proc.wait()
    
    # 2. Try Fallback (root/root)
    logger.info("🟠 Attempt 2: Starting with Fallback (root/root)...")
    fallback_user, fallback_pass = "root", "root"
    proc = start_process(fallback_user, fallback_pass, port)
    
    if check_health(port, fallback_user, fallback_pass, retries=5, proc=proc):
        logger.info("✅ Fallback connection successful. Performing Migration...")
        
        # 3. Migrate
        if rotate_password(port, fallback_user, fallback_pass, target_user, target_pass):
            logger.info("🛑 Stopping Fallback Process...")
            proc.terminate()
            proc.wait()
            time.sleep(2) # Grace period
            
            # 4. Restart with Target
            logger.info("🟢 Restarting with New Credentials...")
            proc = start_process(target_user, target_pass, port)
            if check_health(port, target_user, target_pass, retries=5):
                logger.info("🎉 SUCCESS! Database rotated and running.")
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    proc.terminate()
                return
            else:
                 logger.critical("❌ Failed to connect after migration. Check logs.")
        else:
             logger.critical("❌ Password rotation failed.")
    else:
        logger.critical("❌ Fallback also failed. Is the port blocked or data corrupted?")
    
    # Cleanup if still running
    if proc.poll() is None:
        proc.terminate()

if __name__ == "__main__":
    main()
