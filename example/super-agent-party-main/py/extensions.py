import stat
import shutil
import tempfile
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Request
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from fastapi import UploadFile, File
from py.get_setting import EXT_DIR

router = APIRouter(prefix="/api/extensions", tags=["extensions"])

class Extension(BaseModel):
    id: str
    name: str
    description: str = "无描述"
    version: str = "1.0.0"
    author: str = "未知"
    systemPrompt: str = ""
    repository: str = ""
    backupRepository: Optional[str] = ""
    category: str = ""
    transparent: bool = False
    width: int = 800
    height: int = 600
    enableVrmWindowSize: bool = False

class ExtensionsResponse(BaseModel):
    extensions: List[Extension]

def _remove_readonly(func, path, exc_info):
    """onexc 回调：如果失败就改权限再删一次"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def robust_rmtree(target: Path):
    """安全删除目录，处理 Windows 只读文件问题"""
    target = Path(target)
    if not target.exists():
        return
    # Python ≥3.12 用 onexc；旧版本用 onerror 即可
    kwargs = {"onexc": _remove_readonly} if hasattr(shutil, "rmtree") and "onexc" in shutil.rmtree.__annotations__ else {"onerror": _remove_readonly}
    shutil.rmtree(target, **kwargs)

def make_tree_writable(target: Path):
    """递归清除目录树的只读属性（Windows 专用）"""
    if os.name != 'nt':  # 只在 Windows 上执行
        return
    for root, dirs, files in os.walk(target):
        for name in files:
            try:
                os.chmod(Path(root) / name, stat.S_IWRITE)
            except Exception:
                pass
        for name in dirs:
            try:
                os.chmod(Path(root) / name, stat.S_IWRITE)
            except Exception:
                pass

def find_root_dir(temp_path: Path) -> Path:
    """如果 zip 解压后只有 1 个一级目录且包含 index.html，则返回子目录"""
    entries = [p for p in temp_path.iterdir() if p.is_dir()]
    if len(entries) == 1 and (entries[0] / "index.html").exists():
        return entries[0]
    return temp_path

# ------------------ 获取扩展列表 ------------------
@router.get("/list", response_model=ExtensionsResponse)
async def list_extensions():
    """获取所有可用的扩展列表"""
    try:
        extensions_dir = EXT_DIR
        
        if not os.path.exists(extensions_dir):
            os.makedirs(extensions_dir, exist_ok=True)
            return ExtensionsResponse(extensions=[])
        
        extensions = []
        for dir_name in os.listdir(extensions_dir):
            dir_path = os.path.join(extensions_dir, dir_name)
            if os.path.isdir(dir_path):
                ext_id = dir_name
                index_path = os.path.join(dir_path, "index.html")
                
                if os.path.exists(index_path):
                    package_path = os.path.join(dir_path, "package.json")
                    if os.path.exists(package_path):
                        try:
                            with open(package_path, 'r', encoding='utf-8') as f:
                                package_data = json.load(f)
                                
                            extensions.append(Extension(
                                id=ext_id,
                                name=package_data.get("name", ext_id),
                                description=package_data.get("description", "无描述"),
                                version=package_data.get("version", "1.0.0"),
                                author=package_data.get("author", "未知"),
                                systemPrompt=package_data.get("systemPrompt", ""),
                                repository=package_data.get("repository", ""),
                                backupRepository=package_data.get("backupRepository", ""),
                                category=package_data.get("category", ""),
                                transparent=package_data.get("transparent", False),
                                width=package_data.get("width", 800),
                                height=package_data.get("height", 600),
                                enableVrmWindowSize=package_data.get("enableVrmWindowSize", False)
                            ))
                        except json.JSONDecodeError:
                            extensions.append(Extension(id=ext_id, name=ext_id))
                    else:
                        extensions.append(Extension(id=ext_id, name=ext_id))
        
        return ExtensionsResponse(extensions=extensions)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取扩展列表失败: {str(e)}")

# ------------------ 删除扩展 ------------------
@router.delete("/{ext_id}", status_code=204)
async def delete_extension(ext_id: str):
    target = Path(EXT_DIR) / ext_id
    if not target.exists():
        raise HTTPException(status_code=404, detail="扩展不存在")
    try:
        robust_rmtree(target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")
    return

# ------------------ GitHub 安装 ------------------
class GitHubInstallRequest(BaseModel):
    url: str
    backupUrl: Optional[str] = ""

def _do_single_install(url: str, temp_dir: Path, target: Path):
    """真正执行一次下载或克隆"""
    # 清理目标目录（如果存在）
    if target.exists():
        robust_rmtree(target)
    
    if url.endswith(".zip"):
        zip_path = temp_dir / "repo.zip"
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        shutil.unpack_archive(zip_path, temp_dir)
        
        inner_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name != "repo.zip"]
        if not inner_dirs:
            raise RuntimeError("zip 包内未找到目录")
        inner = inner_dirs[0]
        
        make_tree_writable(inner)  # 清除只读属性
        shutil.move(str(inner), str(target))
    else:
        # git clone
        clone_dir = temp_dir / "repo"
        url = url.rstrip("/").removesuffix(".git")
        
        # 修改这里：增加 timeout 参数，防止 git 卡死
        try:
            subprocess.run(
                ["git", "clone", f"{url}.git", str(clone_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60  # 60秒超时，超时后会抛出 TimeoutExpired，触发外层切换备用源
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git clone timeout")
            
        make_tree_writable(clone_dir)
        shutil.move(str(clone_dir), str(target))

def check_github_latency() -> bool:
    """
    快速检测 GitHub 连通性
    返回 True 表示连接顺畅，False 表示连接超时或失败
    """
    try:
        # 设置 3 秒超时，只请求 HEAD，不下载内容，速度快
        with httpx.Client(timeout=3.0) as client:
            client.head("https://github.com", follow_redirects=True)
        return True
    except Exception:
        return False

install_tasks = {}

# 2. 修改后台任务函数，使其能更新状态
def _run_bg_install(repo_url: str, ext_id: str, backup_url: str = ""):
    # 初始化状态
    install_tasks[ext_id] = {"status": "installing", "detail": "正在初始化..."}
    
    try:
        target = Path(EXT_DIR) / ext_id
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp())

        # ... (保留原有的清洗地址逻辑) ...
        main_repo = repo_url.strip().rstrip("/") if repo_url else ""
        backup_repo = backup_url.strip().rstrip("/") if backup_url else ""
        
        urls: List[str] = []
        
        # 更新状态：正在检测网络
        install_tasks[ext_id] = {"status": "installing", "detail": "正在检测网络连接..."}

        if main_repo and backup_repo:
            if check_github_latency():
                urls = [main_repo, backup_repo]
            else:
                urls = [backup_repo, main_repo]
        elif main_repo:
            urls = [main_repo]
        elif backup_repo:
            urls = [backup_repo]

        if not urls:
            robust_rmtree(temp_dir)
            raise RuntimeError("没有任何可用仓库地址")

        last_err: Exception | None = None
        for i, url in enumerate(urls):
            try:
                # 更新状态：正在下载
                install_tasks[ext_id] = {
                    "status": "installing", 
                    "detail": f"正在尝试源 {i+1}/{len(urls)}: {url}..."
                }
                
                _do_single_install(url, temp_dir, target)
                robust_rmtree(temp_dir)
                
                # 成功！
                install_tasks[ext_id] = {"status": "success", "detail": "安装成功"}
                return
            except Exception as e:
                last_err = e
                continue

        if target.exists():
            robust_rmtree(target)
        robust_rmtree(temp_dir)
        raise RuntimeError(f"所有仓库地址均安装失败：{last_err}")

    except Exception as e:
        # 失败！记录错误信息
        install_tasks[ext_id] = {"status": "error", "detail": str(e)}

# 3. 新增查询状态的接口
@router.get("/task-status/{ext_id}")
async def get_task_status(ext_id: str):
    status = install_tasks.get(ext_id)
    if not status:
        return {"status": "unknown", "detail": "无此任务"}
    return status

@router.post("/install-from-github")
async def install_from_github(
    req: GitHubInstallRequest, background: BackgroundTasks
):
    parse = urlparse(req.url)
    path_parts = parse.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise HTTPException(status_code=400, detail="URL 格式错误")
    ext_id = f"{path_parts[0]}_{path_parts[1]}"
    target = Path(EXT_DIR) / ext_id
    if target.exists():
        raise HTTPException(status_code=409, detail="扩展已存在")
    
    # 传递 backupUrl
    background.add_task(_run_bg_install, req.url, ext_id, req.backupUrl)
    return {"ext_id": ext_id, "status": "installing"}

# ------------------ 上传 ZIP ------------------
@router.post("/upload-zip")
async def upload_zip(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip 文件")
    ext_id = Path(file.filename).stem
    target = Path(EXT_DIR) / ext_id
    if target.exists():
        raise HTTPException(status_code=409, detail="扩展已存在")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        zip_path = tmp / "up.zip"
        with zip_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        
        unpack = tmp / "unpack"
        shutil.unpack_archive(zip_path, unpack)
        
        real_root = find_root_dir(unpack)
        target.mkdir(parents=True, exist_ok=True)
        for item in real_root.iterdir():
            shutil.move(str(item), str(target))

    return {"ext_id": ext_id, "status": "ok"}

# ------------------ 远程插件列表 ------------------
class RemotePluginItem(BaseModel):
    id: str
    name: str
    description: str
    author: str
    version: str
    category: str = "Unknown"
    repository: str
    backupRepository: Optional[str] = ""
    installed: bool = False

class RemotePluginList(BaseModel):
    plugins: List[RemotePluginItem]

@router.get("/remote-list", response_model=RemotePluginList)
async def remote_plugin_list():
    github_raw = (
        "https://raw.githubusercontent.com/super-agent-party/super-agent-party.github.io/"
        "main/plugins.json"
    )
    gitee_raw = (
        "https://gitee.com/super-agent-party/super-agent-party.github.io/"
        "raw/main/plugins.json"
    )

    remote: list[dict] | None = None
    for url in (github_raw, gitee_raw):
        try:
            async with httpx.AsyncClient(timeout=10) as cli:
                r = await cli.get(url)
                r.raise_for_status()
                remote = r.json()
                break
        except Exception:
            if url == gitee_raw:
                raise HTTPException(
                    status_code=502,
                    detail="无法获取远程插件列表（GitHub 与 Gitee 均失败）"
                )
            continue

    try:
        local_res = await list_extensions()
        installed_repos = {
            ext.repository.strip().rstrip("/").lower()
            for ext in local_res.extensions
            if ext.repository
        }
    except Exception:
        installed_repos = set()

    def _with_status(p: dict):
            repo = p.get("repository", "").strip().rstrip("/").lower()
            parse = urlparse(p.get("repository", ""))
            path_parts = parse.path.strip("/").split("/")
            ext_id = f"{path_parts[0]}_{path_parts[1]}" if len(path_parts) >= 2 else p.get("id", "")
            
            return RemotePluginItem(
                id=ext_id,
                name=p.get("name", "未命名"),
                description=p.get("description", ""),
                author=p.get("author", "未知"),
                version=p.get("version", "1.0.0"),
                category=p.get("category", "Unknown"),
                repository=p.get("repository", ""),
                backupRepository=p.get("backupRepository", ""), 
                installed=repo in installed_repos,
            )

    return RemotePluginList(plugins=[_with_status(p) for p in remote])

# ------------------ 更新扩展 ------------------
@router.put("/{ext_id}/update")
async def update_extension(ext_id: str):
    target = Path(EXT_DIR) / ext_id
    if not target.exists():
        raise HTTPException(status_code=404, detail="扩展未安装")

    # 读取主备仓库地址
    pkg_file = target / "package.json"
    repos: list[str] = []
    if pkg_file.exists():
        try:
            meta = json.loads(pkg_file.read_text(encoding="utf-8"))
            if meta.get("repository"):
                repos.append(meta["repository"].strip().rstrip("/"))
            if meta.get("backupRepository"):
                repos.append(meta["backupRepository"].strip().rstrip("/"))
        except Exception:
            pass

    if not repos:
        raise HTTPException(status_code=400, detail="缺少 repository / backupRepository 字段")

    # 顺序尝试更新
    last_err: Exception | None = None
    for idx, repo in enumerate(repos):
        try:
            remote_name = "origin" if idx == 0 else "backup"
            # 确保 remote 存在
            subprocess.run(
                ["git", "-C", str(target), "remote", "add", remote_name, f"{repo}.git"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # 拉取更新
            subprocess.run(
                ["git", "-C", str(target), "pull", remote_name, "--ff-only"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return {"status": "updated", "remote": repo}
        except subprocess.CalledProcessError as e:
            last_err = e
            continue

    raise HTTPException(
        status_code=500,
        detail=f"主/备仓库均更新失败：{last_err and last_err.stderr}"
    )

# ------------------ Node.js 支持 ------------------
from py.node_runner import node_mgr
from aiohttp import ClientSession
import aiohttp

http_sess: ClientSession | None = None

@router.on_event("startup")
async def startup():
    global http_sess
    http_sess = ClientSession()

@router.on_event("shutdown")
async def shutdown():
    await http_sess.close()
    for ext_id in list(node_mgr.exts.keys()):
        await node_mgr.stop(ext_id)

@router.post("/{ext_id}/start-node")
async def start_node(ext_id: str):
    ext_dir = Path(EXT_DIR) / ext_id
    node_entry = ext_dir / "index.js"
    if not node_entry.exists():
        return {"mode": "static"}

    try:
        port = await node_mgr.start(ext_id)
        return {"mode": "node", "port": port}
    except Exception as e:
        return {"mode": "static"}

@router.post("/{ext_id}/stop-node")
async def stop_node(ext_id: str):
    await node_mgr.stop(ext_id)
    return {"status": "stopped"}

@router.api_route("/{ext_id}/node/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(ext_id: str, path: str, request: Request):
    if ext_id not in node_mgr.exts:
        raise HTTPException(404, "扩展未启动")
    port = node_mgr.exts[ext_id].port
    url = f"http://127.0.0.1:{port}/{path}"
    
    body = await request.body()
    async with http_sess.request(
        method=request.method,
        url=url,
        params=request.query_params,
        headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
        data=body
    ) as resp:
        content = await resp.read()
        return Response(content, status_code=resp.status, headers=dict(resp.headers))