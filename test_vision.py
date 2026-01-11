
import requests
import os
import sys
import time
import subprocess

# Color support for Windows terminal
os.system('')

def print_result(success, message):
    if success:
        print(f"\033[92m✅ {message}\033[0m")
    else:
        print(f"\033[91m❌ {message}\033[0m")

print("\n🔍 VISION API DIAGNOSTIC (Moondream2)\n" + "="*40)

# Check if Backend is running
def check_backend():
    try:
        res = requests.get("http://127.0.0.1:8000/docs", timeout=2)
        return res.status_code == 200
    except:
        return False

if not check_backend():
    print("⚠️ Backend (127.0.0.1:8000) seems DOWN.")
    print("   Attempting to verify imports (Dry Run)...")
    
    # Try dry run
    try:
        subprocess.check_call([sys.executable, "-c", "from python_backend.main import app; print('Import OK')"], cwd=os.getcwd())
        print("   ✅ imports look good. Please restart 'python python_backend/main.py' manually in a separate terminal.")
    except subprocess.CalledProcessError as e:
        print("   ❌ Import Verification Failed!")
        print("   There might be a syntax error or missing dependency.")
    
    sys.exit(1)
    
print_result(True, "Backend is reachable (127.0.0.1:8000)")

# 2. Ask for Image
print("\nPlease drag and drop an image file here to test (or paste path):")
img_path = input("> ").strip('"').strip("'")

if not img_path:
    print("Skipping test.")
    sys.exit()

if not os.path.exists(img_path):
    print_result(False, "Image file not found.")
    sys.exit(1)

# 3. Test Analysis
try:
    print(f"\n📦 Analyzing: {os.path.basename(img_path)}")
    print("⏳ Sending request (this may trigger model loading, please wait 10-30s)...")
    
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    files = {"file": ("image.png", img_bytes, "image/png")}
    data = {"prompt": "Describe this image in detail."}
    
    res = requests.post("http://127.0.0.1:8000/vision/analyze", files=files, data=data)
    
    if res.status_code == 200:
        result = res.json()
        print_result(True, "Analysis Success!")
        print(f"\n🧠 Provider: {result.get('provider')}")
        print(f"📝 Description:\n{'-'*20}\n{result.get('description')}\n{'-'*20}")
    else:
        print_result(False, f"Analysis Failed ({res.status_code})")
        print(f"Error: {res.text}")

except Exception as e:
    print_result(False, f"Exception occurred: {e}")
