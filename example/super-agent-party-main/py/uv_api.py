import os, shutil, platform, subprocess, threading, requests, tempfile, time
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/uv")

UV_TASKS = {}

class Progress(BaseModel):
    percent: float
    status: str

# 1. 探针
@router.get("/probe")
def probe():
    return {"installed": shutil.which("uv") is not None}

# 2. 开始安装
@router.post("/install")
def install(background: BackgroundTasks):
    task_id = str(int(time.time()*1000))
    background.add_task(worker, task_id)
    return {"task_id": task_id}

# 3. 查询进度
@router.get("/progress/{task_id}", response_model=Progress)
def progress(task_id: str):
    t = UV_TASKS.get(task_id, {"percent": 0, "status": "error"})
    return Progress(**t)

# 4. 后台线程
def worker(task_id: str):
    try:
        UV_TASKS[task_id] = {"percent": 5, "status": "running"}
        plat = platform.system().lower()
        arch = "x86_64" if platform.machine().lower() in ("amd64", "x86_64") else "aarch64"

        # 取 GitHub 最新 release 下载地址
        api = "https://api.github.com/repos/astral-sh/uv/releases/latest"
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        assets = r.json()["assets"]

        # 选平台对应文件名
        if "windows" in plat:
            target = f"uv-{arch}-pc-windows-msvc.zip"
        elif "darwin" in plat:
            target = f"uv-{arch}-apple-darwin.tar.gz"
        else:
            target = f"uv-{arch}-unknown-linux-gnu.tar.gz"

        url = next(a["browser_download_url"] for a in assets if target in a["name"])
        local_file = Path(tempfile.gettempdir()) / target

        # 下载
        download(task_id, url, local_file)

        # 安装
        UV_TASKS[task_id]["percent"] = 70
        install_bin(local_file, UV_TASKS[task_id])

        # 最终探针
        if shutil.which("uv"):
            UV_TASKS[task_id]["percent"] = 100
            UV_TASKS[task_id]["status"] = "finished"
        else:
            raise RuntimeError("uv 仍不在 PATH")
    except Exception as e:
        UV_TASKS[task_id]["status"] = "error"
        UV_TASKS[task_id]["error"] = str(e)

def download(task_id: str, url: str, local_path: Path):
    r = requests.get(url, stream=True, timeout=15)
    r.raise_for_status()
    total = int(r.headers.get('content-length', 0))
    done = 0
    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(1024*64):
            if chunk:
                f.write(chunk)
                done += len(chunk)
                UV_TASKS[task_id]["percent"] = 5 + done/total*60
    UV_TASKS[task_id]["percent"] = 65

def install_bin(archive: Path, task: dict):
    plat = platform.system().lower()
    tmp = archive.parent / "uv_extract"
    tmp.mkdir(exist_ok=True)
    if archive.suffix == ".zip":
        subprocess.check_call(["powershell", "-command", f"Expand-Archive -Path '{archive}' -DestinationPath '{tmp}'"])
        exe = tmp / "uv.exe"
        target_dir = Path.home() / "AppData/Local/uv"
        target_dir.mkdir(exist_ok=True)
        shutil.copy2(exe, target_dir / "uv.exe")
        # 把目录写进用户 PATH
        add_to_user_path(str(target_dir))
    else:
        # tar.gz
        subprocess.check_call(["tar", "-xzf", str(archive), "-C", str(tmp)])
        exe = next(tmp.rglob("uv"))
        shutil.copy2(exe, "/usr/local/bin/uv")
        subprocess.check_call(["chmod", "+x", "/usr/local/bin/uv"])
    task["percent"] = 95

def add_to_user_path(new_dir: str):
    """Windows 仅当前用户"""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Environment", 0, winreg.KEY_ALL_ACCESS) as key:
        path, _ = winreg.QueryValueEx(key, "Path")
        if new_dir not in path:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ,
                              path + ";" + new_dir)
    # 广播让系统立即生效（可选）
    subprocess.run(["setx", "PATH", path + ";" + new_dir], check=False)