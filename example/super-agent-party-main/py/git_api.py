import os, shutil, platform, subprocess, threading, requests, tempfile, time
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/git")

GIT_TASKS = {}

class Progress(BaseModel):
    percent: float
    status: str

@router.get("/probe")
def probe():
    return {"installed": shutil.which("git") is not None}

@router.post("/install")
def install(background: BackgroundTasks):
    task_id = str(int(time.time() * 1000))
    background.add_task(worker, task_id)
    return {"task_id": task_id}

@router.get("/progress/{task_id}", response_model=Progress)
def progress(task_id: str):
    t = GIT_TASKS.get(task_id, {"percent": 0, "status": "error"})
    return Progress(**t)

def worker(task_id: str):
    try:
        GIT_TASKS[task_id] = {"percent": 5, "status": "running"}
        plat = platform.system().lower()
        arch = platform.machine().lower()

        # 官方最新发布页
        url_map = {
            "windows": "https://github.com/git-for-windows/git/releases/download/v2.45.1/Git-2.45.1-64-bit.exe",
            "darwin": "https://sourceforge.net/projects/git-osx-installer/files/git-2.45.1-intel-universal-mavericks.dmg/download",
            "linux": "https://github.com/git/git/archive/v2.45.1.tar.gz"  # 源码，实际可改用包管理
        }
        url = url_map.get(plat)
        if not url:
            raise RuntimeError("暂不支持当前平台")

        local_file = Path(tempfile.gettempdir()) / url.split("/")[-1]

        # 下载
        download(task_id, url, local_file)
        GIT_TASKS[task_id]["percent"] = 70
        silent_install(local_file, GIT_TASKS[task_id])

        if shutil.which("git"):
            GIT_TASKS[task_id]["percent"] = 100
            GIT_TASKS[task_id]["status"] = "finished"
        else:
            raise RuntimeError("git 仍不在 PATH")
    except Exception as e:
        GIT_TASKS[task_id]["status"] = "error"
        GIT_TASKS[task_id]["error"] = str(e)

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
                GIT_TASKS[task_id]["percent"] = 5 + done / total * 60
    GIT_TASKS[task_id]["percent"] = 65

def silent_install(installer: Path, task: dict):
    plat = platform.system().lower()
    if "windows" in plat:
        subprocess.check_call([str(installer), "/VERYSILENT", "/NORESTART"], timeout=300)
    elif "darwin" in plat:
        # 挂载 dmg + 安装 pkg
        mount = tempfile.mkdtemp()
        subprocess.check_call(["hdiutil", "attach", "-nobrowse", "-mountpoint", mount, str(installer)])
        pkg = next(Path(mount).glob("*.pkg"))
        subprocess.check_call(["sudo", "installer", "-pkg", str(pkg), "-target", "/"])
        subprocess.check_call(["hdiutil", "detach", mount])
    else:
        # 简单用包管理
        subprocess.check_call(["sudo", "apt", "install", "-y", "git"])
    task["percent"] = 95