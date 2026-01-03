import os, shutil, platform, subprocess, threading, requests, tempfile, time
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/node")

NODE_TASKS = {}

class Progress(BaseModel):
    percent: float
    status: str

@router.get("/probe")
def probe():
    return {"installed": shutil.which("node") is not None}

@router.post("/install")
def install(background: BackgroundTasks):
    task_id = str(int(time.time() * 1000))
    background.add_task(worker, task_id)
    return {"task_id": task_id}

@router.get("/progress/{task_id}", response_model=Progress)
def progress(task_id: str):
    t = NODE_TASKS.get(task_id, {"percent": 0, "status": "error"})
    return Progress(**t)

def worker(task_id: str):
    try:
        NODE_TASKS[task_id] = {"percent": 5, "status": "running"}
        plat = platform.system().lower()

        # 取官方最新 LTS 版本号
        r = requests.get("https://nodejs.org/dist/latest-v20.x/")
        r.raise_for_status()
        filename = None
        if "windows" in plat:
            filename = [l for l in r.text.splitlines() if "x64.msi" in l and "href" in l][0].split('"')[1]
        elif "darwin" in plat:
            filename = [l for l in r.text.splitlines() if "pkg" in l and "href" in l][0].split('"')[1]
        else:
            filename = [l for l in r.text.splitlines() if "linux-x64.tar.xz" in l and "href" in l][0].split('"')[1]

        base_url = "https://nodejs.org/dist/latest-v20.x/"
        url = base_url + filename
        local_file = Path(tempfile.gettempdir()) / filename

        download(task_id, url, local_file)
        NODE_TASKS[task_id]["percent"] = 70
        silent_install(local_file, NODE_TASKS[task_id])

        if shutil.which("node"):
            NODE_TASKS[task_id]["percent"] = 100
            NODE_TASKS[task_id]["status"] = "finished"
        else:
            raise RuntimeError("node 仍不在 PATH")
    except Exception as e:
        NODE_TASKS[task_id]["status"] = "error"
        NODE_TASKS[task_id]["error"] = str(e)

def download(task_id: str, url: str, local_path: Path):
    r = requests.get(url, stream=True, timeout=15)
    r.raise_for_status()
    total = int(r.headers.get('content-length', 0))
    done = 0
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(1024 * 64):
            if chunk:
                f.write(chunk)
                done += len(chunk)
                NODE_TASKS[task_id]["percent"] = 5 + done / total * 60
    NODE_TASKS[task_id]["percent"] = 65

def silent_install(installer: Path, task: dict):
    plat = platform.system().lower()
    if "windows" in plat:
        subprocess.check_call(["msiexec", "/i", str(installer), "/quiet", "/norestart"], timeout=300)
    elif "darwin" in plat:
        subprocess.check_call(["sudo", "installer", "-pkg", str(installer), "-target", "/"], timeout=300)
    else:
        extract_to = Path("/usr/local/lib/nodejs")
        subprocess.check_call(["sudo", "tar", "-xJf", str(installer), "-C", "/usr/local/lib"])
        node_dir = next((extract_to / installer.stem.split(".tar")[0]).glob("node*"))
        subprocess.check_call(["sudo", "ln", "-sf", str(node_dir / "bin/node"), "/usr/local/bin/node"])
        subprocess.check_call(["sudo", "ln", "-sf", str(node_dir / "bin/npm"), "/usr/local/bin/npm"])
    task["percent"] = 95