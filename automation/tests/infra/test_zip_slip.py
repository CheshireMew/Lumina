import sys
import os
import zipfile
import shutil
import asyncio
from pathlib import Path
import logging

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup Path to import from python_backend
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.plugin_service import PluginService

# Mock Logger to see warnings
logging.basicConfig(level=logging.INFO)

def create_malicious_zip(zip_name):
    # Create a dummy manifest
    manifest_content = """
    id: "test.malicious"
    name: "Malicious Plugin"
    version: "1.0.0"
    """
    
    with zipfile.ZipFile(zip_name, 'w') as zf:
        zf.writestr('manifest.yaml', manifest_content)
        # Add a file with path traversal
        # Try to write to a file in the current directory (outside plugins/system/test_malicious)
        zf.writestr('../../escaped_file.txt', 'This file should not exist.')

async def test_zip_slip():
    zip_name = 'malicious_test.zip'
    create_malicious_zip(zip_name)
    
    print(f"[Test] Created {zip_name} with malicious payload.")
    
    # Instantiate Service (mock credentials)
    service = PluginService(None)
    
    # Target file that should NOT be created
    # We expect extraction to target plugins/system/test_malicious
    # So ../../escaped_file.txt would land in current working directory
    escaped_file = Path('escaped_file.txt').resolve()
    
    # Cleanup before test
    if escaped_file.exists():
        os.remove(escaped_file)
        
    try:
        print("[Test] Attempting extraction...")
        # Since _extract_zip_sync is sync but called from async in real code, 
        # we can call it directly here as it is a sync function.
        # But wait, in the class it is defined as synchronous `def _extract_zip_sync`.
        plugin_id = service._extract_zip_sync(Path(zip_name))
        
        print(f"[Test] Extraction finished. Plugin ID: {plugin_id}")
        
        if escaped_file.exists():
            print("❌ FAILED: 'escaped_file.txt' was created! Zip Slip vulnerability exists.")
            os.remove(escaped_file)
            sys.exit(1)
        else:
            print("✅ PASSED: 'escaped_file.txt' was NOT created. Zip Slip blocked.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        # If it crashed, it might be good or bad depending on why. 
        # But here we expect it to swallow the error and log a warning (continue loop).
        raise
    finally:
        # Cleanup zip
        if os.path.exists(zip_name):
            os.remove(zip_name)
        # Cleanup plugin dir
        shutil.rmtree('plugins/system/test_malicious', ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(test_zip_slip())
