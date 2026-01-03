import json
import os
import sys
import time
import asyncio
import aiosqlite
from pathlib import Path
from appdirs import user_data_dir

# ----------------- 1. 基础环境检测 (优化版) -----------------
APP_NAME = "Super-Agent-Party"
HOST = None
PORT = None

# 使用一次性检测，避免每次调用都读取文件
def _detect_docker():
    try:
        if os.path.exists('/.dockerenv'):
            return True
        cgroup_path = '/proc/self/cgroup'
        if os.path.exists(cgroup_path):
            with open(cgroup_path, 'rt', encoding='utf-8') as f:
                content = f.read()
                if 'docker' in content or 'container' in content:
                    return True
    except Exception:
        pass
    return False

# 将结果存为常量
IS_DOCKER = _detect_docker()

def in_docker():
    """兼容旧代码的函数调用，但速度极快"""
    return IS_DOCKER

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

base_path = get_base_path()

# ----------------- 2. 路径定义 (完整版) -----------------

if IS_DOCKER:
    USER_DATA_DIR = '/app/data'
else:
    USER_DATA_DIR = user_data_dir(APP_NAME, roaming=True)

# 确保主目录存在
os.makedirs(USER_DATA_DIR, exist_ok=True)

# --- 核心目录定义 ---
LOG_DIR = os.path.join(USER_DATA_DIR, 'logs')
MEMORY_CACHE_DIR = os.path.join(USER_DATA_DIR, 'memory_cache')
UPLOAD_FILES_DIR = os.path.join(USER_DATA_DIR, 'uploaded_files')
TOOL_TEMP_DIR = os.path.join(USER_DATA_DIR, 'tool_temp')
AGENT_DIR = os.path.join(USER_DATA_DIR, 'agents')
KB_DIR = os.path.join(USER_DATA_DIR, 'kb')
EXT_DIR = os.path.join(USER_DATA_DIR, "ext")
DEFAULT_ASR_DIR = os.path.join(USER_DATA_DIR, 'asr')
DEFAULT_EBD_DIR = os.path.join(USER_DATA_DIR, 'ebd')

# --- 配置文件路径 ---
SETTINGS_FILE = os.path.join(USER_DATA_DIR, 'settings.json')
CONFIG_BASE_PATH = os.path.join(base_path, 'config')
SETTINGS_TEMPLATE_FILE = os.path.join(CONFIG_BASE_PATH, 'settings_template.json')
BLOCKLIST_FILE = os.path.join(CONFIG_BASE_PATH, 'blocklist.json')

blocklist = []
if os.path.exists(BLOCKLIST_FILE):
    with open(BLOCKLIST_FILE, 'r', encoding='utf-8') as f:
        blocklist = json.load(f)
BLOCKLIST = set(blocklist)

# --- 静态资源路径 ---
DEFAULT_VRM_DIR = os.path.join(base_path, 'vrm')
STATIC_DIR = os.path.join(base_path, "static")

# --- 数据库路径 ---
DATABASE_PATH = os.path.join(USER_DATA_DIR, 'super_agent_party.db')
COVS_PATH = os.path.join(USER_DATA_DIR, "conversations.db")

# ----------------- 3. 初始化目录 (批量创建) -----------------
# 集中创建目录
dirs_to_create = [
    LOG_DIR, MEMORY_CACHE_DIR, UPLOAD_FILES_DIR, TOOL_TEMP_DIR,
    AGENT_DIR, KB_DIR, EXT_DIR, DEFAULT_ASR_DIR, DEFAULT_EBD_DIR,
    CONFIG_BASE_PATH
]
for d in dirs_to_create:
    os.makedirs(d, exist_ok=True)

# ----------------- 4. 移除阻塞操作：文件清理任务 -----------------

# 注意：请在主程序启动后调用 await clean_temp_files_task()
async def clean_temp_files_task():
    """异步清理临时文件，不拖慢启动速度"""
    try:
        await asyncio.to_thread(_clean_temp_files_sync)
    except Exception as e:
        print(f"[Warning] Temp file cleanup failed: {e}")

def _clean_temp_files_sync():
    if not os.path.exists(TOOL_TEMP_DIR): return
    # 7天
    threshold = time.time() - 7 * 24 * 60 * 60
    for filename in os.listdir(TOOL_TEMP_DIR):
        file_path = os.path.join(TOOL_TEMP_DIR, filename)
        try:
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < threshold:
                    os.remove(file_path)
        except Exception:
            pass

# ----------------- 5. 配置加载优化 -----------------

def configure_host_port(host, port):
    global HOST, PORT
    HOST = host
    PORT = port

def get_host():
    return HOST or "127.0.0.1"

def get_port():
    return PORT or 3456

# 缓存 default_settings
_cached_default_settings = None

def get_default_settings_sync():
    global _cached_default_settings
    if _cached_default_settings is not None:
        return _cached_default_settings
    
    if os.path.exists(SETTINGS_TEMPLATE_FILE):
        try:
            with open(SETTINGS_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                _cached_default_settings = json.load(f)
        except Exception:
            _cached_default_settings = {}
    else:
        _cached_default_settings = {}
    return _cached_default_settings

# --- 关键修复：恢复 init_db 函数名 ---
_db_init_done = False

async def init_db():
    """初始化设置数据库，增加状态位防止重复初始化"""
    global _db_init_done
    # 如果已经初始化过，直接返回，极大提升多次调用的速度
    if _db_init_done: 
        return
    
    Path(USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        await db.commit()
    _db_init_done = True

async def load_settings():
    await init_db() # 调用优化后的 init_db
    
    defaults = get_default_settings_sync().copy()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT data FROM settings WHERE id = 1') as cursor:
            row = await cursor.fetchone()
            if row:
                user_settings = json.loads(row[0])
                # 递归合并
                def merge_defaults(default_dict, target_dict):
                    for key, value in default_dict.items():
                        if key not in target_dict:
                            target_dict[key] = value
                        elif isinstance(value, dict) and isinstance(target_dict.get(key), dict):
                            merge_defaults(value, target_dict[key])
                
                merge_defaults(defaults, user_settings)
                return user_settings
            else:
                if IS_DOCKER:
                    defaults["isdocker"] = True
                await save_settings(defaults)
                return defaults

async def save_settings(settings):
    data = json.dumps(settings, ensure_ascii=False, indent=2)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('INSERT OR REPLACE INTO settings (id, data) VALUES (1, ?)', (data,))
        await db.commit()

# ----------------- 6. 对话存储优化 -----------------

# --- 关键修复：恢复 init_covs_db 函数名 ---
_covs_db_init_done = False

async def init_covs_db():
    """初始化对话数据库，增加状态位"""
    global _covs_db_init_done
    if _covs_db_init_done:
        return
        
    Path(USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(COVS_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        await db.commit()
    _covs_db_init_done = True

async def load_covs():
    try:
        await init_covs_db() # 调用优化后的 init_covs_db
        async with aiosqlite.connect(COVS_PATH) as db:
            async with db.execute('SELECT data FROM settings WHERE id = 1') as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                else:
                    default_covs = {"conversations": []}
                    await save_covs(default_covs)
                    return default_covs
    except Exception as e:
        print(f"Error loading conversations: {e}")
        return {"conversations": []}

async def save_covs(settings):
    data = json.dumps(settings, ensure_ascii=False, indent=2)
    async with aiosqlite.connect(COVS_PATH) as db:
        await db.execute('INSERT OR REPLACE INTO settings (id, data) VALUES (1, ?)', (data,))
        await db.commit()