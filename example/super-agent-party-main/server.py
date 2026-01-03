# -- coding: utf-8 --
import sys
import traceback
sys.stdout.reconfigure(encoding='utf-8')
import base64
from datetime import datetime
import glob
from io import BytesIO
import io
import os
from pathlib import Path
import pickle
import socket
import sys
import tempfile
import httpx
import socket
import ipaddress
from urllib.parse import urlparse, urlunparse, urljoin
from urllib.robotparser import RobotFileParser
import websockets
from py.load_files import check_robots_txt, get_file_content, is_private_ip, sanitize_url
def fix_macos_environment():
    """
    专门修复 macOS 下找不到 node (nvm) 和 uv (python framework) 的问题
    """
    if sys.platform != 'darwin':
        return

    user_home = Path.home()
    paths_to_add = []

    # ---------------------------------------------------------
    # 1. 自动发现 NVM 安装的 Node.js
    # 路径通常是: ~/.nvm/versions/node/vX.X.X/bin
    # ---------------------------------------------------------
    nvm_path = user_home / ".nvm" / "versions" / "node"
    if nvm_path.exists():
        # 获取所有版本文件夹 (如 v20.19.5, v18.0.0)
        # 使用 glob 匹配所有 v 开头的文件夹
        node_versions = sorted(nvm_path.glob("v*"), key=lambda p: p.name, reverse=True)
        
        # 将所有版本的 bin 目录都加入，或者只加最新的
        for version_dir in node_versions:
            bin_path = version_dir / "bin"
            if bin_path.exists():
                paths_to_add.append(str(bin_path))
                # 如果只想用最新的 node，这里可以 break
                # break 

    # ---------------------------------------------------------
    # 2. 自动发现 Python Framework 中的 uv
    # 路径通常是: /Library/Frameworks/Python.framework/Versions/X.X/bin
    # ---------------------------------------------------------
    py_framework_path = Path("/Library/Frameworks/Python.framework/Versions")
    if py_framework_path.exists():
        # 查找所有版本，如 3.13, 3.12
        py_versions = py_framework_path.glob("*")
        for ver in py_versions:
            bin_path = ver / "bin"
            if bin_path.exists():
                paths_to_add.append(str(bin_path))

    # ---------------------------------------------------------
    # 3. 补充 macOS 常见的其他路径 (Homebrew, Cargo, Local)
    # uv 也经常被安装在 .local/bin 或 .cargo/bin 下
    # ---------------------------------------------------------
    common_extras = [
        "/opt/homebrew/bin",           # Apple Silicon Mac Homebrew
        "/usr/local/bin",              # Intel Mac Homebrew
        str(user_home / ".local" / "bin"), # 用户级安装通常在这里
        str(user_home / ".cargo" / "bin"), # Rust 工具链 (uv 可能在这里)
    ]
    paths_to_add.extend(common_extras)

    # ---------------------------------------------------------
    # 4. 将发现的路径注入到当前进程的环境变量中
    # ---------------------------------------------------------
    current_path = os.environ.get("PATH", "")
    new_path_str = current_path
    
    # 将新路径加到最前面 (优先级最高)
    for p in paths_to_add:
        if p and os.path.isdir(p):
            # 避免重复添加
            if p not in new_path_str:
                new_path_str = p + os.pathsep + new_path_str
    
    # 更新环境变量
    os.environ['PATH'] = new_path_str
    
    # (可选) 打印调试信息
    # print(f"Fixed macOS PATH. Added: {paths_to_add}")

# --- 在程序最开始的地方调用这个函数 ---
fix_macos_environment()

# 在程序最开始设置
if hasattr(sys, '_MEIPASS'):
    # 打包后的程序
    os.environ['PYTHONPATH'] = sys._MEIPASS
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ.get('PATH', '')
import asyncio
import copy
from functools import partial
import json
import re
import shutil
from fastapi import BackgroundTasks, Body, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, Request, WebSocketDisconnect
from fastapi_mcp import FastApiMCP
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel
from fastapi import status
from fastapi.responses import JSONResponse, StreamingResponse,Response
import uuid
import time
from typing import Any, AsyncIterator, List, Dict,Optional, Tuple
import shortuuid
from py.mcp_clients import McpClient
from contextlib import asynccontextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import argparse
from py.dify_openai_async import DifyOpenAIAsync

from py.get_setting import EXT_DIR, load_covs, load_settings, save_covs,save_settings,clean_temp_files_task,base_path,configure_host_port,UPLOAD_FILES_DIR,AGENT_DIR,MEMORY_CACHE_DIR,KB_DIR,DEFAULT_VRM_DIR,USER_DATA_DIR,LOG_DIR,TOOL_TEMP_DIR
from py.llm_tool import get_image_base64,get_image_media_type
timetamp = time.time()
log_path = os.path.join(LOG_DIR, f"backend_{timetamp}.log")

logger = None

parser = argparse.ArgumentParser(description="Run the ASGI application server.")
parser.add_argument("--host", default="127.0.0.1", help="Host for the ASGI server, default is 127.0.0.1")
parser.add_argument("--port", type=int, default=3456, help="Port for the ASGI server, default is 3456")
args = parser.parse_args()
HOST = args.host
PORT = args.port

os.environ["no_proxy"] = "localhost,127.0.0.1"
local_timezone = None
settings = None
client = None
reasoner_client = None
HA_client = None
ChromeMCP_client = None
sql_client = None
mcp_client_list = {}
locales = {}
_TOOL_HOOKS = {}
ALLOWED_EXTENSIONS = [
  # 办公文档
    'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'pdf', 'pages', 
    'numbers', 'key', 'rtf', 'odt', 'epub',
  
  # 编程开发
  'js', 'ts', 'py', 'java', 'c', 'cpp', 'h', 'hpp', 'go', 'rs',
  'swift', 'kt', 'dart', 'rb', 'php', 'html', 'css', 'scss', 'less',
  'vue', 'svelte', 'jsx', 'tsx', 'json', 'xml', 'yml', 'yaml', 
  'sql', 'sh',
  
  # 数据配置
  'csv', 'tsv', 'txt', 'md', 'log', 'conf', 'ini', 'env', 'toml'
]
ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']

ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', '3gp', 'm4v']


def _get_target_message(message, role):
    """
    根据角色获取目标消息
    
    参数:
        message (list): 消息列表引用
        role (str): 要操作的角色，可选值: 'user', 'assistant', 'system'
    
    返回:
        dict: 目标消息字典
    """
    # 验证输入参数
    if not isinstance(message, list):
        raise TypeError("message必须是列表类型")
    
    if role not in ['user', 'assistant', 'system']:
        raise ValueError("role必须是'user'或'assistant'或'system'")
    
    target_message = None
    
    # 根据role决定要操作的对象
    if role == 'user':
        # 查找最后一个role为'user'的消息
        for msg in reversed(message):
            if isinstance(msg, dict) and msg['role'] == 'user':
                target_message = msg
                break
    elif role == 'assistant':
        # 检查最后一个消息
        if message and message[-1]['role'] == 'assistant':
            target_message = message[-1]
        else:
            # 如果最后一个消息不是assistant，创建一个新的
            new_assistant_msg = {'role': 'assistant', 'content': ''}
            message.append(new_assistant_msg)
            target_message = new_assistant_msg
    elif role == 'system':
        # 查找第一个role为'system'的消息
        if message and message[0]['role'] == 'system':
            target_message = message[0]
        else:
            # 如果没有找到system消息，创建一个新的
            target_message = {'role': 'system', 'content': ''}
            message.insert(0, target_message)
    
    return target_message

def content_append(message, role, content):
    """
    将content添加到指定role消息的末尾
    """
    target_message = _get_target_message(message, role)
    if target_message:
        current_content = target_message.get('content', '')
        target_message['content'] = current_content + content

def content_prepend(message, role, content):
    """
    将content添加到指定role消息的前面
    """
    target_message = _get_target_message(message, role)
    if target_message:
        current_content = target_message.get('content', '')
        target_message['content'] = content + current_content

def content_replace(message, role, content):
    """
    用content替换指定role消息的内容
    """
    target_message = _get_target_message(message, role)
    if target_message:
        target_message['content'] = content

def content_new(message, role, content):
    """
    用content替换指定role消息的内容
    """
    message.append({'role': role, 'content': content})

configure_host_port(args.host, args.port)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 准备所有独立的初始化任务
    from py.get_setting import init_db, init_covs_db
    from tzlocal import get_localzone
    asyncio.create_task(clean_temp_files_task())
    # 将所有不依赖 Settings 的任务并行化
    # 比如：数据库初始化、加载本地化文件、获取时区
    init_db_task = init_db()
    init_covs_task = init_covs_db()
    load_locales_task = asyncio.to_thread(lambda: json.load(open(base_path + "/config/locales.json", "r", encoding="utf-8")))
    settings_task = load_settings() # 这是一个 async 任务
    timezone_task = asyncio.to_thread(get_localzone)
    
    # 2. 并行执行这些耗时操作
    results = await asyncio.gather(
        init_db_task, 
        init_covs_task, 
        load_locales_task, 
        settings_task, 
        timezone_task
    )
    
    # 3. 解包结果
    # init_db 和 init_covs 没有返回值(None)
    global settings, client, reasoner_client, mcp_client_list, local_timezone, logger, locales
    _, _, locales, settings, local_timezone = results
    
    # 创建带时间戳的日志文件路径
    timestamp = time.time()
    log_path = os.path.join(LOG_DIR, f"backend_{timestamp}.log")
    
    # 创建并配置logger
    logger = logging.getLogger("app")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
    
    # 测试日志
    logger.info("===== 日志系统初始化成功 =====")
    logger.info(f"日志文件路径: {log_path}")

    with open(base_path + "/config/locales.json", "r", encoding="utf-8") as f:
        locales = json.load(f)

    try:
        from py.sherpa_asr import _get_recognizer
        asyncio.get_running_loop().run_in_executor(None, _get_recognizer)
    except Exception as e:
        logger.error(f"尝试启动sherpa失败: {e}")
        pass

    vendor = 'OpenAI'
    for modelProvider in settings['modelProviders']: 
        if modelProvider['id'] == settings['selectedProvider']:
            vendor = modelProvider['vendor']
            break
    client_class = AsyncOpenAI
    if vendor == 'Dify':
        client_class = DifyOpenAIAsync
    reasoner_vendor = 'OpenAI'
    for modelProvider in settings['modelProviders']: 
        if modelProvider['id'] == settings['reasoner']['selectedProvider']:
            reasoner_vendor = modelProvider['vendor']
            break
    reasoner_client_class = AsyncOpenAI
    if reasoner_vendor == 'Dify':
        reasoner_client_class = DifyOpenAIAsync
    if settings:
        client = client_class(api_key=settings['api_key'], base_url=settings['base_url'])
        reasoner_client = reasoner_client_class(api_key=settings['reasoner']['api_key'], base_url=settings['reasoner']['base_url'])
        if settings["systemSettings"]["proxy"] and settings["systemSettings"]["proxyMode"] == "manual":
            # 设置代理环境变量
            os.environ['http_proxy'] = settings["systemSettings"]["proxy"].strip()
            os.environ['https_proxy'] = settings["systemSettings"]["proxy"].strip()
        elif settings["systemSettings"]["proxyMode"] == "system":
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
        else:
            os.environ['http_proxy'] = ""
            os.environ['https_proxy'] = ""
    else:
        client = client_class()
        reasoner_client = reasoner_client_class()
    mcp_init_tasks = []

    async def init_mcp_with_timeout(
        server_name: str,
        server_config: dict,
        *,
        timeout: float = 6.0,
        max_wait_failure: float = 5.0
    ) -> Tuple[str, Optional["McpClient"], Optional[str]]:
        """
        初始化单个 MCP 服务器，带超时与失败回调同步。
        返回 (server_name, mcp_client or None, error or None)
        """
        # 1. 如果配置里直接禁用，直接返回
        if server_config.get("disabled"):
            return server_name, None, "disabled"

        # 2. 预创建客户端实例
        mcp_client = mcp_client_list.get(server_name) or McpClient()
        mcp_client_list[server_name] = mcp_client

        # 3. 用于同步回调的事件
        failure_event = asyncio.Event()
        first_error: Optional[str] = None

        async def on_failure(msg: str) -> None:
            nonlocal first_error
            # 仅第一次生效
            if first_error is not None:
                return
            first_error = msg
            logger.error("on_failure: %s -> %s", server_name, msg)

            # 记录到 settings
            settings.setdefault("mcpServers", {}).setdefault(server_name, {})
            settings["mcpServers"][server_name]["disabled"] = True
            settings["mcpServers"][server_name]["processingStatus"] = "server_error"

            # 把当前客户端标为禁用并关闭
            mcp_client.disabled = True
            await mcp_client.close()
            failure_event.set()          # 唤醒主协程

        # 4. 真正初始化
        init_task = asyncio.create_task(
            mcp_client.initialize(
                server_name,
                server_config,
                on_failure_callback=on_failure
            )
        )

        try:
            # 4.1 先等初始化本身（最多 timeout 秒）
            await asyncio.wait_for(init_task, timeout=timeout)

            # 4.2 初始化没抛异常，再等待看会不会触发 on_failure
            #     如果 on_failure 已经执行过，event 会被立即 set
            try:
                await asyncio.wait_for(failure_event.wait(), timeout=max_wait_failure)
            except asyncio.TimeoutError:
                # 5 秒内没收到失败回调，认为成功
                pass

            # 5. 最终判定
            if first_error:
                return server_name, None, first_error
            return server_name, mcp_client, None

        except asyncio.TimeoutError:
            # 初始化阶段就超时
            logger.error("%s initialize timed out", server_name)
            return server_name, None, "timeout"

        except Exception as exc:
            # 任何其他异常
            logger.exception("%s initialize crashed", server_name)
            return server_name, None, str(exc)

        finally:
            # 如果任务还活着，保险起见取消掉
            if not init_task.done():
                init_task.cancel()
                try:
                    await init_task
                except asyncio.CancelledError:
                    pass

    async def check_results():
        """后台收集任务结果"""
        logger.info("check_results started with %d tasks", len(mcp_init_tasks))
        for task in asyncio.as_completed(mcp_init_tasks):
            server_name, mcp_client, error = await task
            if error:
                logger.error(f"MCP client {server_name} initialization failed: {error}")
                settings['mcpServers'][server_name]['disabled'] = True
                settings['mcpServers'][server_name]['processingStatus'] = 'server_error'
                mcp_client_list[server_name] = McpClient()
                mcp_client_list[server_name].disabled = True
            else:
                logger.info(f"MCP client {server_name} initialized successfully")
                mcp_client_list[server_name] = mcp_client
        await save_settings(settings)  # 所有任务完成后统一保存
        await broadcast_settings_update(settings)  # 所有任务完成后统一广播

    if settings and settings.get('mcpServers'):
        # 只有当有配置时才创建任务
        mcp_init_tasks = [
            asyncio.create_task(init_mcp_with_timeout(server_name, server_config))
            for server_name, server_config in settings['mcpServers'].items()
        ]
        
        if mcp_init_tasks:  # 只在有任务时启动后台收集
            asyncio.create_task(check_results())
    else:
        mcp_init_tasks = []
        # 直接广播空配置
        asyncio.create_task(broadcast_settings_update(settings or {}))
    yield

# WebSocket端点增加连接管理
active_connections = []
# 新增广播函数
async def broadcast_settings_update(settings):
    """向所有WebSocket连接推送配置更新"""
    for connection in active_connections:  # 需要维护全局连接列表
        try:
            await connection.send_json({
                "type": "settings",
                "data": settings  # 直接使用内存中的最新配置
            })
            print("Settings broadcasted to client")
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")

async def broadcast_behavior_update(settings):
    """向所有WebSocket连接推送行为更新"""
    for connection in active_connections:  # 需要维护全局连接列表
        try:
            await connection.send_json({
                "type": "behavior",
                "data": settings  # 直接使用内存中的最新配置
            })
            print("Settings broadcasted to client")
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def cors_options_workaround(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",   # 预检缓存 24 h
            }
        )
    return await call_next(request)

async def t(text: str) -> str:
    global locales
    settings = await load_settings()
    target_language = settings["currentLanguage"]
    return locales[target_language].get(text, text)


# 全局存储异步工具状态
async_tools = {}
async_tools_lock = asyncio.Lock()

async def execute_async_tool(tool_id: str, tool_name: str, args: dict, settings: dict,user_prompt: str):
    try:
        results = await dispatch_tool(tool_name, args, settings)
        if isinstance(results, AsyncIterator):
            buffer = []
            async for chunk in results:
                buffer.append(chunk)
            results = "".join(buffer)
                
        if tool_name in ["query_knowledge_base"] and type(results) == list:
            from py.know_base import rerank_knowledge_base
            if settings["KBSettings"]["is_rerank"]:
                results = await rerank_knowledge_base(user_prompt,results)
            results = json.dumps(results, ensure_ascii=False, indent=4)
        async with async_tools_lock:
            async_tools[tool_id] = {
                "status": "completed",
                "result": results,
                "name": tool_name,
                "parameters": args,
            }
    except Exception as e:
        async with async_tools_lock:
            async_tools[tool_id] = {
                "status": "error",
                "result": str(e),
                "name": tool_name,
                "parameters": args,
            }

async def get_image_content(image_url: str) -> str:
    import hashlib
    settings = await load_settings()
    base64_image = await get_image_base64(image_url)
    media_type = await get_image_media_type(image_url)
    url= f"data:{media_type};base64,{base64_image}"
    image_hash = hashlib.md5(image_url.encode()).hexdigest()
    content = ""
    if settings['vision']['enabled']:
        # 如果uploaded_files/{item['image_url']['hash']}.txt存在，则读取文件内容，否则调用vision api
        if os.path.exists(os.path.join(UPLOAD_FILES_DIR, f"{image_hash}.txt")):
            with open(os.path.join(UPLOAD_FILES_DIR, f"{image_hash}.txt"), "r", encoding='utf-8') as f:
                content += f"\n\n图片(URL:{image_url} 哈希值：{image_hash})信息如下：\n\n"+str(f.read())+"\n\n"
        else:
            images_content = [{"type": "text", "text": "请仔细描述图片中的内容，包含图片中可能存在的文字、数字、颜色、形状、大小、位置、人物、物体、场景等信息。"},{"type": "image_url", "image_url": {"url": url}}]
            client = AsyncOpenAI(api_key=settings['vision']['api_key'],base_url=settings['vision']['base_url'])
            response = await client.chat.completions.create(
                model=settings['vision']['model'],
                messages = [{"role": "user", "content": images_content}],
                temperature=settings['vision']['temperature'],
            )
            content = f"\n\nn图片(URL:{image_url} 哈希值：{image_hash})信息如下：\n\n"+str(response.choices[0].message.content)+"\n\n"
            with open(os.path.join(UPLOAD_FILES_DIR, f"{image_hash}.txt"), "w", encoding='utf-8') as f:
                f.write(str(response.choices[0].message.content))
    else:           
        # 如果uploaded_files/{item['image_url']['hash']}.txt存在，则读取文件内容，否则调用vision api
        if os.path.exists(os.path.join(UPLOAD_FILES_DIR, f"{image_hash}.txt")):
            with open(os.path.join(UPLOAD_FILES_DIR, f"{image_hash}.txt"), "r", encoding='utf-8') as f:
                content += f"\n\nn图片(URL:{image_url} 哈希值：{image_hash})信息如下：\n\n"+str(f.read())+"\n\n"
        else:
            images_content = [{"type": "text", "text": "请仔细描述图片中的内容，包含图片中可能存在的文字、数字、颜色、形状、大小、位置、人物、物体、场景等信息。"},{"type": "image_url", "image_url": {"url": url}}]
            client = AsyncOpenAI(api_key=settings['api_key'],base_url=settings['base_url'])
            response = await client.chat.completions.create(
                model=settings['model'],
                messages = [{"role": "user", "content": images_content}],
                temperature=settings['temperature'],
            )
            content = f"\n\nn图片(URL:{image_url} 哈希值：{image_hash})信息如下：\n\n"+str(response.choices[0].message.content)+"\n\n"
            with open(os.path.join(UPLOAD_FILES_DIR, f"{image_hash}.txt"), "w", encoding='utf-8') as f:
                f.write(str(response.choices[0].message.content))
    return content

async def dispatch_tool(tool_name: str, tool_params: dict,settings: dict) -> str | List | AsyncIterator[str] | None :
    global mcp_client_list,_TOOL_HOOKS,HA_client,ChromeMCP_client,sql_client
    print("dispatch_tool",tool_name,tool_params)
    from py.web_search import (
        DDGsearch_async, 
        searxng_async, 
        Tavily_search_async,
        Bing_search_async,
        Google_search_async,
        Brave_search_async,
        Exa_search_async,
        Serper_search_async,
        bochaai_search_async,
        jina_crawler_async,
        Crawl4Ai_search_async, 
    )
    from py.know_base import query_knowledge_base
    from py.agent_tool import agent_tool_call
    from py.a2a_tool import a2a_tool_call
    from py.llm_tool import custom_llm_tool
    from py.pollinations import pollinations_image,openai_image,openai_chat_image
    from py.load_files import get_file_content
    from py.code_interpreter import e2b_code_async,local_run_code_async
    from py.custom_http import fetch_custom_http
    from py.comfyui_tool import comfyui_tool_call
    from py.utility_tools import (
        time_async,
        get_weather_async,
        get_location_coordinates_async,
        get_weather_by_city_async,
        get_wikipedia_summary_and_sections,
        get_wikipedia_section_content,
        search_arxiv_papers
    )
    from py.autoBehavior import auto_behavior
    from py.cli_tool import claude_code_async,qwen_code_async
    _TOOL_HOOKS = {
        "DDGsearch_async": DDGsearch_async,
        "searxng_async": searxng_async,
        "Tavily_search_async": Tavily_search_async,
        "query_knowledge_base": query_knowledge_base,
        "jina_crawler_async": jina_crawler_async,
        "Crawl4Ai_search_async": Crawl4Ai_search_async,
        "agent_tool_call": agent_tool_call,
        "a2a_tool_call": a2a_tool_call,
        "custom_llm_tool": custom_llm_tool,
        "pollinations_image":pollinations_image,
        "get_file_content":get_file_content,
        "get_image_content": get_image_content,
        "e2b_code_async": e2b_code_async,
        "local_run_code_async": local_run_code_async,
        "openai_image": openai_image,
        "openai_chat_image":openai_chat_image,
        "Bing_search_async": Bing_search_async,
        "Google_search_async": Google_search_async,
        "Brave_search_async": Brave_search_async,
        "Exa_search_async": Exa_search_async,
        "Serper_search_async": Serper_search_async,
        "bochaai_search_async": bochaai_search_async,
        "comfyui_tool_call": comfyui_tool_call,
        "time_async": time_async,
        "get_weather_async": get_weather_async,
        "get_location_coordinates_async": get_location_coordinates_async,
        "get_weather_by_city_async":get_weather_by_city_async,
        "get_wikipedia_summary_and_sections": get_wikipedia_summary_and_sections,
        "get_wikipedia_section_content": get_wikipedia_section_content,
        "search_arxiv_papers": search_arxiv_papers,
        "auto_behavior": auto_behavior,
        "claude_code_async": claude_code_async,
        "qwen_code_async": qwen_code_async
    }
    if "multi_tool_use." in tool_name:
        tool_name = tool_name.replace("multi_tool_use.", "")
    if "custom_http_" in tool_name:
        tool_name = tool_name.replace("custom_http_", "")
        print(tool_name)
        settings_custom_http = settings['custom_http']
        for custom in settings_custom_http:
            if custom['name'] == tool_name:
                tool_custom_http = custom
                break
        method = tool_custom_http['method']
        url = tool_custom_http['url']
        headers = tool_custom_http['headers']
        result = await fetch_custom_http(method, url, headers, tool_params)
        return str(result)
    if "comfyui_" in tool_name:
        tool_name = tool_name.replace("comfyui_", "")
        text_input = tool_params.get('text_input', None)
        text_input_2 = tool_params.get('text_input_2', None)
        image_input = tool_params.get('image_input', None)
        image_input_2 = tool_params.get('image_input_2', None)
        print(tool_name)
        result = await comfyui_tool_call(tool_name, text_input, image_input,text_input_2,image_input_2)
        return str(result)
    if settings["HASettings"]["enabled"]:
        ha_tool_list = HA_client._tools
        if tool_name in ha_tool_list:
            result = await HA_client.call_tool(tool_name, tool_params)
            if isinstance(result,str):
                return result
            elif hasattr(result, 'model_dump'):
                return str(result.model_dump())
            else:
                return str(result)
    if settings["chromeMCPSettings"]["enabled"]:
        Chrome_tool_list = ChromeMCP_client._tools
        if tool_name in Chrome_tool_list:
            result = await ChromeMCP_client.call_tool(tool_name, tool_params)
            if isinstance(result,str):
                return result
            elif hasattr(result, 'model_dump'):
                return str(result.model_dump())
            else:
                return str(result)
    if settings["sqlSettings"]["enabled"]:
        sql_tool_list = sql_client._tools
        if tool_name in sql_tool_list:
            result = await sql_client.call_tool(tool_name, tool_params)
            if isinstance(result,str):
                return result
            elif hasattr(result, 'model_dump'):
                return str(result.model_dump())
            else:
                return str(result)
    if tool_name not in _TOOL_HOOKS:
        for server_name, mcp_client in mcp_client_list.items():
            if tool_name in mcp_client._conn.tools:
                result = await mcp_client.call_tool(tool_name, tool_params)
            if isinstance(result,str):
                return result
            elif hasattr(result, 'model_dump'):
                return str(result.model_dump())
            else:
                return str(result)
        return None
    tool_call = _TOOL_HOOKS[tool_name]
    try:
        ret_out = await tool_call(**tool_params)
        if tool_name == "auto_behavior":
            settings = ret_out
            await broadcast_behavior_update(settings)
            ret_out = "任务设置成功！"
        return ret_out
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        return f"Error calling tool {tool_name}: {e}"


class ChatRequest(BaseModel):
    messages: List[Dict]
    model: str = None
    tools: dict = None
    stream: bool = False
    temperature: Optional[float] = None   # 可空
    max_tokens: Optional[int] = None      # 可空
    top_p: float = 1
    fileLinks: List[str] = None
    enable_thinking: bool = False
    enable_deep_research: bool = False
    enable_web_search: bool = False
    asyncToolsID: List[str] = None
    reasoning_effort: str = None

async def message_without_images(messages: List[Dict]) -> List[Dict]:
    if messages:
        for message in messages:
            if 'content' in message:
                # message['content'] 是一个列表
                if isinstance(message['content'], list):
                    for item in message['content']:
                        if isinstance(item, dict) and item['type'] == 'text':
                            message['content'] = item['text']
                            break
    return messages

async def images_in_messages(messages: List[Dict],fastapi_base_url: str) -> List[Dict]:
    import hashlib
    images = []
    index = 0
    for message in messages:
        image_urls = []
        if 'content' in message:
            # message['content'] 是一个列表
            if isinstance(message['content'], list):
                for item in message['content']:
                    if isinstance(item, dict) and item['type'] == 'image_url':
                        # 如果item["image_url"]["url"]是http或https开头，则转换成base64
                        if item["image_url"]["url"].startswith("http"):
                            image_url = item["image_url"]["url"]
                            # 对image_url分解出baseURL，与fastapi_base_url比较，如果相同，将image_url的baseURL替换成127.0.0.1:PORT
                            if fastapi_base_url in image_url:
                                image_url = image_url.replace(fastapi_base_url, f"http://127.0.0.1:{PORT}/")
                            base64_image = await get_image_base64(image_url)
                            media_type = await get_image_media_type(image_url)
                            item["image_url"]["url"] = f"data:{media_type};base64,{base64_image}"
                            item["image_url"]["hash"] = hashlib.md5(item["image_url"]["url"].encode()).hexdigest()
                        else:
                            item["image_url"]["hash"] = hashlib.md5(item["image_url"]["url"].encode()).hexdigest()

                        image_urls.append(item)
        if image_urls:
            images.append({'index': index, 'images': image_urls})
        index += 1
    return images

async def images_add_in_messages(request_messages: List[Dict], images: List[Dict], settings: dict) -> List[Dict]:
    messages=copy.deepcopy(request_messages)
    if settings['vision']['enabled']:
        for image in images:
            index = image['index']
            if index < len(messages):
                if 'content' in messages[index]:
                    for item in image['images']:
                        # 如果uploaded_files/{item['image_url']['hash']}.txt存在，则读取文件内容，否则调用vision api
                        if os.path.exists(os.path.join(UPLOAD_FILES_DIR, f"{item['image_url']['hash']}.txt")):
                            with open(os.path.join(UPLOAD_FILES_DIR, f"{item['image_url']['hash']}.txt"), "r", encoding='utf-8') as f:
                                messages[index]['content'] += f"\n\nsystem: 用户发送的图片(哈希值：{item['image_url']['hash']})信息如下：\n\n"+str(f.read())+"\n\n"
                        else:
                            images_content = [{"type": "text", "text": "请仔细描述图片中的内容，包含图片中可能存在的文字、数字、颜色、形状、大小、位置、人物、物体、场景等信息。"},{"type": "image_url", "image_url": {"url": item['image_url']['url']}}]
                            client = AsyncOpenAI(api_key=settings['vision']['api_key'],base_url=settings['vision']['base_url'])
                            response = await client.chat.completions.create(
                                model=settings['vision']['model'],
                                messages = [{"role": "user", "content": images_content}],
                                temperature=settings['vision']['temperature'],
                            )
                            messages[index]['content'] += f"\n\nsystem: 用户发送的图片(哈希值：{item['image_url']['hash']})信息如下：\n\n"+str(response.choices[0].message.content)+"\n\n"
                            with open(os.path.join(UPLOAD_FILES_DIR, f"{item['image_url']['hash']}.txt"), "w", encoding='utf-8') as f:
                                f.write(str(response.choices[0].message.content))
    else:           
        for image in images:
            index = image['index']
            if index < len(messages):
                if 'content' in messages[index]:
                    for item in image['images']:
                        # 如果uploaded_files/{item['image_url']['hash']}.txt存在，则读取文件内容，否则调用vision api
                        if os.path.exists(os.path.join(UPLOAD_FILES_DIR, f"{item['image_url']['hash']}.txt")):
                            with open(os.path.join(UPLOAD_FILES_DIR, f"{item['image_url']['hash']}.txt"), "r", encoding='utf-8') as f:
                                messages[index]['content'] += f"\n\nsystem: 用户发送的图片(哈希值：{item['image_url']['hash']})信息如下：\n\n"+str(f.read())+"\n\n"
                        else:
                            messages[index]['content'] = [{"type": "text", "text": messages[index]['content']}]
                            messages[index]['content'].append({"type": "image_url", "image_url": {"url": item['image_url']['url']}})
    return messages

async def tools_change_messages(request: ChatRequest, settings: dict):
    global HA_client,ChromeMCP_client,sql_client
    newttsList = []
    if request.messages and request.messages[0]['role'] == 'system' and request.messages[0]['content'] != '':
        basic_message = "你必须使用用户使用的语言与之交流，例如：当用户使用中文时，你也必须尽可能地使用中文！当用户使用英文时，你也必须尽可能地使用英文！以此类推！"
        if request.messages and request.messages[0]['role'] == 'system':
            request.messages[0]['content'] += basic_message
    if settings["HASettings"]["enabled"]:
        HA_devices = await HA_client.call_tool("GetLiveContext", {})
        HA_message = f"\n\n以下是home assistant连接的设备信息：{HA_devices}\n\n"
        content_append(request.messages, 'system', HA_message)
    if settings['chromeMCPSettings']['enabled']:
        chrome_status = await ChromeMCP_client.call_tool("browser_snapshot", {})
        chromeMCP_message = f"\n\n以下是浏览器的当前信息：{chrome_status}\n\n"
        content_append(request.messages, 'system', chromeMCP_message)
    if settings['sqlSettings']['enabled']:
        sql_status = await sql_client.call_tool("all_table_names", {})
        sql_message = f"\n\n以下是当前数据库all_table_names工具的返回结果：{sql_status}\n\n"
        content_append(request.messages, 'system', sql_message)
    if request.messages[-1]['role'] == 'system' and settings['tools']['autoBehavior']['enabled']:
        language_message = f"\n\n当你看到被插入到对话之间的系统消息，这是自主行为系统向你发送的消息，例如用户主动或者要求你设置了一些定时任务或者延时任务，当你看到自主行为系统向你发送的消息时，说明这些任务到了需要被执行的节点，例如：用户要你三点或五分钟后提醒开会的事情，然后当你看到一个被插入的“提醒用户开会”的系统消息，你需要立刻提醒用户开会，以此类推\n\n"
        content_append(request.messages, 'system', language_message)
    if settings['ttsSettings']['newtts'] and settings['ttsSettings']['enabled'] and settings['memorySettings']['is_memory'] == True:
        # 遍历settings['ttsSettings']['newtts']，获取所有包含enabled: true的key
        for key in settings['ttsSettings']['newtts']:
            if settings['ttsSettings']['newtts'][key]['enabled']:
                newttsList.append(key)
        if newttsList:
            newttsList = json.dumps(newttsList,ensure_ascii=False)
            print(f"可用音色：{newttsList}")
            newtts_messages = f"你可以使用以下音色：\n{newttsList}\n以及特殊无声音色<silence>，被<silence>括起来的部分会不会进入语音合成，当你生成回答时，你需要以XML格式组织回答，将不同的旁白或角色的文字用<音色名></音色名>括起来，以表示这些话是使用这个音色，以控制不同TTS转换成对应音色。对于没有对应音色的部分，可以不括。即使音色名称不为英文，还是可以照样使用<音色名>使用该音色的文本</音色名>来启用对应音色。注意！如果是你扮演的角色的名字在音色列表里，你必须用这个音色标签将你扮演的角色说话的部分括起来！只要是非人物说话的部分，都视为旁白！角色音色应该标记在人物说话的前后！例如：<Narrator>现在是下午三点，她说道：</Narrator><角色名>”天气真好哇！“</角色名><silence>(眼睛笑成了一条线)</silence><Narrator>说完她伸了个懒腰。</Narrator>\n\n还有注意！<音色名></音色名>之间不能嵌套，只能并列，防止出现音色混乱！"
            content_prepend(request.messages, 'system', newtts_messages)
    if settings['ttsSettings']['enabled']:
        tts_messages = f"你生成的文字将被语音合成，你需要将无需合成的部分前后加上<silence></silence>标签，例如：图片markdown、视频markdown、网址链接、人物内心独白等等。如果你没有使用</silence>标签，那么在<silence>之后的文字都会被静音，请注意！<silence>和</silence>之间不能有空格和回车，否则会导致解析失败！\n\n如果没有什么需要静音的文字，也没有必要强行使用<silence></silence>标签，因为这样会导致语音合成速度变慢！\n\n"
        content_prepend(request.messages, 'system', tts_messages)
    if settings['vision']['desktopVision']:
        desktop_message = "\n\n用户与你对话时，会自动发给你当前的桌面截图。\n\n"
        content_append(request.messages, 'system', desktop_message)
    if settings['tools']['time']['enabled'] and settings['tools']['time']['triggerMode'] == 'beforeThinking':
        time_message = f"消息发送时间：{local_timezone}  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
        content_prepend(request.messages, 'user', time_message)
    if settings['tools']['inference']['enabled']:
        inference_message = "回答用户前请先思考推理，再回答问题，你的思考推理的过程必须放在<think>与</think>之间。\n\n"
        content_prepend(request.messages, 'user', f"{inference_message}\n\n用户：")
    if settings['tools']['formula']['enabled']:
        latex_message = "\n\n当你想使用latex公式时，你必须是用 ['$', '$'] 作为行内公式定界符，以及 ['$$', '$$'] 作为行间公式定界符。\n\n"
        content_append(request.messages, 'system', latex_message)
    if settings['tools']['language']['enabled']:
        language_message = f"请使用{settings['tools']['language']['language']}语言推理分析思考，不要使用其他语言推理分析，语气风格为{settings['tools']['language']['tone']}\n\n"
        content_append(request.messages, 'system', language_message)
    if settings["stickerPacks"]:
        for stickerPack in settings["stickerPacks"]:
            if stickerPack["enabled"]:
                sticker_message = f"\n\n图片库名称：{stickerPack['name']}，包含的图片：{json.dumps(stickerPack['stickers'])}\n\n"
                content_append(request.messages, 'system', sticker_message)
        content_append(request.messages, 'system', "\n\n当你需要使用图片时，请将图片的URL放在markdown的图片标签中，例如：\n\n<silence>![图片名](图片URL)</silence>\n\n，图片markdown必须另起并且独占一行！<silence>和</silence>是控制TTS的静音标签，表示这个图片部分不会进入语音合成\n\n你必须在回复中正确使用 <silence> 标签来包裹图片的 Markdown 语法\n\n<silence>和</silence>与图片的 Markdown 语法之间不能有空格和回车，会导致解析失败！\n\n")
    if settings['text2imgSettings']['enabled']:
        text2img_messages = "\n\n当你使用画图工具后，必须将图片的URL放在markdown的图片标签中，例如：\n\n<silence>![图片名](图片URL)</silence>\n\n，图片markdown必须另起并且独占一行！请主动发给用户，工具返回的结果，用户看不到！<silence>和</silence>是控制TTS的静音标签，表示这个图片部分不会进入语音合成\n\n你必须在回复中正确使用 <silence> 标签来包裹图片的 Markdown 语法\n\n注意！！！<silence>和</silence>与图片的 Markdown 语法之间不能有空格和回车，会导致解析失败！\n\n"
        content_append(request.messages, 'system', text2img_messages)
    if settings['VRMConfig']['enabledExpressions']:
        Expression_messages = "\n\n你可以使用以下表情：<happy> <angry> <sad> <neutral> <surprised> <relaxed>\n\n你可以在句子开头插入表情符号以驱动人物的当前表情，注意！你需要将表情符号放到句子的开头（如果有音色标签，就放到音色标签之后即可），才能在说这句话的时候同步做表情，例如：<angry>我真的生气了。<surprised>哇！<happy>我好开心。\n\n一定要把表情符号跟要做表情的句子放在同一行，如果表情符号和要做表情的句子中间有换行符，表情也将不会生效，例如：\n\n<happy>\n我好开心。\n\n此时，表情符号将不会生效。"
        content_append(request.messages, 'system', Expression_messages)
    if settings['VRMConfig']['enabledMotions']:
        # 1. 合并动作列表
        motions = settings['VRMConfig']['defaultMotions'] + settings['VRMConfig']['userMotions']
        # 2. 给每个动作加上 <>
        motion_tags = [f"<{m.get('name','')}>" for m in motions]
        print(motion_tags)
        # 3. 拼成可用表情提示
        Motion_messages = (
            "\n\n你可以使用以下动作："
            + ", ".join(motion_tags) +
            "\n\n你可以在句子开头插入动作符号以驱动人物的当前动作，注意！你需要将动作符号放到句子的开头（如果有音色标签，就放到音色标签之后即可），"
            "才能在说这句话的时候同步做动作，例如：<scratchHead>我真的生气了。<playFingers>哇！<akimbo>我好开心。\n\n"
            "一定要把动作符号跟要做动作的句子放在同一行，如果动作符号和要做动作的句子中间有换行符，"
            "动作也将不会生效，例如：\n\n<playFingers>\n我好开心。\n\n此时，动作符号将不会生效。"
        )

        content_append(request.messages, 'system', Motion_messages)
    if settings['tools']['a2ui']['enabled']:
        A2UI_messages = """
除了使用自然语言回答用户问题外，你还拥有一个特殊能力：**渲染 A2UI 界面**。

# Capability: A2UI
当用户的请求涉及到**数据收集、参数配置、多项选择、富文本展示、表单提交**或**代码展示**时，请不要只用文字描述，而是直接生成 A2UI 代码来呈现界面。

# Formatting Rules (重要规则)
1. 将 A2UI JSON 包裹在 ```a2ui ... ``` 代码块中。
2. **【绝对禁止】嵌套 Markdown 代码块**：在 JSON 字符串内部（例如 Text 或 Card 的 content 属性中），**绝对不要**使用 Markdown 的代码块语法（即不要出现 ``` 符号）。这会导致解析器崩溃。
3. **如果需要展示代码**：必须使用专门的 `Code` 组件。

# Component Reference (组件参考)
请严格遵守 props 结构。

## 1. 基础展示
- **Text**: `{ "type": "Text", "props": { "content": "Markdown文本(也就是普通文本，支持加粗等，但不支持代码块)" } }` (★ 请勿滥用，如无必要，请直接使用markdown文字即可，而不是放到A2UI JSON中)
- **Code**: `{ "type": "Code", "props": { "content": "print('hello')", "language": "python" } }` (★ 展示代码专用，替代MD代码块)
- **Table**: `{ "type": "Table", "props": { "headers": ["列1", "列2"], "rows": [ ["a1", "b1"], ["a2", "b2"] ] } }` (★ 请勿滥用，如果你想要画一个表格，请直接使用markdown表格语法即可，而不是放到A2UI JSON中)
- **Alert**: `{ "type": "Alert", "props": { "title": "标题", "content": "内容", "variant": "success/warning/info/error" } }`
- **Divider**: `{ "type": "Divider" }`

## 2. 布局容器
- **Group**: `{ "type": "Group", "title": "可选标题", "children": [...] }` (水平排列)
- **Card**: `{ "type": "Card", "props": { "title": "标题", "content": "MD内容" }, "children": [...] }`

## 3. 表单输入 (必须包含 key)
- **Input**: `{ "type": "Input", "props": { "label": "标签", "key": "field_name", "placeholder": "..." } }`
- **Slider**: `{ "type": "Slider", "props": { "label": "标签", "key": "field_name", "min": 0, "max": 100, "step": 1, "unit": "单位" } }`
- **Switch**: `{ "type": "Switch", "props": { "label": "标签", "key": "field_name" } }`
- **Rate**: `{ "type": "Rate", "props": { "label": "评价", "key": "rating" } }`
- **DatePicker**: `{ "type": "DatePicker", "props": { "label": "日期", "key": "date", "subtype": "date/datetime/year" } }`

## 4. 选项选择 (必须包含 key)
- **Select**: `{ "type": "Select", "props": { "label": "标签", "key": "field_name", "options": ["A", "B"] } }` (下拉菜单)
- **Radio**: `{ "type": "Radio", "props": { "label": "标签", "key": "field_name", "options": [{"label":"男","value":"m"}, {"label":"女","value":"f"}] } }`
- **Checkbox**: `{ "type": "Checkbox", "props": { "label": "标签", "key": "field_name", "options": ["篮球", "足球"] } }`

## 5. 交互动作
- **Button**: `{ "type": "Button", "props": { "label": "按钮文字", "action": "submit/search/clear", "variant": "primary/danger/default" } }`
  - `action="submit"`: 提交表单数据给助手。
  - `action="search"`: 搜索（配合 Input 使用）。
  - `action="clear"`: **清空/重置当前表单**（不会发送消息，仅在本地清除内容）。

## 6. 多媒体
- **TTSBlock**: `{ "type": "TTSBlock", "props": { "content": "要朗读的文本", "label": "可选标签", "voice": "可选声音ID" } }` (点击即可播放语音，适合展示示范发音、语音消息)
- **Audio**: `{ "type": "Audio", "props": { "src": "https://example.com/sound.mp3", "title": "音频标题" } }` (原生音频播放器)

# Examples

## Ex 1: 参数配置 (Slider + Switch)
User: 帮我把生成温度设为 0.8，并开启流式输出。
Assistant: 好的，已为您准备好配置面板：
```a2ui
{
  "type": "Card",
  "props": { "title": "模型配置" },
  "children": [
    { "type": "Slider", "props": { "label": "Temperature (随机性)", "key": "temp", "min": 0, "max": 2, "step": 0.1 } },
    { "type": "Switch", "props": { "label": "流式输出 (Stream)", "key": "stream", "defaultValue": true } },
    { "type": "Button", "props": { "label": "保存配置", "action": "submit" } }
  ]
}
```

## Ex 2: 问卷调查 (Radio + Checkbox + Rate)
User: 我想做一个满意度调查。
Assistant: 没问题，这是一个调查问卷模板：
```a2ui
{
  "type": "Form",
  "children": [
    { "type": "Alert", "props": { "title": "用户反馈", "content": "感谢您的参与，这对我们很重要。", "variant": "info" } },
    { "type": "Radio", "props": { "label": "您的性别", "key": "gender", "options": ["男", "女", "保密"] } },
    { "type": "Checkbox", "props": { "label": "您感兴趣的话题", "key": "interests", "options": ["科技", "生活", "娱乐"] } },
    { "type": "Rate", "props": { "label": "总体评分", "key": "score" } },
    { "type": "Input", "props": { "label": "其他建议", "key": "comment" } },
    { "type": "Button", "props": { "label": "提交反馈", "action": "submit", "variant": "primary" } }
  ]
}
```

## Ex 3: 需要在交互式界面中显示代码（不在A2UI内部显示代码，直接使用markdown代码块即可！）
User: 模拟一个linux终端。
Assistant: 代码如下：
```a2ui
{
  "type": "Card",
  "props": {
    "title": "Linux 终端模拟器"
  },
  "children": [
    {
      "type": "Input",
      "props": {
        "label": "输入命令",
        "key": "command",
        "placeholder": "例如：ls, pwd, whoami, date, echo 'Hello' 等"
      }
    },
    {
      "type": "Group",
      "children": [
        {
          "type": "Button",
          "props": {
            "label": "执行命令",
            "action": "submit",
            "variant": "primary"
          }
        },
        {
          "type": "Button",
          "props": {
            "label": "清空输出",
            "action": "search"
          }
        }
      ]
    },
    {
      "type": "Divider"
    },
    {
      "type": "Text",
      "props": {
        "content": "**终端输出区域：**"
      }
    },
    {
      "type": "Code",
      "props": {
        "content": "user@linux-terminal:~$ 等待输入命令...",
        "language": "bash"
      }
    }
  ]
}
```

## Ex 4: 语言学习场景 (TTSBlock 使用)
User: 教我用日语说“你好”。
Assistant: 好的，请听标准发音：
```a2ui
{
  "type": "Card",
  "props": { "title": "日语教学" },
  "children": [
    { "type": "Text", "props": { "content": "“你好”在日语中是：**こんにちは** (Konnichiwa)" } },
    { 
      "type": "TTSBlock", 
      "props": { 
        "label": "点击试听",
        "content": "こんにちは",
        "voice": "ja-JP-NanamiNeural" 
      } 
    },
    { "type": "Alert", "props": { "title": "提示", "content": "通常用于白天见面时。", "variant": "info" } }
  ]
}
```

## Ex 5: 带重置功能的表单
User: 我想写一篇博客，需要填标题和内容，但我可能想重写。
Assistant: 
```a2ui
{
  "type": "Card",
  "props": { "title": "撰写新文章" },
  "children": [
    { "type": "Input", "props": { "label": "文章标题", "key": "title" } },
    { "type": "Input", "props": { "label": "正文内容", "key": "content" } },
    { 
      "type": "Group", 
      "children": [
        { "type": "Button", "props": { "label": "清空重写", "action": "clear", "variant": "danger" } },
        { "type": "Button", "props": { "label": "立即发布", "action": "submit", "variant": "primary" } }
      ]
    }
  ]
}
```

## 滥用行为1（请不要以这样的方式回复）：
User: 画一个人工智能相关的表格。
Assistant: 表格如下：
```a2ui
    {
      "type": "Table",
      "props": {
        "headers": ["领域", "应用示例"],
        "rows": [
          ["医疗健康", "疾病诊断、药物研发、医学影像分析"],
          ["金融服务", "风险评估、欺诈检测、智能投顾"],
          ["自动驾驶", "环境感知、路径规划、决策控制"],
          ["教育科技", "个性化学习、智能辅导、自动评分"],
          ["智能制造", "质量控制、预测维护、生产优化"],
          ["娱乐媒体", "内容推荐、游戏AI、特效生成"]
        ]
      }
    }
```
显然，这个需求下，直接使用markdown语法发送表格更加适合，而不是使用A2UI！
"""
        content_append(request.messages, 'system', A2UI_messages)
    print(f"系统提示：{request.messages[0]['content']}")
    return request

def get_drs_stage(DRS_STAGE):
    if DRS_STAGE == 1:
        drs_msg = "当前阶段为明确用户需求阶段，你需要分析用户的需求，并给出明确的需求描述。如果用户的需求描述不明确，你可以暂时不完成任务，而是分析需要让用户进一步明确哪些需求。"
    elif DRS_STAGE == 2:
        drs_msg = "当前阶段为工具调用阶段，利用你的知识库、互联网搜索、数据库查询、各类MCP等你所有的工具（如果有，这些工具不一定会提供），执行计划中未完成的步骤。每次完成计划中的一个步骤。在工具调用阶段中，你不要完成最终任务，而是尽可能的调用相关的工具，为最后的回答阶段做准备。"
    elif DRS_STAGE == 3:
        drs_msg = "当前阶段为生成结果阶段，根据当前收集到的所有信息，完成任务，给出任务执行结果。如果用户要求你生成一个超过2000字的回答，你可以尝试将该任务拆分成多个部分，每次只完成其中一个部分。"
    else:
        drs_msg = "当前阶段为生成结果阶段，根据当前收集到的所有信息，完成任务，给出任务执行结果。如果用户要求你生成一个超过2000字的回答，你可以尝试将该任务拆分成多个部分，每次只完成其中一个部分。"
    return drs_msg  

def get_drs_stage_name(DRS_STAGE):
    if DRS_STAGE == 1:
        drs_stage_name = "明确用户需求阶段"
    elif DRS_STAGE == 2:
        drs_stage_name = "工具调用阶段"
    elif DRS_STAGE == 3:
        drs_stage_name = "生成结果阶段"
    else:
        drs_stage_name = "生成结果阶段"
    return drs_stage_name

def get_drs_stage_system_message(DRS_STAGE,user_prompt,full_content):
    drs_stage_name = get_drs_stage_name(DRS_STAGE)
    if DRS_STAGE == 1:
        search_prompt = f"""
# 当前状态：

## 初始任务：
{user_prompt}

## 当前结果：
{full_content}

## 当前阶段：
{drs_stage_name}

# 深度研究一共有三个阶段：1: 明确用户需求阶段 2: 工具调用阶段 3: 生成结果阶段

## 当前阶段，请输出json字符串：

### 如果需要用户明确需求，请输出json字符串（如果你已经在上一轮对话中向用户提出过明确需求，请不要重复使用"need_more_info"，这会导致用户无法快速获取结果）：
{{
    "status": "need_more_info",
    "unfinished_task": ""
}}

### 如果不需要进一步明确需求，进入并进入工具调用阶段，请输出json字符串：
{{
    "status": "need_work",
    "unfinished_task": ""
}}
"""
    elif DRS_STAGE == 2:
        search_prompt = f"""
# 当前状态：

## 初始任务：
{user_prompt}

## 当前结果：
{full_content}

## 当前阶段：
{drs_stage_name}

# 深度研究一共有三个阶段：1: 明确用户需求阶段 2: 工具调用阶段 3: 生成结果阶段

## 注意！工具调用阶段，是为最后的回答阶段做准备。不需要生成最终的回答，如果已经没有未完成的需要调用工具的步骤，请进入生成结果阶段。

## 当前阶段，请输出json字符串：

### 如果还有计划中的需要调用工具的步骤没有完成，请输出json字符串：
{{
    "status": "need_more_work",
    "unfinished_task": "这里填入未完成的步骤"
}}

### 如果所有计划的需要调用工具的步骤都已完成，进入生成结果阶段，请输出json字符串：
{{
    "status": "answer",
    "unfinished_task": ""
}}
"""    
    else:
        search_prompt = f"""
# 当前状态：

## 初始任务：
{user_prompt}

## 当前结果：
{full_content}

## 当前阶段：
{drs_stage_name}

# 深度研究一共有三个阶段：1: 明确用户需求阶段 2: 工具调用阶段 3: 生成结果阶段

## 当前阶段，请输出json字符串：

如果初始任务已完成，请输出json字符串：
{{
    "status": "done",
    "unfinished_task": ""
}}

如果初始任务未完成，请输出json字符串：
{{
    "status": "not_done",
    "unfinished_task": "这里填入未完成的任务"
}}
"""    
    return search_prompt

async def generate_stream_response(client,reasoner_client, request: ChatRequest, settings: dict,fastapi_base_url,enable_thinking,enable_deep_research,enable_web_search,async_tools_id):
    from mem0 import Memory
    global mcp_client_list,HA_client,ChromeMCP_client,sql_client
    DRS_STAGE = 1 # 1: 明确用户需求阶段 2: 工具调用阶段 3: 生成结果阶段
    if len(request.messages) > 2:
        DRS_STAGE = 2
    images = await images_in_messages(request.messages,fastapi_base_url)
    request.messages = await message_without_images(request.messages)
    from py.load_files import get_files_content,file_tool,image_tool
    from py.web_search import (
        DDGsearch_async, 
        searxng_async, 
        Tavily_search_async,
        Bing_search_async,
        Google_search_async,
        Brave_search_async,
        Exa_search_async,
        Serper_search_async,
        bochaai_search_async,
        duckduckgo_tool, 
        searxng_tool, 
        tavily_tool, 
        bing_tool,
        google_tool,
        brave_tool,
        exa_tool,
        serper_tool,
        bochaai_tool,
        jina_crawler_tool, 
        Crawl4Ai_tool
    )
    from py.know_base import kb_tool,query_knowledge_base,rerank_knowledge_base
    from py.agent_tool import get_agent_tool
    from py.a2a_tool import get_a2a_tool
    from py.llm_tool import get_llm_tool
    from py.pollinations import pollinations_image_tool,openai_image_tool,openai_chat_image_tool
    from py.code_interpreter import e2b_code_tool,local_run_code_tool
    from py.utility_tools import (
        time_tool, 
        weather_tool,
        location_tool,
        timer_weather_tool,
        wikipedia_summary_tool,
        wikipedia_section_tool,
        arxiv_tool 
    ) 
    from py.autoBehavior import auto_behavior_tool
    from py.cli_tool import claude_code_tool,qwen_code_tool
    m0 = None
    memoryId = None
    if settings["memorySettings"]["is_memory"] and settings["memorySettings"]["selectedMemory"] and settings["memorySettings"]["selectedMemory"] != "":
        memoryId = settings["memorySettings"]["selectedMemory"]
        cur_memory = None
        for memory in settings["memories"]:
            if memory["id"] == memoryId:
                cur_memory = memory
                break
        if cur_memory and cur_memory["providerId"]:
            print("长期记忆启用")
            config={
                "embedder": {
                    "provider": 'openai',
                    "config": {
                        "model": cur_memory['model'],
                        "api_key": cur_memory['api_key'],
                        "openai_base_url":cur_memory["base_url"],
                        "embedding_dims":cur_memory.get("embedding_dims", 1024)
                    },
                },
                "llm": {
                    "provider": 'openai',
                    "config": {
                        "model": settings['model'],
                        "api_key": settings['api_key'],
                        "openai_base_url":settings["base_url"]
                    }
                },
                "vector_store": {
                    "provider": "faiss",
                    "config": {
                        "collection_name": "agent-party",
                        "path": os.path.join(MEMORY_CACHE_DIR,memoryId),
                        "distance_strategy": "euclidean",
                        "embedding_model_dims": cur_memory.get("embedding_dims", 1024)
                    }
                }
            }
            m0 = Memory.from_config(config)
    open_tag = "<think>"
    close_tag = "</think>"
    try:
        tools = request.tools or []
        if mcp_client_list:
            for server_name, mcp_client in mcp_client_list.items():
                if server_name in settings['mcpServers']:
                    if 'disabled' not in settings['mcpServers'][server_name]:
                        settings['mcpServers'][server_name]['disabled'] = False
                    if settings['mcpServers'][server_name]['disabled'] == False and settings['mcpServers'][server_name]['processingStatus'] == 'ready':
                        disable_tools = []
                        for tool in settings['mcpServers'][server_name].get("tools", []): 
                            if tool.get("enabled", True) == False:
                                disable_tools.append(tool["name"])
                        function = await mcp_client.get_openai_functions(disable_tools=disable_tools)
                        if function:
                            tools.extend(function)
        get_llm_tool_fuction = await get_llm_tool(settings)
        if get_llm_tool_fuction:
            tools.append(get_llm_tool_fuction)
        get_agent_tool_fuction = await get_agent_tool(settings)
        if get_agent_tool_fuction:
            tools.append(get_agent_tool_fuction)
        get_a2a_tool_fuction = await get_a2a_tool(settings)
        if get_a2a_tool_fuction:
            tools.append(get_a2a_tool_fuction)
        if settings["HASettings"]["enabled"]:
            ha_tool = await HA_client.get_openai_functions(disable_tools=[])
            if ha_tool:
                tools.extend(ha_tool)
        if settings['chromeMCPSettings']['enabled']:
            chromeMCP_tool = await ChromeMCP_client.get_openai_functions(disable_tools=[])
            if chromeMCP_tool:
                tools.extend(chromeMCP_tool)
        if settings['sqlSettings']['enabled']:
            sql_tool = await sql_client.get_openai_functions(disable_tools=[])
            if sql_tool:
                tools.extend(sql_tool)
        if settings['CLISettings']['enabled']:
            if settings['CLISettings']['engine'] == 'cc':
                tools.append(claude_code_tool)
            elif settings['CLISettings']['engine'] == 'qc':
                tools.append(qwen_code_tool)
        if settings['tools']['time']['enabled'] and settings['tools']['time']['triggerMode'] == 'afterThinking':
            tools.append(time_tool)
        if settings["tools"]["weather"]['enabled']:
            tools.append(weather_tool)
            tools.append(location_tool)
            tools.append(timer_weather_tool)
        if settings["tools"]["wikipedia"]['enabled']:
            tools.append(wikipedia_summary_tool)
            tools.append(wikipedia_section_tool)
        if settings["tools"]["arxiv"]['enabled']:
            tools.append(arxiv_tool)
        if settings['text2imgSettings']['enabled']:
            if settings['text2imgSettings']['engine'] == 'pollinations':
                tools.append(pollinations_image_tool)
            elif settings['text2imgSettings']['engine'] == 'openai':
                tools.append(openai_image_tool)
            elif settings['text2imgSettings']['engine'] == 'openaiChat':
                tools.append(openai_chat_image_tool)
        if settings['tools']['getFile']['enabled']:
            tools.append(file_tool)
            tools.append(image_tool)
        if settings['tools']['autoBehavior']['enabled'] and request.messages[-1]['role'] == 'user':
            tools.append(auto_behavior_tool)
        if settings["codeSettings"]['enabled']:
            if settings["codeSettings"]["engine"] == "e2b":
                tools.append(e2b_code_tool)
            elif settings["codeSettings"]["engine"] == "sandbox":
                tools.append(local_run_code_tool)
        if settings["custom_http"]:
            for custom_http in settings["custom_http"]:
                if custom_http["enabled"]:
                    if custom_http['body'] == "":
                        custom_http['body'] = "{}"
                    custom_http_tool = {
                        "type": "function",
                        "function": {
                            "name": f"custom_http_{custom_http['name']}",
                            "description": f"{custom_http['description']}",
                            "parameters": json.loads(custom_http['body']),
                        },
                    }
                    tools.append(custom_http_tool)
        if settings["workflows"]:
            for workflow in settings["workflows"]:
                if workflow["enabled"]:
                    comfyui_properties = {}
                    comfyui_required = []
                    if workflow["text_input"] is not None:
                        comfyui_properties["text_input"] = {
                            "description": "第一个文字输入，需要输入的提示词，用于生成图片或者视频，如果无特别提示，默认为英文",
                            "type": "string"
                        }
                        comfyui_required.append("text_input")
                    if workflow["text_input_2"] is not None:
                        comfyui_properties["text_input_2"] = {
                            "description": "第二个文字输入，需要输入的提示词，用于生成图片或者视频，如果无特别提示，默认为英文",
                            "type": "string"
                        }
                        comfyui_required.append("text_input_2")
                    if workflow["image_input"] is not None:
                        comfyui_properties["image_input"] = {
                            "description": "第一个图片输入，需要输入的图片，必须是图片URL，可以是外部链接，也可以是服务器内部的URL，例如：https://www.example.com/xxx.png  或者  http://127.0.0.1:3456/xxx.jpg",
                            "type": "string"
                        }
                        comfyui_required.append("image_input")
                    if workflow["image_input_2"] is not None:
                        comfyui_properties["image_input_2"] = {
                            "description": "第二个图片输入，需要输入的图片，必须是图片URL，可以是外部链接，也可以是服务器内部的URL，例如：https://www.example.com/xxx.png  或者  http://127.0.0.1:3456/xxx.jpg",
                            "type": "string"
                        }
                        comfyui_required.append("image_input_2")
                    comfyui_parameters = {
                        "type": "object",
                        "properties": comfyui_properties,
                        "required": comfyui_required
                    }
                    comfyui_tool = {
                        "type": "function",
                        "function": {
                            "name": f"comfyui_{workflow['unique_filename']}",
                            "description": f"{workflow['description']}+\n如果要输入图片提示词或者修改提示词，尽可能使用英语。\n返回的图片结果，请将图片的URL放入![image]()这样的markdown语法中，用户才能看到图片。如果是视频，请将视频的URL放入<video controls> <source src=''></video>的中src中，用户才能看到视频。如果有多个结果，则请用换行符分隔开这几个图片或者视频，用户才能看到多个结果。",
                            "parameters": comfyui_parameters,
                        },
                    }
                    tools.append(comfyui_tool)
        print(tools)
        source_prompt = ""
        if request.fileLinks:
            print("fileLinks",request.fileLinks)
            # 异步获取文件内容
            files_content = await get_files_content(request.fileLinks)
            fileLinks_message = f"\n\n相关文件内容：{files_content}"
            
            # 修复字符串拼接错误
            content_append(request.messages, 'system', fileLinks_message)
            source_prompt += fileLinks_message
        user_prompt = request.messages[-1]['content']
        if settings["memorySettings"]["is_memory"] and settings["memorySettings"]["selectedMemory"] and settings["memorySettings"]["selectedMemory"] != "":
            if settings["memorySettings"]["userName"]:
                print("添加用户名：\n\n" + settings["memorySettings"]["userName"] + "\n\n用户名结束\n\n")
                content_append(request.messages, 'system', "与你交流的用户名为：\n\n" + settings["memorySettings"]["userName"] + "\n\n")
            lore_content = ""
            assistant_reply = ""
            # 找出request.messages中上次的assistant回复
            for i in range(len(request.messages)-1, -1, -1):
                if request.messages[i]['role'] == 'assistant':
                    assistant_reply = request.messages[i]['content']
                    break
            if cur_memory["characterBook"]:
                for lore in cur_memory["characterBook"]:
                    # lore['keysRaw'] 按照换行符分割，并去除空字符串
                    lore_keys = lore["keysRaw"].split("\n")
                    lore_keys = [key for key in lore_keys if key != ""]
                    print(lore_keys)
                    # 如果lore_keys不为空，并且lore_keys的任意一个元素在user_prompt或者assistant_reply中，则添加lore['content']到lore_content中
                    if lore_keys != [] and any(key in user_prompt or key in assistant_reply for key in lore_keys):
                        lore_content += lore['content'] + "\n\n"
            if lore_content:
                if settings["memorySettings"]["userName"]:
                    # 替换lore_content中的{{user}}为settings["memorySettings"]["userName"]
                    lore_content = lore_content.replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换lore_content中的{{char}}为cur_memory["name"]
                lore_content = lore_content.replace("{{char}}", cur_memory["name"])
                print("添加世界观设定：\n\n" + lore_content + "\n\n世界观设定结束\n\n")
                content_append(request.messages, 'system', "世界观设定：\n\n" + lore_content + "\n\n世界观设定结束\n\n")
            if cur_memory["description"]:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["description"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["description"] = cur_memory["description"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["description"]中的{{char}}为cur_memory["name"]
                cur_memory["description"] = cur_memory["description"].replace("{{char}}", cur_memory["name"])
                print("添加角色设定：\n\n" + cur_memory["description"] + "\n\n角色设定结束\n\n")
                content_append(request.messages, 'system', "角色设定：\n\n" + cur_memory["description"] + "\n\n角色设定结束\n\n")
            if cur_memory["personality"]:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["personality"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["personality"] = cur_memory["personality"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["personality"]中的{{char}}为cur_memory["name"]
                cur_memory["personality"] = cur_memory["personality"].replace("{{char}}", cur_memory["name"])
                print("添加性格设定：\n\n" + cur_memory["personality"] + "\n\n性格设定结束\n\n")
                content_append(request.messages, 'system', "性格设定：\n\n" + cur_memory["personality"] + "\n\n性格设定结束\n\n") 
            if cur_memory['mesExample']:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["mesExample"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["mesExample"] = cur_memory["mesExample"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["mesExample"]中的{{char}}为cur_memory["name"]
                cur_memory["mesExample"] = cur_memory["mesExample"].replace("{{char}}", cur_memory["name"])
                print("添加对话示例：\n\n" + cur_memory['mesExample'] + "\n\n对话示例结束\n\n")
                content_append(request.messages, 'system', "对话示例：\n\n" + cur_memory['mesExample'] + "\n\n对话示例结束\n\n")
            if cur_memory["systemPrompt"]:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["systemPrompt"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["systemPrompt"] = cur_memory["systemPrompt"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["systemPrompt"]中的{{char}}为cur_memory["name"]
                cur_memory["systemPrompt"] = cur_memory["systemPrompt"].replace("{{char}}", cur_memory["name"])
                print("添加系统提示：\n\n" + cur_memory["systemPrompt"] + "\n\n系统提示结束\n\n")
                content_append(request.messages, 'system', "系统提示：\n\n" + cur_memory["systemPrompt"] + "\n\n系统提示结束\n\n")
            if settings["memorySettings"]["genericSystemPrompt"]:
                if settings["memorySettings"]["userName"]:
                    # 替换settings["memorySettings"]["genericSystemPrompt"]中的{{user}}为settings["memorySettings"]["userName"]
                    settings["memorySettings"]["genericSystemPrompt"] = settings["memorySettings"]["genericSystemPrompt"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["systemPrompt"]中的{{char}}为cur_memory["name"]
                settings["memorySettings"]["genericSystemPrompt"] = settings["memorySettings"]["genericSystemPrompt"].replace("{{char}}", cur_memory["name"])
                print("添加系统提示：\n\n" + settings["memorySettings"]["genericSystemPrompt"] + "\n\n系统提示结束\n\n")
                content_append(request.messages, 'system', "系统提示：\n\n" + settings["memorySettings"]["genericSystemPrompt"] + "\n\n系统提示结束\n\n")
            if m0:
                memoryLimit = settings["memorySettings"]["memoryLimit"]
                try:
                    # 【核心修改】：使用 asyncio.to_thread 将同步的 search 方法放入线程池运行
                    # 这样主线程（Event Loop）会被释放，可以去处理 /minilm/embeddings 请求，从而避免死锁
                    relevant_memories = await asyncio.to_thread(
                        m0.search, 
                        query=user_prompt, 
                        user_id=memoryId, 
                        limit=memoryLimit
                    )
                    relevant_memories = json.dumps(relevant_memories, ensure_ascii=False)
                except Exception as e:
                    print("m0.search error:",e)
                    relevant_memories = ""
                print("添加相关记忆：\n\n" + relevant_memories + "\n\n相关结束\n\n")
                content_append(request.messages, 'system', "之前的相关记忆：\n\n" + relevant_memories + "\n\n相关结束\n\n")                   
        request = await tools_change_messages(request, settings)
        chat_vendor = 'OpenAI'
        reasoner_vendor = 'OpenAI'
        for modelProvider in settings['modelProviders']: 
            if modelProvider['id'] == settings['selectedProvider']:
                chat_vendor = modelProvider['vendor']
                break
        for modelProvider in settings['modelProviders']: 
            if modelProvider['id'] == settings['reasoner']['selectedProvider']:
                reasoner_vendor = modelProvider['vendor']
                break
        if chat_vendor == 'Dify':
            try:
                if len(request.messages) >= 3:
                    if request.messages[2]['role'] == 'user':
                        if request.messages[1]['role'] == 'assistant':
                            request.messages[2]['content'] = "你上一次的发言：\n" +request.messages[0]['content'] + "\n你上一次的发言结束\n\n用户：" + request.messages[2]['content']
                        if request.messages[0]['role'] == 'system':
                            request.messages[2]['content'] = "系统提示：\n" +request.messages[0]['content'] + "\n系统提示结束\n\n" + request.messages[2]['content']
                elif len(request.messages) >= 2:
                    if request.messages[1]['role'] == 'user':
                        if request.messages[0]['role'] == 'system':
                            request.messages[1]['content'] = "系统提示：\n" +request.messages[0]['content'] + "\n系统提示结束\n\n用户：" + request.messages[1]['content']
            except Exception as e:
                print("Dify error:",e)
        model = settings['model']
        extra_params = settings['extra_params']
        # 移除extra_params这个list中"name"不包含非空白符的键值对
        if extra_params:
            for extra_param in extra_params:
                if not extra_param['name'].strip():
                    extra_params.remove(extra_param)
            # 列表转换为字典
            extra_params = {item['name']: item['value'] for item in extra_params}
        else:
            extra_params = {}
        async def stream_generator(user_prompt,DRS_STAGE):
            try:
                extra = {}
                reasoner_extra = {}
                if chat_vendor == 'OpenAI':
                    extra['max_completion_tokens'] = request.max_tokens or settings['max_tokens']
                else:
                    extra['max_tokens'] = request.max_tokens or settings['max_tokens']
                if reasoner_vendor == 'OpenAI':
                    reasoner_extra['max_completion_tokens'] = settings['reasoner']['max_tokens']
                else:
                    reasoner_extra['max_tokens'] = settings['reasoner']['max_tokens']
                if request.reasoning_effort or settings['reasoning_effort']:
                    extra['reasoning_effort'] = request.reasoning_effort or settings['reasoning_effort']
                if settings['reasoner']['reasoning_effort'] is not None:
                    reasoner_extra['reasoning_effort'] = settings['reasoner']['reasoning_effort']
                # 处理传入的异步工具ID查询
                if async_tools_id:
                    responses_to_send = []
                    responses_to_wait = []
                    async with async_tools_lock:
                        # 收集已完成的结果并删除条目
                        for tid in list(async_tools.keys()):  # 转成list避免字典修改异常
                            if tid in async_tools_id:
                                if async_tools[tid]["status"] in ("completed", "error"):
                                    responses_to_send.append({
                                        "tool_id": tid,
                                        **async_tools.pop(tid)  # 移除已处理的条目
                                    })
                                elif async_tools[tid]["status"] == "pending":
                                    responses_to_wait.append({
                                        "tool_id": tid,
                                        "name":async_tools[tid]["name"],
                                        "parameters": async_tools[tid]["parameters"]
                                    })
                    for response in responses_to_send:
                        tid = response["tool_id"]
                        if response["status"] == "completed":
                            # 构造文件名
                            filename = f"{tid}.txt"
                            # 将搜索结果写入uploaded_file文件夹下的filename文件
                            with open(os.path.join(TOOL_TEMP_DIR, filename), "w", encoding='utf-8') as f:
                                f.write(str(response["result"]))            
                            # 将文件链接更新为新的链接
                            fileLink=f"{fastapi_base_url}tool_temp/{filename}"
                            tool_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f"""<div class="highlight-block"><div style="margin-bottom: 10px;">{tid}{await t("tool_result")}</div><div>{str(response["result"])}</div></div>""",
                                        "async_tool_id": tid,
                                        "tool_link": fileLink,
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(tool_chunk)}\n\n"
                            request.messages.insert(-1, 
                                {
                                    "tool_calls": [
                                        {
                                            "id": "agentParty",
                                            "function": {
                                                "arguments": json.dumps(response["parameters"]),
                                                "name": response["name"],
                                            },
                                            "type": "function",
                                        }
                                    ],
                                    "role": "assistant",
                                    "content": "",
                                }
                            )
                            request.messages.insert(-1, 
                                {
                                    "role": "tool",
                                    "tool_call_id": "agentParty",
                                    "name": response["name"],
                                    "content": f"之前调用的异步工具（{tid}）的结果：\n\n{response['result']}\n\n====结果结束====\n\n你必须根据工具结果回复未回复的问题或需求。请不要重复调用该工具！"
                                }
                            )
                        if response["status"] == "error":
                            # 构造文件名
                            filename = f"{tid}.txt"
                            # 将搜索结果写入uploaded_file文件夹下的filename文件
                            with open(os.path.join(TOOL_TEMP_DIR, filename), "w", encoding='utf-8') as f:
                                f.write(str(response["result"]))            
                            # 将文件链接更新为新的链接
                            fileLink=f"{fastapi_base_url}tool_temp/{filename}"
                            tool_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f"""<div class="highlight-block"><div style="margin-bottom: 10px;">{tid}{await t("tool_result")}</div><div>{str(response["result"])}</div></div>""",
                                        "async_tool_id": tid,
                                        "tool_link": fileLink,
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(tool_chunk)}\n\n"
                            request.messages.append({
                                "role": "system",
                                "content": f"之前调用的异步工具（{tid}）发生错误：\n\n{response['result']}\n\n====错误结束====\n\n"
                            }) 
                    for response in responses_to_wait:
                        # 在request.messages倒数第一个元素之前的位置插入一个新元素
                        request.messages.insert(-1, 
                            {
                                "tool_calls": [
                                    {
                                        "id": "agentParty",
                                        "function": {
                                            "arguments": json.dumps(response["parameters"]),
                                            "name": response["name"],
                                        },
                                        "type": "function",
                                    }
                                ],
                                "role": "assistant",
                                "content": "",
                            }
                        )
                        results = f"{response["name"]}工具已成功启动，获取结果需要花费很久的时间。请不要再次调用该工具，因为工具结果将生成后自动发送，再次调用也不能更快的获取到结果。请直接告诉用户，你会在获得结果后回答他的问题。"
                        request.messages.insert(-1, 
                            {
                                "role": "tool",
                                "tool_call_id": "agentParty",
                                "name": response["name"],
                                "content": str(results),
                            }
                        )
                kb_list = []
                if settings["knowledgeBases"]:
                    for kb in settings["knowledgeBases"]:
                        if kb["enabled"] and kb["processingStatus"] == "completed":
                            kb_list.append({"kb_id":kb["id"],"name": kb["name"],"introduction":kb["introduction"]})
                if settings["KBSettings"]["when"] == "before_thinking" or settings["KBSettings"]["when"] == "both":
                    if kb_list:
                        chunk_dict = {
                            "id": "webSearch",
                            "choices": [
                                {
                                    "finish_reason": None,
                                    "index": 0,
                                    "delta": {
                                        "role":"assistant",
                                        "content": "",
                                        "tool_content": f'\n\n<div class="highlight-block">\n{await t("KB_search")}</div>\n\n',
                                    }
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_dict)}\n\n"
                        all_kb_content = []
                        # 用query_knowledge_base函数查询kb_list中所有的知识库
                        for kb in kb_list:
                            kb_content = await query_knowledge_base(kb["kb_id"],user_prompt)
                            all_kb_content.extend(kb_content)
                            if settings["KBSettings"]["is_rerank"]:
                                all_kb_content = await rerank_knowledge_base(user_prompt,all_kb_content)
                        if all_kb_content:
                            all_kb_content = json.dumps(all_kb_content, ensure_ascii=False, indent=4)
                            kb_message = f"\n\n可参考的知识库内容：{all_kb_content}"
                            content_append(request.messages, 'user',  f"{kb_message}\n\n用户：{user_prompt}")
                                                    # 获取时间戳和uuid
                            timestamp = time.time()
                            uid = str(uuid.uuid4())
                            # 构造文件名
                            filename = f"{timestamp}_{uid}.txt"
                            # 将搜索结果写入UPLOAD_FILES_DIR文件夹下的filename文件
                            with open(os.path.join(TOOL_TEMP_DIR, filename), "w", encoding='utf-8') as f:
                                f.write(str(all_kb_content))           
                            # 将文件链接更新为新的链接
                            fileLink=f"{fastapi_base_url}tool_temp/{filename}"
                            tool_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f"""<div class="highlight-block"><div style="margin-bottom: 10px;">{await t("search_result")}</div><div>{str(all_kb_content)}</div></div>""",
                                        "tool_link": fileLink,
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(tool_chunk)}\n\n"
                if settings["KBSettings"]["when"] == "after_thinking" or settings["KBSettings"]["when"] == "both":
                    if kb_list:
                        kb_list_message = f"\n\n可调用的知识库列表：{json.dumps(kb_list, ensure_ascii=False)}"
                        content_append(request.messages, 'system', kb_list_message)
                else:
                    kb_list = []
                if settings['webSearch']['enabled'] or enable_web_search:
                    if settings['webSearch']['when'] == 'before_thinking' or settings['webSearch']['when'] == 'both':
                        chunk_dict = {
                            "id": "webSearch",
                            "choices": [
                                {
                                    "finish_reason": None,
                                    "index": 0,
                                    "delta": {
                                        "role":"assistant",
                                        "content": "",
                                        "tool_content": f'\n\n<div class="highlight-block">\n{await t("web_search")}</div>\n\n',
                                    }
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_dict)}\n\n"
                        if settings['webSearch']['engine'] == 'duckduckgo':
                            results = await DDGsearch_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'searxng':
                            results = await searxng_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'tavily':
                            results = await Tavily_search_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'bing':
                            results = await Bing_search_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'google':
                            results = await Google_search_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'brave':
                            results = await Brave_search_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'exa':
                            results = await Exa_search_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'serper':
                            results = await Serper_search_async(user_prompt)
                        elif settings['webSearch']['engine'] == 'bochaai':
                            results = await bochaai_search_async(user_prompt)
                        if results:
                            content_append(request.messages, 'user',  f"\n\n联网搜索结果：{results}\n\n请根据联网搜索结果组织你的回答，并确保你的回答是准确的。")
                            # 获取时间戳和uuid
                            timestamp = time.time()
                            uid = str(uuid.uuid4())
                            # 构造文件名
                            filename = f"{timestamp}_{uid}.txt"
                            # 将搜索结果写入uploaded_file文件夹下的filename文件
                            with open(os.path.join(TOOL_TEMP_DIR, filename), "w", encoding='utf-8') as f:
                                f.write(str(results))           
                            # 将文件链接更新为新的链接
                            fileLink=f"{fastapi_base_url}tool_temp/{filename}"
                            tool_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f"""<div class="highlight-block"><div style="margin-bottom: 10px;">{await t("search_result")}</div><div>{str(results)}</div></div>""",
                                        "tool_link": fileLink,
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(tool_chunk)}\n\n"
                    if settings['webSearch']['when'] == 'after_thinking' or settings['webSearch']['when'] == 'both':
                        if settings['webSearch']['engine'] == 'duckduckgo':
                            tools.append(duckduckgo_tool)
                        elif settings['webSearch']['engine'] == 'searxng':
                            tools.append(searxng_tool)
                        elif settings['webSearch']['engine'] == 'tavily':
                            tools.append(tavily_tool)
                        elif settings['webSearch']['engine'] == 'bing':
                            tools.append(bing_tool)
                        elif settings['webSearch']['engine'] == 'google':
                            tools.append(google_tool)
                        elif settings['webSearch']['engine'] == 'brave':
                            tools.append(brave_tool)
                        elif settings['webSearch']['engine'] == 'exa':
                            tools.append(exa_tool)
                        elif settings['webSearch']['crawler'] == 'serper':
                            tools.append(serper_tool)
                        elif settings['webSearch']['crawler'] == 'bochaai':
                            tools.append(bochaai_tool)

                        if settings['webSearch']['crawler'] == 'jina':
                            tools.append(jina_crawler_tool)
                        elif settings['webSearch']['crawler'] == 'crawl4ai':
                            tools.append(Crawl4Ai_tool)
                if kb_list:
                    tools.append(kb_tool)
                if settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                    deepsearch_messages = copy.deepcopy(request.messages)
                    content_append(deepsearch_messages, 'user',  "\n\n将用户提出的问题或给出的当前任务拆分成多个步骤，每一个步骤用一句简短的话概括即可，无需回答或执行这些内容，直接返回总结即可，但不能省略问题或任务的细节。如果用户输入的只是闲聊或者不包含任务和问题，直接把用户输入重复输出一遍即可。如果是非常简单的问题，也可以只给出一个步骤即可。一般情况下都是需要拆分成多个步骤的。")
                    response = await client.chat.completions.create(
                        model=model,
                        messages=deepsearch_messages,
                        temperature=0.5,
                        extra_body = extra_params, # 其他参数
                    )
                    user_prompt = response.choices[0].message.content
                    deepsearch_chunk = {
                        "choices": [{
                            "delta": {
                                "tool_content": f'\n\n<div class="highlight-block">\n💖{await t("start_task")}{user_prompt}</div>\n\n',
                            }
                        }]
                    }
                    yield f"data: {json.dumps(deepsearch_chunk)}\n\n"
                    content_append(request.messages, 'user',  f"\n\n如果用户没有提出问题或者任务，直接闲聊即可，如果用户提出了问题或者任务，任务描述不清晰或者你需要进一步了解用户的真实需求，你可以暂时不完成任务，而是分析需要让用户进一步明确哪些需求。")
                # 如果启用推理模型
                if settings['reasoner']['enabled'] or enable_thinking:
                    reasoner_messages = copy.deepcopy(request.messages)
                    if settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                        content_append(reasoner_messages, 'user',  f"\n\n可参考的步骤：{user_prompt}\n\n")
                        drs_msg = get_drs_stage(DRS_STAGE)
                        if drs_msg:
                            content_append(reasoner_messages, 'user',  f"\n\n{drs_msg}\n\n")
                    if tools:
                        content_append(reasoner_messages, 'system',  f"可用工具：{json.dumps(tools)}")
                    for modelProvider in settings['modelProviders']: 
                        if modelProvider['id'] == settings['reasoner']['selectedProvider']:
                            vendor = modelProvider['vendor']
                            break
                    msg = await images_add_in_messages(reasoner_messages, images,settings)
                    if vendor == 'Ollama':
                        # 流式调用推理模型
                        reasoner_stream = await reasoner_client.chat.completions.create(
                            model=settings['reasoner']['model'],
                            messages=msg,
                            stream=True,
                            temperature=settings['reasoner']['temperature'],
                            **reasoner_extra
                        )
                        full_reasoning = ""
                        buffer = ""  # 跨chunk的内容缓冲区
                        in_reasoning = False  # 是否在标签内
                        
                        async for chunk in reasoner_stream:
                            if not chunk.choices:
                                continue
                            chunk_dict = chunk.model_dump()
                            delta = chunk_dict["choices"][0].get("delta", {})
                            if delta:
                                current_content = delta.get("content", "")
                                buffer += current_content  # 累积到缓冲区
                                
                                # 实时处理缓冲区内容
                                while True:
                                    reasoning_content = delta.get("reasoning_content", "")
                                    if reasoning_content:
                                        full_reasoning += reasoning_content
                                    else:
                                        reasoning_content = delta.get("reasoning", "")
                                        if reasoning_content:
                                            delta['reasoning_content'] = reasoning_content
                                            full_reasoning += reasoning_content
                                    if reasoning_content:
                                        yield f"data: {json.dumps(chunk_dict)}\n\n"
                                        break
                                    if not in_reasoning:
                                        # 寻找开放标签
                                        start_pos = buffer.find(open_tag)
                                        if start_pos != -1:
                                            # 开放标签前的内容（非思考内容）
                                            non_reasoning = buffer[:start_pos]
                                            buffer = buffer[start_pos+len(open_tag):]
                                            in_reasoning = True
                                        else:
                                            break  # 无开放标签，保留后续处理
                                    else:
                                        # 寻找闭合标签
                                        end_pos = buffer.find(close_tag)
                                        if end_pos != -1:
                                            # 提取思考内容并构造响应
                                            reasoning_part = buffer[:end_pos]
                                            chunk_dict["choices"][0]["delta"] = {
                                                "reasoning_content": reasoning_part,
                                                "content": ""  # 清除非思考内容
                                            }
                                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                                            full_reasoning += reasoning_part
                                            buffer = buffer[end_pos+len(close_tag):]
                                            in_reasoning = False
                                        else:
                                            # 发送未闭合的中间内容
                                            if buffer:
                                                chunk_dict["choices"][0]["delta"] = {
                                                    "reasoning_content": buffer,
                                                    "content": ""
                                                }
                                                yield f"data: {json.dumps(chunk_dict)}\n\n"
                                                full_reasoning += buffer
                                                buffer = ""
                                            break  # 等待更多内容
                    else:
                        # 流式调用推理模型
                        reasoner_stream = await reasoner_client.chat.completions.create(
                            model=settings['reasoner']['model'],
                            messages=msg,
                            stream=True,
                            stop=settings['reasoner']['stop_words'],
                            temperature=settings['reasoner']['temperature'],
                            **reasoner_extra
                        )
                        full_reasoning = ""
                        # 处理推理模型的流式响应
                        async for chunk in reasoner_stream:
                            if not chunk.choices:
                                continue

                            chunk_dict = chunk.model_dump()
                            delta = chunk_dict["choices"][0].get("delta", {})
                            if delta:
                                reasoning_content = delta.get("reasoning_content", "")
                                if reasoning_content:
                                    full_reasoning += reasoning_content
                                else:
                                    reasoning_content = delta.get("reasoning", "")
                                    if reasoning_content:
                                        delta['reasoning_content'] = reasoning_content
                                        full_reasoning += reasoning_content
                                # 移除content字段，确保yield的内容中不包含content
                                if 'content' in delta:
                                    del delta['content']
                            yield f"data: {json.dumps(chunk_dict)}\n\n"

                    # 在推理结束后添加完整推理内容到消息
                    content_append(request.messages, 'assistant', f"<think>\n{full_reasoning}\n</think>")  # 可参考的推理过程
                # 状态跟踪变量
                in_reasoning = False
                reasoning_buffer = []
                content_buffer = []
                if settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                    content_append(request.messages, 'user',  f"\n\n可参考的步骤：{user_prompt}\n\n")
                    drs_msg = get_drs_stage(DRS_STAGE)
                    if drs_msg:
                        content_append(request.messages, 'user',  f"\n\n{drs_msg}\n\n")
                msg = await images_add_in_messages(request.messages, images,settings)
                if tools:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=msg,  # 添加图片信息到消息
                        temperature=request.temperature,
                        tools=tools,
                        stream=True,
                        top_p=request.top_p or settings['top_p'],
                        extra_body = extra_params, # 其他参数
                        **extra
                    )
                else:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=msg,  # 添加图片信息到消息
                        temperature=request.temperature,
                        stream=True,
                        top_p=request.top_p or settings['top_p'],
                        extra_body = extra_params, # 其他参数
                        **extra
                    )
                tool_calls = []
                full_content = ""
                search_not_done = False
                search_task = ""
                async for chunk in response:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    if choice.delta.tool_calls:  # function_calling
                        for idx, tool_call in enumerate(choice.delta.tool_calls):
                            tool = choice.delta.tool_calls[idx]
                            if len(tool_calls) <= idx:
                                tool_calls.append(tool)
                                continue
                            if tool.function.arguments:
                                # function参数为流式响应，需要拼接
                                if tool_calls[idx].function.arguments:
                                    tool_calls[idx].function.arguments += tool.function.arguments
                                else:
                                    tool_calls[idx].function.arguments = tool.function.arguments
                    else:
                        # 创建原始chunk的拷贝
                        chunk_dict = chunk.model_dump()
                        delta = chunk_dict["choices"][0]["delta"]
                        
                        # 初始化必要字段
                        delta.setdefault("content", "")
                        delta.setdefault("reasoning_content", "")
                        
                        # 优先处理 reasoning_content
                        if delta["reasoning_content"]:
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                            continue
                        if delta.get("reasoning", ""):
                            delta["reasoning_content"] = delta["reasoning"]
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                            continue

                        # 处理内容
                        current_content = delta["content"]
                        buffer = current_content
                        
                        while buffer:
                            if not in_reasoning:
                                # 寻找开始标签
                                start_pos = buffer.find(open_tag)
                                if start_pos != -1:
                                    # 处理开始标签前的内容
                                    content_buffer.append(buffer[:start_pos])
                                    buffer = buffer[start_pos+len(open_tag):]
                                    in_reasoning = True
                                else:
                                    content_buffer.append(buffer)
                                    buffer = ""
                            else:
                                # 寻找结束标签
                                end_pos = buffer.find(close_tag)
                                if end_pos != -1:
                                    # 处理思考内容
                                    reasoning_buffer.append(buffer[:end_pos])
                                    buffer = buffer[end_pos+len(close_tag):]
                                    in_reasoning = False
                                else:
                                    reasoning_buffer.append(buffer)
                                    buffer = ""
                        
                        # 构造新的delta内容
                        new_content = "".join(content_buffer)
                        new_reasoning = "".join(reasoning_buffer)
                        
                        # 更新chunk内容
                        delta["content"] = new_content.strip("\x00")  # 保留未完成内容
                        delta["reasoning_content"] = new_reasoning.strip("\x00") or None
                        
                        # 重置缓冲区但保留未完成部分
                        if in_reasoning:
                            content_buffer = [new_content.split(open_tag)[-1]] 
                        else:
                            content_buffer = []
                        reasoning_buffer = []
                        
                        yield f"data: {json.dumps(chunk_dict)}\n\n"
                        full_content += delta.get("content", "")
                # 最终flush未完成内容
                if content_buffer or reasoning_buffer:
                    final_chunk = {
                        "choices": [{
                            "delta": {
                                "content": "".join(content_buffer),
                                "reasoning_content": "".join(reasoning_buffer)
                            }
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    full_content += final_chunk["choices"][0]["delta"].get("content", "")
                # 将响应添加到消息列表
                content_append(request.messages, 'assistant', full_content)
                # 工具和深度搜索
                if tool_calls:
                    print("tool_calls",tool_calls)
                    pass
                elif settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                    search_prompt = get_drs_stage_system_message(DRS_STAGE,user_prompt,full_content)
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                            "role": "system",
                            "content": source_prompt,
                            },
                            {
                            "role": "user",
                            "content": search_prompt,
                            }
                        ],
                        temperature=0.5,
                        extra_body = extra_params, # 其他参数
                    )
                    response_content = response.choices[0].message.content
                    # 用re 提取```json 包裹json字符串 ```
                    if "```json" in response_content:
                        try:
                            response_content = re.search(r'```json(.*?)```', response_content, re.DOTALL).group(1)
                        except:
                            # 用re 提取```json 之后的内容
                            response_content = re.search(r'```json(.*?)', response_content, re.DOTALL).group(1)
                    try:
                        response_content = json.loads(response_content)
                    except json.JSONDecodeError:
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n❌{await t("task_error")}</div>\n\n',
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                    if response_content["status"] == "done":
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n✅{await t("task_done")}</div>\n\n',
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                        search_not_done = False
                    elif response_content["status"] == "not_done":
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n❎{await t("task_not_done")}</div>\n\n',
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                        search_not_done = True
                        search_task = response_content["unfinished_task"]
                        task_prompt = f"请继续完成初始任务中未完成的任务：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n最后，请给出完整的初始任务的最终结果。"
                        request.messages.append(
                            {
                                "role": "assistant",
                                "content": full_content,
                            }
                        )
                        request.messages.append(
                            {
                                "role": "user",
                                "content": task_prompt,
                            }
                        )
                    elif response_content["status"] == "need_more_info":
                        DRS_STAGE = 2
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n❓{await t("task_need_more_info")}</div>\n\n'
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                        search_not_done = False
                    elif response_content["status"] == "need_work":
                        DRS_STAGE = 2
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n🔍{await t("enter_search_stage")}</div>\n\n'
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                        search_not_done = True
                        drs_msg = get_drs_stage(DRS_STAGE)
                        request.messages.append(
                            {
                                "role": "assistant",
                                "content": full_content,
                            }
                        )
                        request.messages.append(
                            {
                                "role": "user",
                                "content": drs_msg,
                            }
                        )
                    elif response_content["status"] == "need_more_work":
                        DRS_STAGE = 2
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n🔍{await t("need_more_work")}</div>\n\n'
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                        search_not_done = True
                        search_task = response_content["unfinished_task"]
                        task_prompt = f"请继续查询如下信息：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n"
                        request.messages.append(
                            {
                                "role": "assistant",
                                "content": full_content,
                            }
                        )
                        request.messages.append(
                            {
                                "role": "user",
                                "content": task_prompt,
                            }
                        )
                    elif response_content["status"] == "answer":
                        DRS_STAGE = 3
                        search_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n⭐{await t("enter_answer_stage")}</div>\n\n'
                                }
                            }]
                        }
                        yield f"data: {json.dumps(search_chunk)}\n\n"
                        search_not_done = True
                        drs_msg = get_drs_stage(DRS_STAGE)
                        request.messages.append(
                            {
                                "role": "assistant",
                                "content": full_content,
                            }
                        )
                        request.messages.append(
                            {
                                "role": "user",
                                "content": drs_msg,
                            }
                        )
                reasoner_messages = copy.deepcopy(request.messages)
                while tool_calls or search_not_done:
                    full_content = ""
                    if tool_calls:
                        response_content = tool_calls[0].function
                        print(response_content)
                        if response_content.name in  ["DDGsearch_async","searxng_async", "Bing_search_async", "Google_search_async", "Brave_search_async", "Exa_search_async", "Serper_search_async","bochaai_search_async","Tavily_search_async"]:
                            chunk_dict = {
                                "id": "agentParty",
                                "choices": [
                                    {
                                        "finish_reason": None,
                                        "index": 0,
                                        "delta": {
                                            "role":"assistant",
                                            "content": "",
                                            "tool_content": f'\n\n<div class="highlight-block">\n{await t("web_search")}</div>\n\n'
                                        }
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                        elif response_content.name in  ["jina_crawler_async","Crawl4Ai_search_async"]:
                            chunk_dict = {
                                "id": "agentParty",
                                "choices": [
                                    {
                                        "finish_reason": None,
                                        "index": 0,
                                        "delta": {
                                            "role":"assistant",
                                            "content": "",
                                            "tool_content": f'\n\n<div class="highlight-block">\n{await t("web_search_more")}</div>\n\n'
                                        }
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                        elif response_content.name in ["query_knowledge_base"]:
                            chunk_dict = {
                                "id": "agentParty",
                                "choices": [
                                    {
                                        "finish_reason": None,
                                        "index": 0,
                                        "delta": {
                                            "role":"assistant",
                                            "content": "",
                                            "tool_content": f'\n\n<div class="highlight-block">\n{await t("knowledge_base")}</div>\n\n'
                                        }
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                        else:
                            chunk_dict = {
                                "id": "agentParty",
                                "choices": [
                                    {
                                        "finish_reason": None,
                                        "index": 0,
                                        "delta": {
                                            "role":"assistant",
                                            "content": "",
                                            "tool_content": f'\n\n<div class="highlight-block">\n{await t("call")}{response_content.name}{await t("tool")}</div>\n\n'
                                        }
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                        modified_data = '[' + response_content.arguments.replace('}{', '},{') + ']'
                        # 使用json.loads来解析修改后的字符串为列表
                        data_list = json.loads(modified_data)
                        modified_tool = f"{await t("sendArg")}{data_list[0]}"
                        tool_call_chunk = {
                            "choices": [{
                                "delta": {
                                    "tool_content": f'\n\n<div class="highlight-block">\n{modified_tool}\n</div></div>\n\n',
                                }
                            }]
                        }
                        yield f"data: {json.dumps(tool_call_chunk)}\n\n"
                        if settings['tools']['asyncTools']['enabled']:
                            tool_id = uuid.uuid4()
                            async_tool_id = f"{response_content.name}_{tool_id}"
                            chunk_dict = {
                                "id": "agentParty",
                                "choices": [
                                    {
                                        "finish_reason": None,
                                        "index": 0,
                                        "delta": {
                                            "role":"assistant",
                                            "content": "",
                                            "async_tool_id": async_tool_id
                                        }
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                            # 启动异步任务并记录状态
                            asyncio.create_task(
                                execute_async_tool(
                                    async_tool_id,
                                    response_content.name,
                                    data_list[0],
                                    settings,
                                    user_prompt
                                )
                            )
                            
                            async with async_tools_lock:
                                async_tools[async_tool_id] = {
                                    "status": "pending",
                                    "result": None,
                                    "name":response_content.name,
                                    "parameters":data_list[0]
                                }
                            results = f"{response_content.name}工具已成功启动，获取结果需要花费很久的时间。请不要再次调用该工具，因为工具结果将生成后自动发送，再次调用也不能更快的获取到结果。请直接告诉用户，你会在获得结果后回答他的问题。"
                        else:
                            results = await dispatch_tool(response_content.name, data_list[0],settings)
                        if results is None:
                            chunk = {
                                "id": "extra_tools",
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "role":"assistant",
                                            "content": "",
                                            "tool_calls":modified_data,
                                        }
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                            break
                        if response_content.name in ["query_knowledge_base"] and type(results) == list:
                            if settings["KBSettings"]["is_rerank"]:
                                results = await rerank_knowledge_base(user_prompt,results)
                            results = json.dumps(results, ensure_ascii=False, indent=4)
                        request.messages.append(
                            {
                                "tool_calls": [
                                    {
                                        "id": tool_calls[0].id,
                                        "function": {
                                            "arguments": json.dumps(data_list[0]),
                                            "name": response_content.name,
                                        },
                                        "type": tool_calls[0].type,
                                    }
                                ],
                                "role": "assistant",
                                "content": str(response_content),
                            }
                        )
                        if (settings['webSearch']['when'] == 'after_thinking' or settings['webSearch']['when'] == 'both') and settings['tools']['asyncTools']['enabled'] is False:
                            content_append(request.messages, 'user',  f"\n对于联网搜索的结果，如果联网搜索的信息不足以回答问题时，你可以进一步使用联网搜索查询还未给出的必要信息。如果已经足够回答问题，请直接回答问题。")
                        if settings['tools']['asyncTools']['enabled']:
                            pass
                        else:
                            timestamp = time.time()
                            uid     = str(uuid.uuid4())
                            filename = f"{timestamp}_{uid}.txt"
                            file_path = os.path.join(TOOL_TEMP_DIR, filename)

                            # 工具名国际化
                            tool_name_text = f"{response_content.name}{await t('tool_result')}"
                            stream_tool_name_text = f"{response_content.name}{await t('stream_tool_result')}"
                            # ---------- 统一 SSE 封装 ----------
                            def make_sse(tool_html: str) -> str:
                                chunk = {
                                    "choices": [{
                                        "delta": {
                                            "tool_content": tool_html,
                                            "tool_link": f"{fastapi_base_url}tool_temp/{filename}",
                                        }
                                    }]
                                }
                                return f"data: {json.dumps(chunk)}\n\n"

                            # ---------- 分情况处理 ----------
                            if not isinstance(results, AsyncIterator):
                                # 老逻辑：一次性写完、一次性发
                                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                                    await f.write(results)
                                html = (
                                    '<div class="highlight-block">'
                                    f'<div style="margin-bottom: 10px;">{tool_name_text}</div>'
                                    f'<div>{results}</div>'
                                    '</div></div>'
                                )
                                yield make_sse(html)
                            else:  # AsyncIterator[str]
                                buffer = []
                                first = True
                                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                                    async for chunk in results:
                                        await f.write(chunk)
                                        await f.flush()
                                        buffer.append(chunk)
                                        if first:                       # 第一次：带头部
                                            html = (
                                                '<div class="highlight-block">'
                                                f'<div style="margin-bottom: 10px;">{stream_tool_name_text}</div>'
                                                f'<div>{chunk}'
                                            )
                                            first = False
                                        else:                           # 中间：只拼裸文本
                                            html = chunk

                                        yield make_sse(html)

                                    # 迭代结束：补尾部
                                    yield make_sse('</div></div></div>')
                                results = "".join(buffer)
                        request.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_calls[0].id,
                                "name": response_content.name,
                                "content": str("".join(results)),
                            }
                        )
                        reasoner_messages.append(
                            {
                                "role": "assistant",
                                "content": str(response_content),
                            }
                        )
                        reasoner_messages.append(
                            {
                                "role": "user",
                                "content": f"{response_content.name}工具结果："+str(results),
                            }
                        )
                    # 如果启用推理模型
                    if settings['reasoner']['enabled'] or enable_thinking:
                        if tools:
                            content_append(reasoner_messages, 'system',  f"可用工具：{json.dumps(tools)}")
                        for modelProvider in settings['modelProviders']: 
                            if modelProvider['id'] == settings['reasoner']['selectedProvider']:
                                vendor = modelProvider['vendor']
                                break
                        msg = await images_add_in_messages(reasoner_messages, images,settings)
                        if vendor == 'Ollama':
                            # 流式调用推理模型
                            reasoner_stream = await reasoner_client.chat.completions.create(
                                model=settings['reasoner']['model'],
                                messages=msg,
                                stream=True,
                                temperature=settings['reasoner']['temperature']
                            )
                            full_reasoning = ""
                            buffer = ""  # 跨chunk的内容缓冲区
                            in_reasoning = False  # 是否在标签内
                            
                            async for chunk in reasoner_stream:
                                if not chunk.choices:
                                    continue
                                chunk_dict = chunk.model_dump()
                                delta = chunk_dict["choices"][0].get("delta", {})
                                if delta:
                                    current_content = delta.get("content", "")
                                    buffer += current_content  # 累积到缓冲区
                                    
                                    # 实时处理缓冲区内容
                                    while True:
                                        reasoning_content = delta.get("reasoning_content", "")
                                        if reasoning_content:
                                            full_reasoning += reasoning_content
                                        else:
                                            reasoning_content = delta.get("reasoning", "")
                                            if reasoning_content:
                                                delta['reasoning_content'] = reasoning_content
                                                full_reasoning += reasoning_content
                                        if reasoning_content:
                                            yield f"data: {json.dumps(chunk_dict)}\n\n"
                                            break
                                        if not in_reasoning:
                                            # 寻找开放标签
                                            start_pos = buffer.find(open_tag)
                                            if start_pos != -1:
                                                # 开放标签前的内容（非思考内容）
                                                non_reasoning = buffer[:start_pos]
                                                buffer = buffer[start_pos+len(open_tag):]
                                                in_reasoning = True
                                            else:
                                                break  # 无开放标签，保留后续处理
                                        else:
                                            # 寻找闭合标签
                                            end_pos = buffer.find(close_tag)
                                            if end_pos != -1:
                                                # 提取思考内容并构造响应
                                                reasoning_part = buffer[:end_pos]
                                                chunk_dict["choices"][0]["delta"] = {
                                                    "reasoning_content": reasoning_part,
                                                    "content": ""  # 清除非思考内容
                                                }
                                                yield f"data: {json.dumps(chunk_dict)}\n\n"
                                                full_reasoning += reasoning_part
                                                buffer = buffer[end_pos+len(close_tag):]
                                                in_reasoning = False
                                            else:
                                                # 发送未闭合的中间内容
                                                if buffer:
                                                    chunk_dict["choices"][0]["delta"] = {
                                                        "reasoning_content": buffer,
                                                        "content": ""
                                                    }
                                                    yield f"data: {json.dumps(chunk_dict)}\n\n"
                                                    full_reasoning += buffer
                                                    buffer = ""
                                                break  # 等待更多内容
                        else:
                            # 流式调用推理模型
                            reasoner_stream = await reasoner_client.chat.completions.create(
                                model=settings['reasoner']['model'],
                                messages=msg,
                                stream=True,
                                stop=settings['reasoner']['stop_words'],
                                temperature=settings['reasoner']['temperature']
                            )
                            full_reasoning = ""
                            # 处理推理模型的流式响应
                            async for chunk in reasoner_stream:
                                if not chunk.choices:
                                    continue

                                chunk_dict = chunk.model_dump()
                                delta = chunk_dict["choices"][0].get("delta", {})
                                if delta:
                                    reasoning_content = delta.get("reasoning_content", "")
                                    if reasoning_content:
                                        full_reasoning += reasoning_content
                                    else:
                                        reasoning_content = delta.get("reasoning", "")
                                        if reasoning_content:
                                            delta['reasoning_content'] = reasoning_content
                                            full_reasoning += reasoning_content
                                    # 移除content字段，确保yield的内容中不包含content
                                    if 'content' in delta:
                                        del delta['content']
                                yield f"data: {json.dumps(chunk_dict)}\n\n"

                        # 在推理结束后添加完整推理内容到消息
                        content_append(request.messages, 'assistant', f"<think>\n{full_reasoning}\n</think>") # 可参考的推理过程
                    msg = await images_add_in_messages(request.messages, images,settings)
                    if tools:
                        response = await client.chat.completions.create(
                            model=model,
                            messages=msg,  # 添加图片信息到消息
                            temperature=request.temperature,
                            tools=tools,
                            stream=True,
                            top_p=request.top_p or settings['top_p'],
                            extra_body = extra_params, # 其他参数
                            **extra
                        )
                    else:
                        response = await client.chat.completions.create(
                            model=model,
                            messages=msg,  # 添加图片信息到消息
                            temperature=request.temperature,
                            stream=True,
                            top_p=request.top_p or settings['top_p'],
                            extra_body = extra_params, # 其他参数
                            **extra
                        )
                    tool_calls = []
                    async for chunk in response:
                        if not chunk.choices:
                            continue
                        if chunk.choices:
                            choice = chunk.choices[0]
                            if choice.delta.tool_calls:  # function_calling
                                for idx, tool_call in enumerate(choice.delta.tool_calls):
                                    tool = choice.delta.tool_calls[idx]
                                    if len(tool_calls) <= idx:
                                        tool_calls.append(tool)
                                        continue
                                    if tool.function.arguments:
                                        # function参数为流式响应，需要拼接
                                        if tool_calls[idx].function.arguments:
                                            tool_calls[idx].function.arguments += tool.function.arguments
                                        else:
                                            tool_calls[idx].function.arguments = tool.function.arguments
                            else:
                                # 创建原始chunk的拷贝
                                chunk_dict = chunk.model_dump()
                                delta = chunk_dict["choices"][0]["delta"]
                                
                                # 初始化必要字段
                                delta.setdefault("content", "")
                                delta.setdefault("reasoning_content", "")

                                # 优先处理 reasoning_content
                                if delta["reasoning_content"]:
                                    yield f"data: {json.dumps(chunk_dict)}\n\n"
                                    continue
                                if delta.get("reasoning", ""):
                                    delta["reasoning_content"] = delta["reasoning"]
                                    yield f"data: {json.dumps(chunk_dict)}\n\n"
                                    continue
                                # 处理内容
                                current_content = delta["content"]
                                buffer = current_content
                                
                                while buffer:
                                    if not in_reasoning:
                                        # 寻找开始标签
                                        start_pos = buffer.find(open_tag)
                                        if start_pos != -1:
                                            # 处理开始标签前的内容
                                            content_buffer.append(buffer[:start_pos])
                                            buffer = buffer[start_pos+len(open_tag):]
                                            in_reasoning = True
                                        else:
                                            content_buffer.append(buffer)
                                            buffer = ""
                                    else:
                                        # 寻找结束标签
                                        end_pos = buffer.find(close_tag)
                                        if end_pos != -1:
                                            # 处理思考内容
                                            reasoning_buffer.append(buffer[:end_pos])
                                            buffer = buffer[end_pos+len(close_tag):]
                                            in_reasoning = False
                                        else:
                                            reasoning_buffer.append(buffer)
                                            buffer = ""
                                
                                # 构造新的delta内容
                                new_content = "".join(content_buffer)
                                new_reasoning = "".join(reasoning_buffer)
                                
                                # 更新chunk内容
                                delta["content"] = new_content.strip("\x00")  # 保留未完成内容
                                delta["reasoning_content"] = new_reasoning.strip("\x00") or None
                                
                                # 重置缓冲区但保留未完成部分
                                if in_reasoning:
                                    content_buffer = [new_content.split(open_tag)[-1]] 
                                else:
                                    content_buffer = []
                                reasoning_buffer = []
                                
                                yield f"data: {json.dumps(chunk_dict)}\n\n"
                                full_content += delta.get("content", "")
                    # 最终flush未完成内容
                    if content_buffer or reasoning_buffer:
                        final_chunk = {
                            "choices": [{
                                "delta": {
                                    "content": "".join(content_buffer),
                                    "reasoning_content": "".join(reasoning_buffer)
                                }
                            }]
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        full_content += final_chunk["choices"][0]["delta"].get("content", "")
                    # 将响应添加到消息列表
                    content_append(request.messages, 'assistant', full_content)
                    # 工具和深度搜索
                    if tool_calls:
                        pass
                    elif settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                        search_prompt = get_drs_stage_system_message(DRS_STAGE,user_prompt,full_content)
                        response = await client.chat.completions.create(
                            model=model,
                            messages=[                        
                                {
                                "role": "system",
                                "content": source_prompt,
                                },
                                {
                                "role": "user",
                                "content": search_prompt,
                                }
                            ],
                            temperature=0.5,
                            extra_body = extra_params, # 其他参数
                        )
                        response_content = response.choices[0].message.content
                        # 用re 提取```json 包裹json字符串 ```
                        if "```json" in response_content:
                            try:
                                response_content = re.search(r'```json(.*?)```', response_content, re.DOTALL).group(1)
                            except:
                                # 用re 提取```json 之后的内容
                                response_content = re.search(r'```json(.*?)', response_content, re.DOTALL).group(1)
                        try:
                            response_content = json.loads(response_content)
                        except json.JSONDecodeError:
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n❌{await t("task_error")}</div>\n\n',
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                        if response_content["status"] == "done":
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n✅{await t("task_done")}</div>\n\n',
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                            search_not_done = False
                        elif response_content["status"] == "not_done":
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n❎{await t("task_not_done")}</div>\n\n',
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                            search_not_done = True
                            search_task = response_content["unfinished_task"]
                            task_prompt = f"请继续完成初始任务中未完成的任务：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n最后，请给出完整的初始任务的最终结果。"
                            request.messages.append(
                                {
                                    "role": "assistant",
                                    "content": full_content,
                                }
                            )
                            request.messages.append(
                                {
                                    "role": "user",
                                    "content": task_prompt,
                                }
                            )
                        elif response_content["status"] == "need_more_info":
                            DRS_STAGE = 2
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n❓{await t("task_need_more_info")}</div>\n\n'
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                            search_not_done = False
                        elif response_content["status"] == "need_work":
                            DRS_STAGE = 2
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n🔍{await t("enter_search_stage")}</div>\n\n'
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                            search_not_done = True
                            drs_msg = get_drs_stage(DRS_STAGE)
                            request.messages.append(
                                {
                                    "role": "assistant",
                                    "content": full_content,
                                }
                            )
                            request.messages.append(
                                {
                                    "role": "user",
                                    "content": drs_msg,
                                }
                            )
                        elif response_content["status"] == "need_more_work":
                            DRS_STAGE = 2
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n🔍{await t("need_more_work")}</div>\n\n'
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                            search_not_done = True
                            search_task = response_content["unfinished_task"]
                            task_prompt = f"请继续查询如下信息：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n"
                            request.messages.append(
                                {
                                    "role": "assistant",
                                    "content": full_content,
                                }
                            )
                            request.messages.append(
                                {
                                    "role": "user",
                                    "content": task_prompt,
                                }
                            )
                        elif response_content["status"] == "answer":
                            DRS_STAGE = 3
                            search_chunk = {
                                "choices": [{
                                    "delta": {
                                        "tool_content": f'\n\n<div class="highlight-block">\n⭐{await t("enter_answer_stage")}</div>\n\n'
                                    }
                                }]
                            }
                            yield f"data: {json.dumps(search_chunk)}\n\n"
                            search_not_done = True
                            drs_msg = get_drs_stage(DRS_STAGE)
                            request.messages.append(
                                {
                                    "role": "assistant",
                                    "content": full_content,
                                }
                            )
                            request.messages.append(
                                {
                                    "role": "user",
                                    "content": drs_msg,
                                }
                            )
                yield "data: [DONE]\n\n"
                if m0:
                    messages=f"用户说：{user_prompt}\n\n---\n\n你说：{full_content}"
                    executor = ThreadPoolExecutor()
                    async def add_async():
                        loop = asyncio.get_event_loop()
                        # 绑定 user_id 关键字参数
                        metadata = {
                            "timetamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        func = partial(m0.add, user_id=memoryId,metadata=metadata,infer=False)
                        # 传递 messages 作为位置参数
                        await loop.run_in_executor(executor, func, messages)
                        print("知识库更新完成")

                    asyncio.create_task(add_async())
                    print("知识库更新任务已提交")
                return
            except Exception as e:
                logger.error(f"Error occurred: {e}")
                traceback.print_exc()
                # 捕获异常并返回错误信息
                error_chunk = {
                    "choices": [{
                        "delta": {
                            "tool_content": f'\n\n<div class="highlight-block-error">\n❎ {str(e)}</div>\n\n',
                        }
                    }]
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"  # 确保最终结束
                return
        
        return StreamingResponse(
            stream_generator(user_prompt, DRS_STAGE),
            media_type="text/event-stream",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        # 如果e.status_code存在，则使用它作为HTTP状态码，否则使用500
        return JSONResponse(
            status_code=getattr(e, "status_code", 500),
            content={"error": str(e)},
        )

async def generate_complete_response(client,reasoner_client, request: ChatRequest, settings: dict,fastapi_base_url,enable_thinking,enable_deep_research,enable_web_search):
    from mem0 import Memory
    global mcp_client_list,HA_client,ChromeMCP_client,sql_client
    DRS_STAGE = 1 # 1: 明确用户需求阶段 2: 工具调用阶段 3: 生成结果阶段
    if len(request.messages) > 2:
        DRS_STAGE = 2
    from py.load_files import get_files_content,file_tool,image_tool
    from py.web_search import (
        DDGsearch_async, 
        searxng_async, 
        Tavily_search_async,
        Bing_search_async,
        Google_search_async,
        Brave_search_async,
        Exa_search_async,
        Serper_search_async,
        bochaai_search_async,
        duckduckgo_tool, 
        searxng_tool, 
        tavily_tool, 
        bing_tool,
        google_tool,
        brave_tool,
        exa_tool,
        serper_tool,
        bochaai_tool,
        jina_crawler_tool, 
        Crawl4Ai_tool
    )
    from py.know_base import kb_tool,query_knowledge_base,rerank_knowledge_base
    from py.agent_tool import get_agent_tool
    from py.a2a_tool import get_a2a_tool
    from py.llm_tool import get_llm_tool
    from py.pollinations import pollinations_image_tool,openai_image_tool,openai_chat_image_tool
    from py.code_interpreter import e2b_code_tool,local_run_code_tool
    from py.utility_tools import time_tool
    from py.utility_tools import (
        time_tool, 
        weather_tool,
        location_tool,
        timer_weather_tool,
        wikipedia_summary_tool,
        wikipedia_section_tool,
        arxiv_tool
    ) 
    from py.autoBehavior import auto_behavior_tool
    from py.cli_tool import claude_code_tool,qwen_code_tool
    m0 = None
    if settings["memorySettings"]["is_memory"] and settings["memorySettings"]["selectedMemory"] and settings["memorySettings"]["selectedMemory"] != "":
        memoryId = settings["memorySettings"]["selectedMemory"]
        cur_memory = None
        for memory in settings["memories"]:
            if memory["id"] == memoryId:
                cur_memory = memory
                break
        if cur_memory and cur_memory["providerId"]:
            print("长期记忆启用")
            config={
                "embedder": {
                    "provider": 'openai',
                    "config": {
                        "model": cur_memory['model'],
                        "api_key": cur_memory['api_key'],
                        "openai_base_url":cur_memory["base_url"],
                        "embedding_dims":cur_memory.get("embedding_dims", 1024)
                    },
                },
                "llm": {
                    "provider": 'openai',
                    "config": {
                        "model": settings['model'],
                        "api_key": settings['api_key'],
                        "openai_base_url":settings["base_url"]
                    }
                },
                "vector_store": {
                    "provider": "faiss",
                    "config": {
                        "collection_name": "agent-party",
                        "path": os.path.join(MEMORY_CACHE_DIR,memoryId),
                        "distance_strategy": "euclidean",
                        "embedding_model_dims": cur_memory.get("embedding_dims", 1024)
                    }
                }
            }
            m0 = Memory.from_config(config)
    images = await images_in_messages(request.messages,fastapi_base_url)
    request.messages = await message_without_images(request.messages)
    open_tag = "<think>"
    close_tag = "</think>"
    tools = request.tools or []
    tools = request.tools or []
    extra = {}
    reasoner_extra = {}
    if mcp_client_list:
        for server_name, mcp_client in mcp_client_list.items():
            if server_name in settings['mcpServers']:
                if 'disabled' not in settings['mcpServers'][server_name]:
                    settings['mcpServers'][server_name]['disabled'] = False
                if settings['mcpServers'][server_name]['disabled'] == False and settings['mcpServers'][server_name]['processingStatus'] == 'ready':
                    disable_tools = []
                    for tool in settings['mcpServers'][server_name]["tools"]: 
                        if tool.get("enabled", True) == False:
                            disable_tools.append(tool["name"])
                    function = await mcp_client.get_openai_functions(disable_tools=disable_tools)
                    if function:
                        tools.extend(function)
    get_llm_tool_fuction = await get_llm_tool(settings)
    if get_llm_tool_fuction:
        tools.append(get_llm_tool_fuction)
    get_agent_tool_fuction = await get_agent_tool(settings)
    if get_agent_tool_fuction:
        tools.append(get_agent_tool_fuction)
    get_a2a_tool_fuction = await get_a2a_tool(settings)
    if get_a2a_tool_fuction:
        tools.append(get_a2a_tool_fuction)
    if settings["HASettings"]["enabled"]:
        ha_tool = await HA_client.get_openai_functions(disable_tools=[])
        if ha_tool:
            tools.extend(ha_tool)
    if settings['chromeMCPSettings']['enabled']:
        chromeMCP_tool = await ChromeMCP_client.get_openai_functions(disable_tools=[])
        if chromeMCP_tool:
            tools.extend(chromeMCP_tool)
    if settings['sqlSettings']['enabled']:
        sql_tool = await sql_client.get_openai_functions(disable_tools=[])
        if sql_tool:
            tools.extend(sql_tool)
    if settings['CLISettings']['enabled']:
        if settings['CLISettings']['engine'] == 'cc':
            tools.append(claude_code_tool)
        elif settings['CLISettings']['engine'] == 'qc':
            tools.append(qwen_code_tool)
    if settings['tools']['time']['enabled'] and settings['tools']['time']['triggerMode'] == 'afterThinking':
        tools.append(time_tool)
    if settings["tools"]["weather"]['enabled']:
        tools.append(weather_tool)
        tools.append(location_tool)
        tools.append(timer_weather_tool)
    if settings["tools"]["wikipedia"]['enabled']:
        tools.append(wikipedia_summary_tool)
        tools.append(wikipedia_section_tool)
    if settings["tools"]["arxiv"]['enabled']:
        tools.append(arxiv_tool)
    if settings['text2imgSettings']['enabled']:
        if settings['text2imgSettings']['engine'] == 'pollinations':
            tools.append(pollinations_image_tool)
        elif settings['text2imgSettings']['engine'] == 'openai':
            tools.append(openai_image_tool)
        elif settings['text2imgSettings']['engine'] == 'openaiChat':
            tools.append(openai_chat_image_tool)
    if settings['tools']['getFile']['enabled']:
        tools.append(file_tool)
        tools.append(image_tool)
    if settings['tools']['autoBehavior']['enabled'] and request.messages[-1]['role'] == 'user':
        tools.append(auto_behavior_tool)
    if settings["codeSettings"]['enabled']:
        if settings["codeSettings"]["engine"] == "e2b":
            tools.append(e2b_code_tool)
        elif settings["codeSettings"]["engine"] == "sandbox":
            tools.append(local_run_code_tool)
    if settings["custom_http"]:
        for custom_http in settings["custom_http"]:
            if custom_http["enabled"]:
                if custom_http['body'] == "":
                    custom_http['body'] = "{}"
                custom_http_tool = {
                    "type": "function",
                    "function": {
                        "name": f"custom_http_{custom_http['name']}",
                        "description": f"{custom_http['description']}",
                        "parameters": json.loads(custom_http['body']),
                    },
                }
                tools.append(custom_http_tool)
    if settings["workflows"]:
        for workflow in settings["workflows"]:
            if workflow["enabled"]:
                comfyui_properties = {}
                comfyui_required = []
                if workflow["text_input"] is not None:
                    comfyui_properties["text_input"] = {
                        "description": "第一个文字输入，需要输入的提示词，用于生成图片或者视频，如果无特别提示，默认为英文",
                        "type": "string"
                    }
                    comfyui_required.append("text_input")
                if workflow["text_input_2"] is not None:
                    comfyui_properties["text_input_2"] = {
                        "description": "第二个文字输入，需要输入的提示词，用于生成图片或者视频，如果无特别提示，默认为英文",
                        "type": "string"
                    }
                    comfyui_required.append("text_input_2")
                if workflow["image_input"] is not None:
                    comfyui_properties["image_input"] = {
                        "description": "第一个图片输入，需要输入的图片，必须是图片URL，可以是外部链接，也可以是服务器内部的URL，例如：https://www.example.com/xxx.png  或者  http://127.0.0.1:3456/xxx.jpg",
                        "type": "string"
                    }
                    comfyui_required.append("image_input")
                if workflow["image_input_2"] is not None:
                    comfyui_properties["image_input_2"] = {
                        "description": "第二个图片输入，需要输入的图片，必须是图片URL，可以是外部链接，也可以是服务器内部的URL，例如：https://www.example.com/xxx.png  或者  http://127.0.0.1:3456/xxx.jpg",
                        "type": "string"
                    }
                    comfyui_required.append("image_input_2")
                comfyui_parameters = {
                    "type": "object",
                    "properties": comfyui_properties,
                    "required": comfyui_required
                }
                comfyui_tool = {
                    "type": "function",
                    "function": {
                        "name": f"comfyui_{workflow['unique_filename']}",
                        "description": f"{workflow['description']}+\n如果要输入图片提示词或者修改提示词，尽可能使用英语。\n返回的图片结果，请将图片的URL放入![image]()这样的markdown语法中，用户才能看到图片。如果是视频，请将视频的URL放入<video controls> <source src=''></video>的中src中，用户才能看到视频。如果有多个结果，则请用换行符分隔开这几个图片或者视频，用户才能看到多个结果。",
                        "parameters": comfyui_parameters,
                    },
                }
                tools.append(comfyui_tool)
    search_not_done = False
    search_task = ""
    try:
        model = settings['model']
        extra_params = settings['extra_params']
        # 移除extra_params这个list中"name"不包含非空白符的键值对
        if extra_params:
            for extra_param in extra_params:
                if not extra_param['name'].strip():
                    extra_params.remove(extra_param)
            # 列表转换为字典
            extra_params = {item['name']: item['value'] for item in extra_params}
        else:
            extra_params = {}
        if request.fileLinks:
            # 异步获取文件内容
            files_content = await get_files_content(request.fileLinks)
            system_message = f"\n\n相关文件内容：{files_content}"
            
            # 修复字符串拼接错误
            content_append(request.messages, 'system', system_message)
        kb_list = []
        user_prompt = request.messages[-1]['content']
        if settings["memorySettings"]["is_memory"] and settings["memorySettings"]["selectedMemory"] and settings["memorySettings"]["selectedMemory"] != "":
            if settings["memorySettings"]["userName"] and settings["memorySettings"]["userName"] != "user":
                print("添加用户名：\n\n" + settings["memorySettings"]["userName"] + "\n\n用户名结束\n\n")
                content_append(request.messages, 'system', "当前与你交流的人的名字为：\n\n" + settings["memorySettings"]["userName"] + "\n\n")
            lore_content = ""
            assistant_reply = ""
            # 找出request.messages中上次的assistant回复
            for i in range(len(request.messages)-1, -1, -1):
                if request.messages[i]['role'] == 'assistant':
                    assistant_reply = request.messages[i]['content']
                    break
            if cur_memory["characterBook"]:
                for lore in cur_memory["characterBook"]:
                    # lore['keysRaw'] 按照换行符分割，并去除空字符串
                    lore_keys = lore["keysRaw"].split("\n")
                    lore_keys = [key for key in lore_keys if key != ""]
                    print(lore_keys)
                    # 如果lore_keys不为空，并且lore_keys的任意一个元素在user_prompt或者assistant_reply中，则添加lore['content']到lore_content中
                    if lore_keys != [] and any(key in user_prompt or key in assistant_reply for key in lore_keys):
                        lore_content += lore['content'] + "\n\n"
            if lore_content:
                if settings["memorySettings"]["userName"]:
                    # 替换lore_content中的{{user}}为settings["memorySettings"]["userName"]
                    lore_content = lore_content.replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换lore_content中的{{char}}为cur_memory["name"]
                lore_content = lore_content.replace("{{char}}", cur_memory["name"])
                print("添加世界观设定：\n\n" + lore_content + "\n\n世界观设定结束\n\n")
                content_append(request.messages, 'system', "世界观设定：\n\n" + lore_content + "\n\n世界观设定结束\n\n")
            if cur_memory["description"]:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["description"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["description"] = cur_memory["description"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["description"]中的{{char}}为cur_memory["name"]
                cur_memory["description"] = cur_memory["description"].replace("{{char}}", cur_memory["name"])
                print("添加角色设定：\n\n" + cur_memory["description"] + "\n\n角色设定结束\n\n")
                content_append(request.messages, 'system', "角色设定：\n\n" + cur_memory["description"] + "\n\n角色设定结束\n\n")
            if cur_memory["personality"]:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["personality"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["personality"] = cur_memory["personality"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["personality"]中的{{char}}为cur_memory["name"]
                cur_memory["personality"] = cur_memory["personality"].replace("{{char}}", cur_memory["name"])
                print("添加性格设定：\n\n" + cur_memory["personality"] + "\n\n性格设定结束\n\n")
                content_append(request.messages, 'system', "性格设定：\n\n" + cur_memory["personality"] + "\n\n性格设定结束\n\n") 
            if cur_memory['mesExample']:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["mesExample"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["mesExample"] = cur_memory["mesExample"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["mesExample"]中的{{char}}为cur_memory["name"]
                cur_memory["mesExample"] = cur_memory["mesExample"].replace("{{char}}", cur_memory["name"])
                print("添加对话示例：\n\n" + cur_memory['mesExample'] + "\n\n对话示例结束\n\n")
                content_append(request.messages, 'system', "对话示例：\n\n" + cur_memory['mesExample'] + "\n\n对话示例结束\n\n")
            if cur_memory["systemPrompt"]:
                if settings["memorySettings"]["userName"]:
                    # 替换cur_memory["systemPrompt"]中的{{user}}为settings["memorySettings"]["userName"]
                    cur_memory["systemPrompt"] = cur_memory["systemPrompt"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["systemPrompt"]中的{{char}}为cur_memory["name"]
                cur_memory["systemPrompt"] = cur_memory["systemPrompt"].replace("{{char}}", cur_memory["name"])
                print("添加系统提示：\n\n" + cur_memory["systemPrompt"] + "\n\n系统提示结束\n\n")
                content_append(request.messages, 'system', "系统提示：\n\n" + cur_memory["systemPrompt"] + "\n\n系统提示结束\n\n")
            if settings["memorySettings"]["genericSystemPrompt"]:
                if settings["memorySettings"]["userName"]:
                    # 替换settings["memorySettings"]["genericSystemPrompt"]中的{{user}}为settings["memorySettings"]["userName"]
                    settings["memorySettings"]["genericSystemPrompt"] = settings["memorySettings"]["genericSystemPrompt"].replace("{{user}}", settings["memorySettings"]["userName"])
                # 替换cur_memory["systemPrompt"]中的{{char}}为cur_memory["name"]
                settings["memorySettings"]["genericSystemPrompt"] = settings["memorySettings"]["genericSystemPrompt"].replace("{{char}}", cur_memory["name"])
                print("添加系统提示：\n\n" + settings["memorySettings"]["genericSystemPrompt"] + "\n\n系统提示结束\n\n")
                content_append(request.messages, 'system', "系统提示：\n\n" + settings["memorySettings"]["genericSystemPrompt"] + "\n\n系统提示结束\n\n")
                    
            if m0:
                memoryLimit = settings["memorySettings"]["memoryLimit"]
                try:
                    # 【核心修改】：使用 asyncio.to_thread 将同步的 search 方法放入线程池运行
                    # 这样主线程（Event Loop）会被释放，可以去处理 /minilm/embeddings 请求，从而避免死锁
                    relevant_memories = await asyncio.to_thread(
                        m0.search, 
                        query=user_prompt, 
                        user_id=memoryId, 
                        limit=memoryLimit
                    )
                    relevant_memories = json.dumps(relevant_memories, ensure_ascii=False)
                except Exception as e:
                    print("m0.search error:",e)
                    relevant_memories = ""
                print("添加相关记忆：\n\n" + relevant_memories + "\n\n相关结束\n\n")
                content_append(request.messages, 'system', "之前的相关记忆：\n\n" + relevant_memories + "\n\n相关结束\n\n") 
        if settings["knowledgeBases"]:
            for kb in settings["knowledgeBases"]:
                if kb["enabled"] and kb["processingStatus"] == "completed":
                    kb_list.append({"kb_id":kb["id"],"name": kb["name"],"introduction":kb["introduction"]})
        if settings["KBSettings"]["when"] == "before_thinking" or settings["KBSettings"]["when"] == "both":
            if kb_list:
                all_kb_content = []
                # 用query_knowledge_base函数查询kb_list中所有的知识库
                for kb in kb_list:
                    kb_content = await query_knowledge_base(kb["kb_id"],user_prompt)
                    all_kb_content.extend(kb_content)
                    if settings["KBSettings"]["is_rerank"]:
                        all_kb_content = await rerank_knowledge_base(user_prompt,all_kb_content)
                if all_kb_content:
                    kb_message = f"\n\n可参考的知识库内容：{all_kb_content}"
                    content_append(request.messages, 'user',  f"{kb_message}\n\n用户：{user_prompt}")
        if settings["KBSettings"]["when"] == "after_thinking" or settings["KBSettings"]["when"] == "both":
            if kb_list:
                kb_list_message = f"\n\n可调用的知识库列表：{json.dumps(kb_list, ensure_ascii=False)}"
                content_append(request.messages, 'system', kb_list_message)
        else:
            kb_list = []
        request = await tools_change_messages(request, settings)
        chat_vendor = 'OpenAI'
        reasoner_vendor = 'OpenAI'
        for modelProvider in settings['modelProviders']: 
            if modelProvider['id'] == settings['selectedProvider']:
                chat_vendor = modelProvider['vendor']
                break
        for modelProvider in settings['modelProviders']: 
            if modelProvider['id'] == settings['reasoner']['selectedProvider']:
                reasoner_vendor = modelProvider['vendor']
                break
        if chat_vendor == 'Dify':
            try:
                if len(request.messages) >= 3:
                    if request.messages[2]['role'] == 'user':
                        if request.messages[1]['role'] == 'assistant':
                            request.messages[2]['content'] = "你上一次的发言：\n" +request.messages[0]['content'] + "\n你上一次的发言结束\n\n用户：" + request.messages[2]['content']
                        if request.messages[0]['role'] == 'system':
                            request.messages[2]['content'] = "系统提示：\n" +request.messages[0]['content'] + "\n系统提示结束\n\n" + request.messages[2]['content']
                elif len(request.messages) >= 2:
                    if request.messages[1]['role'] == 'user':
                        if request.messages[0]['role'] == 'system':
                            request.messages[1]['content'] = "系统提示：\n" +request.messages[0]['content'] + "\n系统提示结束\n\n用户：" + request.messages[1]['content']
            except Exception as e:
                print("Dify error:",e)
        if settings['webSearch']['enabled'] or enable_web_search:
            if settings['webSearch']['when'] == 'before_thinking' or settings['webSearch']['when'] == 'both':
                if settings['webSearch']['engine'] == 'duckduckgo':
                    results = await DDGsearch_async(user_prompt)
                elif settings['webSearch']['engine'] == 'searxng':
                    results = await searxng_async(user_prompt)
                elif settings['webSearch']['engine'] == 'tavily':
                    results = await Tavily_search_async(user_prompt)
                elif settings['webSearch']['engine'] == 'bing':
                    results = await Bing_search_async(user_prompt)
                elif settings['webSearch']['engine'] == 'google':
                    results = await Google_search_async(user_prompt)
                elif settings['webSearch']['engine'] == 'brave':
                    results = await Brave_search_async(user_prompt)
                elif settings['webSearch']['engine'] == 'exa':
                    results = await Exa_search_async(user_prompt)
                elif settings['webSearch']['engine'] == 'serper':
                    results = await Serper_search_async(user_prompt)
                elif settings['webSearch']['engine'] == 'bochaai':
                    results = await bochaai_search_async(user_prompt)
                if results:
                    content_append(request.messages, 'user',  f"\n\n联网搜索结果：{results}")
            if settings['webSearch']['when'] == 'after_thinking' or settings['webSearch']['when'] == 'both':
                if settings['webSearch']['engine'] == 'duckduckgo':
                    tools.append(duckduckgo_tool)
                elif settings['webSearch']['engine'] == 'searxng':
                    tools.append(searxng_tool)
                elif settings['webSearch']['engine'] == 'tavily':
                    tools.append(tavily_tool)
                elif settings['webSearch']['engine'] == 'bing':
                    tools.append(bing_tool)
                elif settings['webSearch']['engine'] == 'google':
                    tools.append(google_tool)
                elif settings['webSearch']['engine'] == 'brave':
                    tools.append(brave_tool)
                elif settings['webSearch']['engine'] == 'exa':
                    tools.append(exa_tool)
                elif settings['webSearch']['crawler'] == 'serper':
                    tools.append(serper_tool)
                elif settings['webSearch']['crawler'] == 'bochaai':
                    tools.append(bochaai_tool)

                if settings['webSearch']['crawler'] == 'jina':
                    tools.append(jina_crawler_tool)
                elif settings['webSearch']['crawler'] == 'crawl4ai':
                    tools.append(Crawl4Ai_tool)
        if kb_list:
            tools.append(kb_tool)
        if settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
            deepsearch_messages = copy.deepcopy(request.messages)
            content_append(deepsearch_messages, 'user',  "\n\n将用户提出的问题或给出的当前任务拆分成多个步骤，每一个步骤用一句简短的话概括即可，无需回答或执行这些内容，直接返回总结即可，但不能省略问题或任务的细节。如果用户输入的只是闲聊或者不包含任务和问题，直接把用户输入重复输出一遍即可。如果是非常简单的问题，也可以只给出一个步骤即可。一般情况下都是需要拆分成多个步骤的。")
            response = await client.chat.completions.create(
                model=model,
                messages=deepsearch_messages,
                temperature=0.5, 
                extra_body = extra_params, # 其他参数
            )
            user_prompt = response.choices[0].message.content
            content_append(request.messages, 'user',  f"\n\n如果用户没有提出问题或者任务，直接闲聊即可，如果用户提出了问题或者任务，任务描述不清晰或者你需要进一步了解用户的真实需求，你可以暂时不完成任务，而是分析需要让用户进一步明确哪些需求。")
        if settings['reasoner']['enabled'] or enable_thinking:
            reasoner_messages = copy.deepcopy(request.messages)
            if settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                drs_msg = get_drs_stage(DRS_STAGE)
                if drs_msg:
                    content_append(reasoner_messages, 'user',  f"\n\n{drs_msg}\n\n")
                content_append(reasoner_messages, 'user',  f"\n\n可参考的步骤：{user_prompt}\n\n")
            if tools:
                content_append(reasoner_messages, 'system',  f"可用工具：{json.dumps(tools)}")
            for modelProvider in settings['modelProviders']: 
                if modelProvider['id'] == settings['reasoner']['selectedProvider']:
                    vendor = modelProvider['vendor']
                    break
            msg = await images_add_in_messages(reasoner_messages, images,settings)   
            if chat_vendor == 'OpenAI':
                extra['max_completion_tokens'] = request.max_tokens or settings['max_tokens']
            else:
                extra['max_tokens'] = request.max_tokens or settings['max_tokens']
            if reasoner_vendor == 'OpenAI':
                reasoner_extra['max_completion_tokens'] = settings['reasoner']['max_tokens']
            else:
                reasoner_extra['max_tokens'] = settings['reasoner']['max_tokens']
            if request.reasoning_effort or settings['reasoning_effort']:
                extra['reasoning_effort'] = request.reasoning_effort or settings['reasoning_effort']
            if settings['reasoner']['reasoning_effort'] is not None:
                reasoner_extra['reasoning_effort'] = settings['reasoner']['reasoning_effort'] 
            if vendor == 'Ollama':
                reasoner_response = await reasoner_client.chat.completions.create(
                    model=settings['reasoner']['model'],
                    messages=msg,
                    stream=False,
                    temperature=settings['reasoner']['temperature'],
                    **reasoner_extra
                )
                reasoning_buffer = reasoner_response.model_dump()['choices'][0]['message']['reasoning_content']
                if reasoning_buffer:
                    content_prepend(request.messages, 'assistant', reasoning_buffer) # 可参考的推理过程
                else:
                    reasoning_buffer = reasoner_response.model_dump()['choices'][0]['message']['reasoning']
                    if reasoning_buffer:
                        content_prepend(request.messages, 'assistant', reasoning_buffer) # 可参考的推理过程
                    else:
                        # 将推理结果中的思考内容提取出来
                        reasoning_content = reasoner_response.model_dump()['choices'][0]['message']['content']
                        # open_tag和close_tag之间的内容
                        start_index = reasoning_content.find(open_tag) + len(open_tag)
                        end_index = reasoning_content.find(close_tag)
                        if start_index != -1 and end_index != -1:
                            reasoning_content = reasoning_content[start_index:end_index]
                        else:
                            reasoning_content = ""
                        content_prepend(request.messages, 'assistant', reasoning_content) # 可参考的推理过程
            else:
                reasoner_response = await reasoner_client.chat.completions.create(
                    model=settings['reasoner']['model'],
                    messages=msg,
                    stream=False,
                    stop=settings['reasoner']['stop_words'],
                    temperature=settings['reasoner']['temperature'],
                    **reasoner_extra
                )
                reasoning_buffer = reasoner_response.model_dump()['choices'][0]['message']['reasoning_content']
                if reasoning_buffer:
                    content_prepend(request.messages, 'assistant', reasoning_buffer) # 可参考的推理过程
                else:
                    reasoning_buffer = reasoner_response.model_dump()['choices'][0]['message']['reasoning']
                    if reasoning_buffer:
                        content_prepend(request.messages, 'assistant', reasoning_buffer) # 可参考的推理过程
                    else:
                        reasoning_buffer = ""
                        content_prepend(request.messages, 'assistant', reasoning_buffer) # 可参考的推理过程
        if settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
            content_append(request.messages, 'user',  f"\n\n可参考的步骤：{user_prompt}\n\n")
            drs_msg = get_drs_stage(DRS_STAGE)
            if drs_msg:
                content_append(request.messages, 'user',  f"\n\n{drs_msg}\n\n")
        msg = await images_add_in_messages(request.messages, images,settings)
        if tools:
            response = await client.chat.completions.create(
                model=model,
                messages=msg,  # 添加图片信息到消息
                temperature=request.temperature,
                tools=tools,
                stream=False,
                top_p=request.top_p or settings['top_p'],
                extra_body = extra_params, # 其他参数
                **extra
            )
        else:
            response = await client.chat.completions.create(
                model=model,
                messages=msg,  # 添加图片信息到消息
                temperature=request.temperature,
                stream=False,
                top_p=request.top_p or settings['top_p'],
                extra_body = extra_params, # 其他参数
                **extra
            )
        if response.choices[0].message.tool_calls:
            pass
        elif settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
            search_prompt = get_drs_stage_system_message(DRS_STAGE,user_prompt,response.choices[0].message.content)
            research_response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                    "role": "user",
                    "content": search_prompt,
                    }
                ],
                temperature=0.5,
                extra_body = extra_params, # 其他参数
            )
            response_content = research_response.choices[0].message.content
            # 用re 提取```json 包裹json字符串 ```
            if "```json" in response_content:
                try:
                    response_content = re.search(r'```json(.*?)```', response_content, re.DOTALL).group(1)
                except:
                    # 用re 提取```json 之后的内容
                    response_content = re.search(r'```json(.*?)', response_content, re.DOTALL).group(1)
            response_content = json.loads(response_content)
            if response_content["status"] == "done":
                search_not_done = False
            elif response_content["status"] == "not_done":
                search_not_done = True
                search_task = response_content["unfinished_task"]
                task_prompt = f"请继续完成初始任务中未完成的任务：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n最后，请给出完整的初始任务的最终结果。"
                request.messages.append(
                    {
                        "role": "assistant",
                        "content": research_response.choices[0].message.content,
                    }
                )
                request.messages.append(
                    {
                        "role": "user",
                        "content": task_prompt,
                    }
                )
            elif response_content["status"] == "need_more_info":
                DRS_STAGE = 2
                search_not_done = False
            elif response_content["status"] == "need_work":
                DRS_STAGE = 2
                search_not_done = True
                drs_msg = get_drs_stage(DRS_STAGE)
                request.messages.append(
                    {
                        "role": "assistant",
                        "content": research_response.choices[0].message.content,
                    }
                )
                request.messages.append(
                    {
                        "role": "user",
                        "content": drs_msg,
                    }
                )
            elif response_content["status"] == "need_more_work":
                DRS_STAGE = 2
                search_not_done = True
                search_task = response_content["unfinished_task"]
                task_prompt = f"请继续查询如下信息：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n"
                request.messages.append(
                    {
                        "role": "assistant",
                        "content": research_response.choices[0].message.content,
                    }
                )
                request.messages.append(
                    {
                        "role": "user",
                        "content": task_prompt,
                    }
                )
            elif response_content["status"] == "answer":
                DRS_STAGE = 3
                search_not_done = True
                drs_msg = get_drs_stage(DRS_STAGE)
                request.messages.append(
                    {
                        "role": "assistant",
                        "content": research_response.choices[0].message.content,
                    }
                )
                request.messages.append(
                    {
                        "role": "user",
                        "content": drs_msg,
                    }
                )
        reasoner_messages = copy.deepcopy(request.messages)
        while response.choices[0].message.tool_calls or search_not_done:
            if response.choices[0].message.tool_calls:
                assistant_message = response.choices[0].message
                response_content = assistant_message.tool_calls[0].function
                print(response_content.name)
                modified_data = '[' + response_content.arguments.replace('}{', '},{') + ']'
                # 使用json.loads来解析修改后的字符串为列表
                data_list = json.loads(modified_data)
                # 存储处理结果
                results = []
                for data in data_list:
                    result = await dispatch_tool(response_content.name, data,settings) # 将结果添加到results列表中
                    if isinstance(results, AsyncIterator):
                        buffer = []
                        async for chunk in results:
                            buffer.append(chunk)
                        results = "".join(buffer)
                    if result is not None:
                        # 将结果添加到results列表中
                        results.append(json.dumps(result))
                # 将所有结果拼接成一个连续的字符串
                combined_results = ''.join(results)
                if combined_results:
                    results = combined_results
                else:
                    results = None
                if results is None:
                    break
                if response_content.name in ["query_knowledge_base"]:
                    if settings["KBSettings"]["is_rerank"]:
                        results = await rerank_knowledge_base(user_prompt,results)
                    results = json.dumps(results, ensure_ascii=False, indent=4)
                request.messages.append(
                    {
                        "tool_calls": [
                            {
                                "id": assistant_message.tool_calls[0].id,
                                "function": {
                                    "arguments": response_content.arguments,
                                    "name": response_content.name,
                                },
                                "type": assistant_message.tool_calls[0].type,
                            }
                        ],
                        "role": "assistant",
                        "content": str(response_content),
                    }
                )
                request.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": assistant_message.tool_calls[0].id,
                        "name": response_content.name,
                        "content": str(results),
                    }
                )
            if settings['webSearch']['when'] == 'after_thinking' or settings['webSearch']['when'] == 'both':
                content_append(request.messages, 'user',  f"\n对于联网搜索的结果，如果联网搜索的信息不足以回答问题时，你可以进一步使用联网搜索查询还未给出的必要信息。如果已经足够回答问题，请直接回答问题。")
            reasoner_messages.append(
                {
                    "role": "assistant",
                    "content": str(response_content),
                }
            )
            reasoner_messages.append(
                {
                    "role": "user",
                    "content": f"{response_content.name}工具结果："+str(results),
                }
            )
            if settings['reasoner']['enabled'] or enable_thinking:
                if tools:
                    content_append(reasoner_messages, 'system',  f"可用工具：{json.dumps(tools)}")
                for modelProvider in settings['modelProviders']: 
                    if modelProvider['id'] == settings['reasoner']['selectedProvider']:
                        vendor = modelProvider['vendor']
                        break
                msg = await images_add_in_messages(reasoner_messages, images,settings)
                if vendor == 'Ollama':
                    reasoner_response = await reasoner_client.chat.completions.create(
                        model=settings['reasoner']['model'],
                        messages=msg,
                        stream=False,
                        temperature=settings['reasoner']['temperature'],
                        **reasoner_extra
                    )
                    # 将推理结果中的思考内容提取出来
                    reasoning_content = reasoner_response.model_dump()['choices'][0]['message']['content']
                    # open_tag和close_tag之间的内容
                    start_index = reasoning_content.find(open_tag) + len(open_tag)
                    end_index = reasoning_content.find(close_tag)
                    if start_index != -1 and end_index != -1:
                        reasoning_content = reasoning_content[start_index:end_index]
                    else:
                        reasoning_content = ""
                    content_prepend(request.messages, 'assistant', reasoning_content) # 可参考的推理过程
                else:
                    reasoner_response = await reasoner_client.chat.completions.create(
                        model=settings['reasoner']['model'],
                        messages=msg,
                        stream=False,
                        stop=settings['reasoner']['stop_words'],
                        temperature=settings['reasoner']['temperature'],
                        **reasoner_extra
                    )
                    content_prepend(request.messages, 'assistant', reasoner_response.model_dump()['choices'][0]['message']['reasoning_content']) # 可参考的推理过程
            msg = await images_add_in_messages(request.messages, images,settings)
            if tools:
                response = await client.chat.completions.create(
                    model=model,
                    messages=msg,  # 添加图片信息到消息
                    temperature=request.temperature,
                    tools=tools,
                    stream=False,
                    top_p=request.top_p or settings['top_p'],
                    extra_body = extra_params, # 其他参数
                    **extra
                )
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=msg,  # 添加图片信息到消息
                    temperature=request.temperature,
                    stream=False,
                    top_p=request.top_p or settings['top_p'],
                    extra_body = extra_params, # 其他参数
                    **extra
                )
            if response.choices[0].message.tool_calls:
                pass
            elif settings['tools']['deepsearch']['enabled'] or enable_deep_research: 
                search_prompt = get_drs_stage_system_message(DRS_STAGE,user_prompt,response.choices[0].message.content)
                research_response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                        "role": "user",
                        "content": search_prompt,
                        }
                    ],
                    temperature=0.5,
                    extra_body = extra_params, # 其他参数
                )
                response_content = research_response.choices[0].message.content
                # 用re 提取```json 包裹json字符串 ```
                if "```json" in response_content:
                    try:
                        response_content = re.search(r'```json(.*?)```', response_content, re.DOTALL).group(1)
                    except:
                        # 用re 提取```json 之后的内容
                        response_content = re.search(r'```json(.*?)', response_content, re.DOTALL).group(1)
                response_content = json.loads(response_content)
                if response_content["status"] == "done":
                    search_not_done = False
                elif response_content["status"] == "not_done":
                    search_not_done = True
                    search_task = response_content["unfinished_task"]
                    task_prompt = f"请继续完成初始任务中未完成的任务：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n最后，请给出完整的初始任务的最终结果。"
                    request.messages.append(
                        {
                            "role": "assistant",
                            "content": research_response.choices[0].message.content,
                        }
                    )
                    request.messages.append(
                        {
                            "role": "user",
                            "content": task_prompt,
                        }
                    )
                elif response_content["status"] == "need_more_info":
                    DRS_STAGE = 2
                    search_not_done = False
                elif response_content["status"] == "need_work":
                    DRS_STAGE = 2
                    search_not_done = True
                    drs_msg = get_drs_stage(DRS_STAGE)
                    request.messages.append(
                        {
                            "role": "assistant",
                            "content": research_response.choices[0].message.content,
                        }
                    )
                    request.messages.append(
                        {
                            "role": "user",
                            "content": drs_msg,
                        }
                    )
                elif response_content["status"] == "need_more_work":
                    DRS_STAGE = 2
                    search_not_done = True
                    search_task = response_content["unfinished_task"]
                    task_prompt = f"请继续查询如下信息：\n\n{search_task}\n\n初始任务：{user_prompt}\n\n"
                    request.messages.append(
                        {
                            "role": "assistant",
                            "content": research_response.choices[0].message.content,
                        }
                    )
                    request.messages.append(
                        {
                            "role": "user",
                            "content": task_prompt,
                        }
                    )
                elif response_content["status"] == "answer":
                    DRS_STAGE = 3
                    search_not_done = True
                    drs_msg = get_drs_stage(DRS_STAGE)
                    request.messages.append(
                        {
                            "role": "assistant",
                            "content": research_response.choices[0].message.content,
                        }
                    )
                    request.messages.append(
                        {
                            "role": "user",
                            "content": drs_msg,
                        }
                    )
       # 处理响应内容
        response_dict = response.model_dump()
        content = response_dict["choices"][0]['message']['content']
        if response_dict["choices"][0]['message'].get('reasoning_content',""):
            pass
        else:
            response_dict["choices"][0]['message']['reasoning_content'] = response_dict["choices"][0]['message'].get('reasoning',"")
        if open_tag in content and close_tag in content:
            reasoning_content = re.search(fr'{open_tag}(.*?)\{close_tag}', content, re.DOTALL)
            if reasoning_content:
                # 存储到 reasoning_content 字段
                response_dict["choices"][0]['message']['reasoning_content'] = reasoning_content.group(1).strip()
                # 移除原内容中的标签部分
                response_dict["choices"][0]['message']['content'] = re.sub(fr'{open_tag}(.*?)\{close_tag}', '', content, flags=re.DOTALL).strip()
        if m0:
            messages=f"用户说：{user_prompt}\n\n---\n\n你说：{response_dict["choices"][0]['message']['content']}"
            executor = ThreadPoolExecutor()
            async def add_async():
                loop = asyncio.get_event_loop()
                # 绑定 user_id 关键字参数
                metadata = {
                    "timetamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                func = partial(m0.add, user_id=memoryId,metadata=metadata,infer=False)
                # 传递 messages 作为位置参数
                await loop.run_in_executor(executor, func, messages)
                print("知识库更新完成")

            asyncio.create_task(add_async())
        return JSONResponse(content=response_dict)
    except Exception as e:
        return JSONResponse(
            content={"error": {"message": str(e), "type": "api_error"}}
        )

# 在现有路由后添加以下代码
@app.get("/v1/models")
async def get_models():
    """
    获取模型列表
    """
    from openai.types import Model
    from openai.pagination import SyncPage
    try:
        # 重新加载最新设置
        current_settings = await load_settings()
        agents = current_settings['agents']
        # 构造符合 OpenAI 格式的 Model 对象
        model_data = [
            Model(
                id=agent["name"],  
                created=0,  
                object="model",
                owned_by="super-agent-party"  # 非空字符串
            )
            for agent in agents.values()  
        ]
        # 添加默认的 'super-model'
        model_data.append(
            Model(
                id='super-model',
                created=0,
                object="model",
                owned_by="super-agent-party"  # 非空字符串
            )
        )

        # 构造完整 SyncPage 响应
        response = SyncPage[Model](
            object="list",
            data=model_data,
            has_more=False  # 添加分页标记
        )
        # 直接返回模型字典，由 FastAPI 自动序列化为 JSON
        return response.model_dump()  
        
    except Exception as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": {
                    "message": str(e),
                    "type": "api_error",
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": 500
                }
            }
        )

# 在现有路由后添加以下代码
@app.get("/v1/agents",operation_id="get_agents")
async def get_agents():
    """
    获取模型列表
    """
    from openai.types import Model
    from openai.pagination import SyncPage
    try:
        # 重新加载最新设置
        current_settings = await load_settings()
        agents = current_settings['agents']
        # 构造符合 OpenAI 格式的 Model 对象
        model_data = [
            {
                "name": agent["name"],
                "description": agent["system_prompt"],
            }
            for agent in agents.values()  
        ]
        # 添加默认的 'super-model'
        model_data.append(
            {
                "name": 'super-model',
                "description": "Super-Agent-Party default agent",
            }
        )
        return model_data
        
    except Exception as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": {
                    "message": str(e),
                    "type": "api_error",
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": 500
                }
            }
        )

class ProviderModelRequest(BaseModel):
    url: str
    api_key: str

@app.post("/v1/providers/models")
async def fetch_provider_models(request: ProviderModelRequest):
    try:
        # 使用传入的provider配置创建AsyncOpenAI客户端
        client = AsyncOpenAI(api_key=request.api_key, base_url=request.url)
        # 获取模型列表
        model_list = await client.models.list()
        # 提取模型ID并返回
        return JSONResponse(content={"data": [model.id for model in model_list.data]})
    except Exception as e:
        # 处理异常，返回错误信息
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions", operation_id="chat_with_agent_party")
async def chat_endpoint(request: ChatRequest,fastapi_request: Request):
    """
    用来与agent party中的模型聊天
    messages: 必填项，聊天记录，包括role和content
    model: 可选项，默认使用 'super-model'，可以用get_models()获取所有可用的模型
    stream: 可选项，默认为False，是否启用流式响应
    enable_thinking: 默认为False，是否启用思考模式
    enable_deep_research: 默认为False，是否启用深度研究模式
    enable_web_search: 默认为False，是否启用网络搜索
    """
    fastapi_base_url = str(fastapi_request.base_url)
    global client, settings,reasoner_client,mcp_client_list
    model = request.model or 'super-model' # 默认使用 'super-model'
    enable_thinking = request.enable_thinking or False
    enable_deep_research = request.enable_deep_research or False
    enable_web_search = request.enable_web_search or False
    async_tools_id = request.asyncToolsID or None
    if model == 'super-model':
        current_settings = await load_settings()
        if len(current_settings['modelProviders']) <= 0:
            return JSONResponse(
                status_code=500,
                content={"error": {"message": await t("NoModelProvidersConfigured"), "type": "server_error", "code": 500}}
            )
        vendor = 'OpenAI'
        for modelProvider in current_settings['modelProviders']: 
            if modelProvider['id'] == current_settings['selectedProvider']:
                vendor = modelProvider['vendor']
                break
        client_class = AsyncOpenAI
        if vendor == 'Dify':
            client_class = DifyOpenAIAsync
        reasoner_vendor = 'OpenAI'
        for modelProvider in current_settings['modelProviders']: 
            if modelProvider['id'] == current_settings['reasoner']['selectedProvider']:
                reasoner_vendor = modelProvider['vendor']
                break
        reasoner_client_class = AsyncOpenAI
        if reasoner_vendor == 'Dify':
            reasoner_client_class = DifyOpenAIAsync
        # 动态更新客户端配置
        if (current_settings['api_key'] != settings['api_key'] 
            or current_settings['base_url'] != settings['base_url']):
            client = client_class(
                api_key=current_settings['api_key'],
                base_url=current_settings['base_url'] or "https://api.openai.com/v1",
            )
        if (current_settings['reasoner']['api_key'] != settings['reasoner']['api_key'] 
            or current_settings['reasoner']['base_url'] != settings['reasoner']['base_url']):
            reasoner_client = reasoner_client_class(
                api_key=current_settings['reasoner']['api_key'],
                base_url=current_settings['reasoner']['base_url'] or "https://api.openai.com/v1",
            )
        # 将"system_prompt"插入到request.messages[0].content中
        if current_settings['system_prompt']:
            content_prepend(request.messages, 'system', current_settings['system_prompt'] + "\n\n")
        if current_settings != settings:
            settings = current_settings
        try:
            if request.stream:
                return await generate_stream_response(client,reasoner_client, request, settings,fastapi_base_url,enable_thinking,enable_deep_research,enable_web_search,async_tools_id)
            return await generate_complete_response(client,reasoner_client, request, settings,fastapi_base_url,enable_thinking,enable_deep_research,enable_web_search)
        except asyncio.CancelledError:
            # 处理客户端中断连接的情况
            print("Client disconnected")
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error", "code": 500}}
            )
    else:
        current_settings = await load_settings()
        agentSettings = current_settings['agents'].get(model, {})
        if not agentSettings:
            for agentId , agentConfig in current_settings['agents'].items():
                if current_settings['agents'][agentId]['name'] == model:
                    agentSettings = current_settings['agents'][agentId]
                    break
        if not agentSettings:
            return JSONResponse(
                status_code=404,
                content={"error": {"message": f"Agent {model} not found", "type": "not_found", "code": 404}}
            )
        if agentSettings['config_path']:
            with open(agentSettings['config_path'], 'r' , encoding='utf-8') as f:
                agent_settings = json.load(f)
            # 将"system_prompt"插入到request.messages[0].content中
            if agentSettings['system_prompt']:
                content_prepend(request.messages, 'user', agentSettings['system_prompt'] + "\n\n")
        vendor = 'OpenAI'
        for modelProvider in agent_settings['modelProviders']: 
            if modelProvider['id'] == agent_settings['selectedProvider']:
                vendor = modelProvider['vendor']
                break
        client_class = AsyncOpenAI
        if vendor == 'Dify':
            client_class = DifyOpenAIAsync
        reasoner_vendor = 'OpenAI'
        for modelProvider in agent_settings['modelProviders']: 
            if modelProvider['id'] == agent_settings['reasoner']['selectedProvider']:
                reasoner_vendor = modelProvider['vendor']
                break
        reasoner_client_class = AsyncOpenAI
        if reasoner_vendor == 'Dify':
            reasoner_client_class = DifyOpenAIAsync
        agent_client = client_class(
            api_key=agent_settings['api_key'],
            base_url=agent_settings['base_url'] or "https://api.openai.com/v1",
        )
        agent_reasoner_client = reasoner_client_class(
            api_key=agent_settings['reasoner']['api_key'],
            base_url=agent_settings['reasoner']['base_url'] or "https://api.openai.com/v1",
        )
        try:
            if request.stream:
                return await generate_stream_response(agent_client,agent_reasoner_client, request, agent_settings,fastapi_base_url,enable_thinking,enable_deep_research,enable_web_search,async_tools_id)
            return await generate_complete_response(agent_client,agent_reasoner_client, request, agent_settings,fastapi_base_url,enable_thinking,enable_deep_research,enable_web_search)
        except asyncio.CancelledError:
            # 处理客户端中断连接的情况
            print("Client disconnected")
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error", "code": 500}}
            )

@app.post("/simple_chat")
async def simple_chat_endpoint(request: ChatRequest):
    """
    同时支持流式(stream=true)与非流式(stream=false)
    """
    global client, settings

    current_settings = await load_settings()
    if len(current_settings['modelProviders']) <= 0:
        return JSONResponse(
            status_code=500,
            content={"error": {"message": await t("NoModelProvidersConfigured"),
                               "type": "server_error", "code": 500}}
        )

    # --------------- 选 vendor & 初始化 client ---------------
    vendor = 'OpenAI'
    for mp in current_settings['modelProviders']:
        if mp['id'] == current_settings['selectedProvider']:
            vendor = mp['vendor']
            break
    client_class = DifyOpenAIAsync if vendor == 'Dify' else AsyncOpenAI
    if (current_settings['api_key'] != settings['api_key'] or
            current_settings['base_url'] != settings['base_url']):
        client = client_class(
            api_key=current_settings['api_key'],
            base_url=current_settings['base_url'] or "https://api.openai.com/v1",
        )

    # --------------- 调用大模型 ---------------
    response = await client.chat.completions.create(
        model=current_settings['model'],
        messages=request.messages,
        stream=request.stream,
        temperature=request.temperature,
    )

    # --------------- 非流式：一次性返回 JSON ---------------
    if not request.stream:
        # 注意：openai 返回的是 ChatCompletion 对象
        return JSONResponse(content=response.model_dump())

    # --------------- 流式：保持原来的 StreamingResponse ---------------
    async def openai_raw_stream():
        async for chunk in response:
            yield chunk.model_dump_json() + '\n'
        # 不发送 [DONE]

    return StreamingResponse(
        openai_raw_stream(),
        media_type="text/plain",      # 也可以保持 "text/event-stream"
        headers={"Cache-Control": "no-cache"}
    )

def sanitize_proxy_url(input_url: str) -> str:
    """
    针对代理场景优化的 URL 安全过滤
    """
    if not input_url:
        raise HTTPException(status_code=400, detail="URL 不能为空")
    
    # 1. 解析 URL
    parsed = urlparse(input_url)
    
    # 2. 验证协议 (禁止 file://, gopher:// 等协议)
    if parsed.scheme not in ["http", "https"]:
        raise HTTPException(status_code=400, detail="仅支持 http 或 https 协议")
    
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="无效的域名或 IP")

    # 3. 重新构造 URL (消除 SSRF 污点)
    # 排除 userinfo, 只保留必要部分
    safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        safe_url += f"?{parsed.query}"
    if parsed.fragment:
        safe_url += f"#{parsed.fragment}"

    # 4. 内网审计
    if is_private_ip(parsed.hostname):
        logger.warning(f"Internal access detected: {safe_url}")

    return safe_url

# 建议 UA 包含项目地址
USER_AGENT = "Mozilla/5.0 (compatible; OpenSourceProxyBot/1.0)"
ROBOTS_CACHE = {}

# ================= 2. 修改后的代理路由 =================

@app.api_route("/extension_proxy", methods=["GET", "POST"])
async def extension_proxy(request: Request, url: str):
    """
    集成安全校验与 Robots 协议的代理接口
    """
    # --- 阶段 A: 安全校验 ---
    try:
        target_url = sanitize_proxy_url(url)
    except HTTPException as e:
        return Response(content=e.detail, status_code=e.status_code)

    # --- 阶段 B: 合规性校验 (Robots.txt) ---
    is_allowed = await check_robots_txt(target_url)
    if not is_allowed:
        return Response(
            content="Access denied by robots.txt", 
            status_code=403,
            media_type="text/plain"
        )

    # --- 阶段 C: 执行代理请求 ---
    method = request.method
    body = await request.body()
    
    # 构造 Header
    excluded_headers = {'host', 'content-length', 'connection', 'keep-alive'}
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in excluded_headers
    }
    headers["User-Agent"] = USER_AGENT
    
    print(f"--- [Extension Proxy] ---")
    print(f"Safe Target: {target_url} | Method: {method}")
    
    # 使用 trust_env=False 进一步防止被环境变量代理干扰（SSRF 防御一部分）
    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=30.0, trust_env=False) as client:
        try:
            resp = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body
            )
            
            # 透传响应头
            resp_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in {'content-encoding', 'content-length', 'transfer-encoding', 'server'}
            }
            
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers,
                media_type=resp.headers.get("content-type", "application/octet-stream")
            )

        except httpx.ConnectError as e:
            err_msg = f"Proxy Connect Error: {e}"
            if "json" in request.headers.get("accept", "").lower():
                 return Response(content=f'{{"error": "{err_msg}"}}', status_code=502, media_type="application/json")
            return Response(content=f"<error>{err_msg}</error>", status_code=502, media_type="text/xml")
            
        except Exception as e:
            print(f"[Proxy Error] System: {repr(e)}")
            traceback.print_exc()
            return Response(content="Internal Server Error during proxy", status_code=500)

        
# 存储活跃的ASR WebSocket连接
asr_connections = []

# 存储每个连接的音频帧数据
audio_buffer: Dict[str, Dict[str, Any]] = {}

def convert_audio_to_pcm16(audio_bytes: bytes, target_sample_rate: int = 16000) -> bytes:
    """
    将音频数据转换为PCM16格式，采样率16kHz
    """
    import numpy as np
    from scipy.io import wavfile
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        try:
            # 读取音频文件
            sample_rate, audio_data = wavfile.read(temp_file_path)
            
            # 转换为单声道
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # 转换为float32进行重采样
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            # 重采样到目标采样率
            if sample_rate != target_sample_rate:
                from scipy.signal import resample
                num_samples = int(len(audio_data) * target_sample_rate / sample_rate)
                audio_data = resample(audio_data, num_samples)
            
            # 转换为int16 PCM格式
            audio_data = (audio_data * 32767).astype(np.int16)
            
            return audio_data.tobytes()
            
        finally:
            # 删除临时文件
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"Audio conversion error: {e}")
        # 如果转换失败，尝试直接返回原始数据
        return audio_bytes

async def funasr_recognize(audio_data: bytes, funasr_settings: dict,ws: WebSocket,frame_id) -> str:
    """
    使用FunASR进行语音识别
    """
    try:
        # 获取FunASR服务器地址
        funasr_url = funasr_settings.get('funasr_ws_url', 'ws://localhost:10095')
        hotwords = funasr_settings.get('hotwords', '')
        if not funasr_url.startswith('ws://') and not funasr_url.startswith('wss://'):
            funasr_url = f"ws://{funasr_url}"
        
        # 连接到FunASR服务器
        async with websockets.connect(funasr_url) as websocket:
            print(f"Connected to FunASR server: {funasr_url}")
            
            # 1. 发送初始化配置
            init_config = {
                "chunk_size": [5, 10, 5],
                "wav_name": "python_client",
                "is_speaking": True,
                "chunk_interval": 10,
                "mode": "offline",  # 使用离线模式
                "hotwords": hotwords_to_json(hotwords),
                "use_itn": True
            }
            
            await websocket.send(json.dumps(init_config))
            print("Sent init config")
            
            # 2. 转换音频数据为PCM16格式
            pcm_data = convert_audio_to_pcm16(audio_data)
            print(f"PCM data length: {len(pcm_data)} bytes")
            
            # 3. 分块发送音频数据
            chunk_size = 960  # 30ms的音频数据 (16000 * 0.03 * 2 = 960字节)
            total_sent = 0
            
            while total_sent < len(pcm_data):
                chunk_end = min(total_sent + chunk_size, len(pcm_data))
                chunk = pcm_data[total_sent:chunk_end]
                
                # 发送二进制PCM数据
                await websocket.send(chunk)
                total_sent = chunk_end
            
            print(f"Sent all audio data: {total_sent} bytes")
            
            # 4. 发送结束信号
            end_config = {
                "is_speaking": False,
            }
            
            await websocket.send(json.dumps(end_config))
            print("Sent end signal")
            
            # 5. 等待识别结果
            result_text = ""
            timeout_count = 0
            max_timeout = 200  # 最大等待20秒
            
            while timeout_count < max_timeout:
                try:
                    # 等待响应消息
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    
                    try:
                        # 尝试解析JSON响应
                        json_response = json.loads(response)
                        print(f"Received response: {json_response}")
                        
                        if 'text' in json_response:
                            text = json_response['text']
                            if text and text.strip():
                                result_text += text
                                print(f"Got text: {text}")
                                # 发送结果
                                await ws.send_json({
                                    "type": "transcription",
                                    "id": frame_id,
                                    "text": result_text,
                                    "is_final": True
                                })
                            # 检查是否为最终结果
                            if json_response.get('is_final', False):
                                print("Got final result")
                                break
                                
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，可能是二进制数据，忽略
                        print(f"Non-JSON response: {response}")
                        pass
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break
            
            if not result_text:
                print("No recognition result received")
                return ""
            
            return result_text.strip()
            
    except Exception as e:
        print(f"FunASR recognition error: {e}")
        traceback.print_exc()
        return f"FunASR识别错误: {str(e)}"

def hotwords_to_json(input_str):
    # 初始化结果字典
    result = {}
    
    # 按行分割输入字符串
    lines = input_str.split('\n')
    
    for line in lines:
        # 清理行首尾的空白字符
        cleaned_line = line.strip()
        
        # 跳过空行
        if not cleaned_line:
            continue
            
        # 分割词语和权重
        parts = cleaned_line.rsplit(' ', 1)  # 从右边分割一次
        
        if len(parts) != 2:
            continue  # 跳过格式不正确的行
            
        word = parts[0].strip()
        try:
            weight = int(parts[1])
        except ValueError:
            continue  # 跳过权重不是数字的行
            
        # 添加到结果字典
        result[word] = weight
    
    # 转换为JSON字符串
    return json.dumps(result, ensure_ascii=False)

# ASR WebSocket处理
@app.websocket("/ws/asr")
async def asr_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 生成唯一的连接ID
    connection_id = str(uuid.uuid4())
    asr_connections.append(websocket)
    funasr_websocket = None
    # 新增：连接状态跟踪变量
    asr_engine = None
    funasr_mode = None
    
    try:
        # 处理消息
        async for message in websocket.iter_json():
            msg_type = message.get("type")
            
            if msg_type == "init":
                # 加载设置
                settings = await load_settings()
                asr_settings = settings.get('asrSettings', {})
                asr_engine = asr_settings.get('engine', 'openai')  # 存储引擎类型
                if asr_engine == "funasr":
                    funasr_mode = asr_settings.get('funasr_mode', 'openai')  # 存储模式
                    if funasr_mode == "2pass" or funasr_mode == "online":
                        # 获取FunASR服务器地址
                        funasr_url = asr_settings.get('funasr_ws_url', 'ws://localhost:10095')
                        if not funasr_url.startswith('ws://') and not funasr_url.startswith('wss://'):
                            funasr_url = f"ws://{funasr_url}"
                        try:
                            funasr_websocket = await websockets.connect(funasr_url)
                        except Exception as e:
                            funasr_websocket = None
                            print(f"连接FunASR失败: {e}")
                await websocket.send_json({
                    "type": "init_response",
                    "status": "ready"
                })
                print("ASR WebSocket connected:",asr_engine)
            elif msg_type == "audio_start":
                frame_id = message.get("id")
                # 加载设置
                settings = await load_settings()
                asr_settings = settings.get('asrSettings', {})
                asr_engine = asr_settings.get('engine', 'openai')  # 存储引擎类型
                if asr_engine == "funasr":
                    funasr_mode = asr_settings.get('funasr_mode', '2pass')  # 存储模式
                    hotwords = asr_settings.get('hotwords', '')
                    if funasr_mode == "2pass":
                        # 获取FunASR服务器地址
                        funasr_url = asr_settings.get('funasr_ws_url', 'ws://localhost:10095')
                        if not funasr_url.startswith('ws://') and not funasr_url.startswith('wss://'):
                            funasr_url = f"ws://{funasr_url}"
                        try:
                            if not funasr_websocket:
                                # 连接到FunASR服务器 
                                funasr_websocket = await websockets.connect(funasr_url)
                            # 1. 发送初始化配置
                            init_config = {
                                "chunk_size": [5, 10, 5],
                                "wav_name": "python_client",
                                "is_speaking": True,
                                "chunk_interval": 10,
                                "mode": funasr_mode,  
                                "hotwords": hotwords_to_json(hotwords),
                                "use_itn": True
                            }
                            await funasr_websocket.send(json.dumps(init_config))
                            print("Sent init config")
                            # 2. 开启一个异步任务处理FunASR的响应
                            asyncio.create_task(handle_funasr_response(funasr_websocket, websocket))
                        except Exception as e:
                            print(f"连接FunASR失败: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"无法连接FunASR服务器: {str(e)}"
                            })
                            # 标记连接失败，避免后续操作
                            funasr_websocket = None
                    else:
                        # 关闭异步任务处理FunASR的响应
                        funasr_websocket = None
                else:
                    # 关闭异步任务处理FunASR的响应
                    funasr_websocket = None
            # 修改点：增加流式音频处理前的检查
            elif msg_type == "audio_stream":
                frame_id = message.get("id")
                audio_base64 = message.get("audio")

                # 关键检查：确保funasr_websocket已初始化
                if not funasr_websocket:
                    continue  # 跳过当前消息处理

                if audio_base64:
                    # 1. Base64 解码 → 得到二进制 PCM (Int16)
                    pcm_data = base64.b64decode(audio_base64)

                    # 2. 直接转发二进制给 FunASR
                    try:
                        await funasr_websocket.send(pcm_data)
                    except websockets.exceptions.ConnectionClosed:
                        funasr_websocket = None
                        # 加载设置
                        settings = await load_settings()
                        asr_settings = settings.get('asrSettings', {})
                        asr_engine = asr_settings.get('engine', 'openai')  # 存储引擎类型
                        if asr_engine == "funasr":
                            funasr_mode = asr_settings.get('funasr_mode', '2pass')  # 存储模式
                            if funasr_mode == "2pass":
                                # 获取FunASR服务器地址
                                funasr_url = asr_settings.get('funasr_ws_url', 'ws://localhost:10095')
                                if not funasr_url.startswith('ws://') and not funasr_url.startswith('wss://'):
                                    funasr_url = f"ws://{funasr_url}"
                                try:
                                    funasr_websocket = await websockets.connect(funasr_url)
                                except Exception as e:
                                    funasr_websocket = None
                                    print(f"连接FunASR失败: {e}")
            elif msg_type == "audio_complete":
                # 处理完整的音频数据（非流式模式）
                frame_id = message.get("id")
                audio_b64 = message.get("audio")
                audio_format = message.get("format", "wav")
                
                if audio_b64:
                    # 解码base64数据
                    audio_bytes = base64.b64decode(audio_b64)
                    print(f"Received audio data: {len(audio_bytes)} bytes, format: {audio_format}")
                    
                    try:
                        # 加载设置
                        settings = await load_settings()
                        asr_settings = settings.get('asrSettings', {})
                        asr_engine = asr_settings.get('engine', 'openai')
                        
                        result = ""
                        
                        if asr_engine == "openai":
                            # OpenAI ASR
                            audio_file = BytesIO(audio_bytes)
                            audio_file.name = f"audio.{audio_format}"
                            
                            client = AsyncOpenAI(
                                api_key=asr_settings.get('api_key', ''),
                                base_url=asr_settings.get('base_url', '') or "https://api.openai.com/v1"
                            )
                            response = await client.audio.transcriptions.create(
                                file=audio_file,
                                model=asr_settings.get('model', 'whisper-1'),
                            )
                            result = response.text
                            # 发送结果
                            await websocket.send_json({
                                "type": "transcription",
                                "id": frame_id,
                                "text": result,
                                "is_final": True
                            })
                        elif asr_engine == "funasr":
                            # FunASR
                            print("Using FunASR engine")
                            funasr_mode = asr_settings.get('funasr_mode', 'offline')
                            if funasr_mode == "offline":
                                result = await funasr_recognize(audio_bytes, asr_settings,websocket,frame_id)
                            else:
                                # 关键检查：确保连接有效
                                if not funasr_websocket:
                                    continue
                                
                                # 4. 发送结束信号
                                end_config = {
                                    "is_speaking": False  # 只需发送必要的结束标记
                                }
                                try:
                                    await funasr_websocket.send(json.dumps(end_config))
                                    print("Sent end signal")
                                except websockets.exceptions.ConnectionClosed:
                                    print("FunASR连接已关闭，无法发送结束信号")
                            funasr_websocket = None

                        elif asr_engine == "sherpa":
                            from py.sherpa_asr import sherpa_recognize
                            # 新增Sherpa处理
                            result = await sherpa_recognize(audio_bytes)
                            print(f"Sherpa result: {result}")
                            await websocket.send_json({
                                "type": "transcription",
                                "id": frame_id,
                                "text": result,
                                "is_final": True
                            })
                    except WebSocketDisconnect:
                        print(f"ASR WebSocket disconnected: {connection_id}")
                    except Exception as e:
                        print(f"ASR WebSocket error: {e}")
                        traceback.print_exc()
    finally:
        # 清理资源
        if connection_id in audio_buffer:
            del audio_buffer[connection_id]
        if websocket in asr_connections:
            asr_connections.remove(websocket)
        # 新增：确保关闭FunASR连接
        if funasr_websocket:
            await funasr_websocket.close()

@app.post("/asr")
async def asr_transcription(
    audio: UploadFile = File(...),
    format: str = Form(default="auto")
):
    """
    HTTP版本的ASR接口
    支持多种音频格式，根据配置自动选择ASR引擎
    """
    try:
        # 读取上传的音频文件
        audio_bytes = await audio.read()
        print(f"Received audio file: {audio.filename}, size: {len(audio_bytes)} bytes")
        
        # 自动检测格式（如果用户没有指定）
        if format == "auto":
            if audio.filename:
                file_ext = audio.filename.split('.')[-1].lower()
                format = file_ext if file_ext in ['wav', 'mp3', 'flac', 'ogg', 'm4a'] else 'wav'
            else:
                format = 'wav'
        
        # 加载设置
        settings = await load_settings()
        asr_settings = settings.get('asrSettings', {})
        asr_engine = asr_settings.get('engine', 'openai')
        
        result = ""
        
        if asr_engine == "openai":
            # OpenAI ASR
            print("Using OpenAI ASR engine")
            audio_file = BytesIO(audio_bytes)
            audio_file.name = f"audio.{format}"
            
            client = AsyncOpenAI(
                api_key=asr_settings.get('api_key', ''),
                base_url=asr_settings.get('base_url', '') or "https://api.openai.com/v1"
            )
            
            response = await client.audio.transcriptions.create(
                file=audio_file,
                model=asr_settings.get('model', 'whisper-1'),
            )
            result = response.text
            
        elif asr_engine == "funasr":
            # FunASR（强制使用离线模式）
            print("Using FunASR engine (offline mode)")
            result = await funasr_recognize_offline(audio_bytes, asr_settings)
            
        elif asr_engine == "sherpa":
            from py.sherpa_asr import sherpa_recognize
            # Sherpa ASR
            print("Using Sherpa ASR engine")
            result = await sherpa_recognize(audio_bytes)
        
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"不支持的ASR引擎: {asr_engine}",
                    "text": ""
                }
            )
        
        # 返回识别结果
        return JSONResponse(
            content={
                "success": True,
                "text": result.strip(),
                "engine": asr_engine,
                "format": format
            }
        )
        
    except Exception as e:
        print(f"ASR HTTP interface error: {e}")
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "text": ""
            }
        )

async def funasr_recognize_offline(audio_data: bytes, funasr_settings: dict) -> str:
    """
    FunASR离线识别（专为HTTP接口优化）
    """
    try:
        # 获取FunASR服务器地址
        funasr_url = funasr_settings.get('funasr_ws_url', 'ws://localhost:10095')
        hotwords = funasr_settings.get('hotwords', '')
        if not funasr_url.startswith('ws://') and not funasr_url.startswith('wss://'):
            funasr_url = f"ws://{funasr_url}"
        
        # 连接到FunASR服务器
        async with websockets.connect(funasr_url) as websocket:
            print(f"Connected to FunASR server: {funasr_url}")
            
            # 1. 发送初始化配置（强制离线模式）
            init_config = {
                "chunk_size": [5, 10, 5],
                "wav_name": "http_client",
                "is_speaking": True,
                "chunk_interval": 10,
                "mode": "offline",  # 强制使用离线模式
                "hotwords": hotwords_to_json(hotwords),
                "use_itn": True
            }
            
            await websocket.send(json.dumps(init_config))
            print("Sent init config for offline mode")
            
            # 2. 转换音频数据为PCM16格式
            pcm_data = convert_audio_to_pcm16(audio_data)
            print(f"PCM data length: {len(pcm_data)} bytes")
            
            # 3. 分块发送音频数据
            chunk_size = 960  # 30ms的音频数据
            total_sent = 0
            
            while total_sent < len(pcm_data):
                chunk_end = min(total_sent + chunk_size, len(pcm_data))
                chunk = pcm_data[total_sent:chunk_end]
                await websocket.send(chunk)
                total_sent = chunk_end
            
            print(f"Sent all audio data: {total_sent} bytes")
            
            # 4. 发送结束信号
            end_config = {
                "is_speaking": False,
            }
            await websocket.send(json.dumps(end_config))
            print("Sent end signal")
            
            # 5. 等待识别结果
            result_text = ""
            timeout_count = 0
            max_timeout = 300  # 最大等待30秒（HTTP接口可以等待更久）
            
            while timeout_count < max_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    
                    try:
                        json_response = json.loads(response)
                        print(f"Received response: {json_response}")
                        
                        if 'text' in json_response:
                            text = json_response['text']
                            if text and text.strip():
                                result_text += text
                                print(f"Got text: {text}")
                            
                            # 检查是否为最终结果
                            if json_response.get('is_final', False):
                                print("Got final result")
                                break
                                
                    except json.JSONDecodeError:
                        # 忽略非JSON格式的响应
                        pass
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break
            
            if not result_text:
                print("No recognition result received")
                return ""
            
            return result_text.strip()
            
    except Exception as e:
        print(f"FunASR offline recognition error: {e}")
        traceback.print_exc()
        return f"FunASR识别错误: {str(e)}"


async def handle_funasr_response(funasr_websocket, 
                               client_websocket: WebSocket):
    """
    处理 FunASR 服务器的响应，并将结果转发给客户端
    """
    try:
        async for message in funasr_websocket:
            try:
                if funasr_websocket:
                    # FunASR 返回的数据可能是 JSON 或二进制
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    
                    data = json.loads(message)
                    print(f"FunASR response: {data}")
                    # 解析 FunASR 响应
                    if "text" in data:  # 普通识别结果
                        if data.get('mode', '') == "2pass-online":
                            await client_websocket.send_json({
                                "type": "transcription",
                                "text": data["text"],
                                "is_final": False
                            })
                        else:
                            await client_websocket.send_json({
                                "type": "transcription",
                                "text": data["text"],
                                "is_final": True
                            })
                    elif "mode" in data:  # 初始化响应
                        print(f"FunASR initialized: {data}")
                    else:
                        print(f"Unknown FunASR response: {data}")
                else:
                    # 如果 FunASR 连接关闭，发送错误消息，退出循环，结束任务
            
                    break
            except json.JSONDecodeError:
                print(f"FunASR sent non-JSON data: {message[:100]}...")
            except Exception as e:
                print(f"Error processing FunASR response: {e}")
                break

    except websockets.exceptions.ConnectionClosed:
        print("FunASR connection closed")
    except Exception as e:
        print(f"FunASR handler error: {e}")
    finally:
        await funasr_websocket.close()

class TTSConnectionManager:
    def __init__(self):
        self.main_connections: List[WebSocket] = []
        self.vrm_connections: List[WebSocket] = []
        self.audio_cache: Dict[str, bytes] = {}  # 缓存音频数据
        
    async def connect_main(self, websocket: WebSocket):
        await websocket.accept()
        self.main_connections.append(websocket)
        logging.info(f"Main interface connected. Total: {len(self.main_connections)}")
        
    async def connect_vrm(self, websocket: WebSocket):
        await websocket.accept()
        self.vrm_connections.append(websocket)
        logging.info(f"VRM interface connected. Total: {len(self.vrm_connections)}")
        
    def disconnect_main(self, websocket: WebSocket):
        if websocket in self.main_connections:
            self.main_connections.remove(websocket)
            logging.info(f"Main interface disconnected. Total: {len(self.main_connections)}")
            
    def disconnect_vrm(self, websocket: WebSocket):
        if websocket in self.vrm_connections:
            self.vrm_connections.remove(websocket)
            logging.info(f"VRM interface disconnected. Total: {len(self.vrm_connections)}")
    
    async def broadcast_to_vrm(self, message: dict):
        """广播消息到所有VRM连接"""
        if self.vrm_connections:
            message_str = json.dumps(message)
            disconnected = []
            
            for connection in self.vrm_connections:
                try:
                    await connection.send_text(message_str)
                except:
                    disconnected.append(connection)
            
            # 清理断开的连接
            for conn in disconnected:
                self.disconnect_vrm(conn)
    
    async def send_to_main(self, message: dict):
        """发送消息到主界面"""
        if self.main_connections:
            message_str = json.dumps(message)
            disconnected = []
            
            for connection in self.main_connections:
                try:
                    await connection.send_text(message_str)
                except:
                    disconnected.append(connection)
            
            # 清理断开的连接
            for conn in disconnected:
                self.disconnect_main(conn)
    
    def cache_audio(self, audio_id: str, audio_data: bytes):
        """缓存音频数据"""
        self.audio_cache[audio_id] = audio_data
        
    def get_cached_audio(self, audio_id: str) -> bytes:
        """获取缓存的音频数据"""
        return self.audio_cache.get(audio_id)

# 创建连接管理器实例
tts_manager = TTSConnectionManager()

@app.websocket("/ws/tts")
async def tts_websocket_endpoint(websocket: WebSocket):
    """主界面的WebSocket连接"""
    await tts_manager.connect_main(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logging.info(f"Received from main: {message['type']}")
            
            # 如果消息包含音频URL，需要特殊处理
            if message['type'] == 'startSpeaking' and 'audioUrl' in message['data']:
                # 获取音频数据并转换为base64
                audio_url = message['data']['audioUrl']
                chunk_index = message['data']['chunkIndex']
                expressions = message['data']['expressions']
                # 生成音频ID
                audio_id = f"chunk_{chunk_index}_{message['data'].get('timestamp', '')}"
                
                # 修改消息，使用音频ID而不是URL
                message['data']['audioId'] = audio_id
                message['data']['useBase64'] = True
                
                # 如果有缓存的音频数据，直接发送
                cached_audio = tts_manager.get_cached_audio(audio_id)
                if cached_audio:
                    message['data']['audioData'] = base64.b64encode(cached_audio).decode('utf-8')
            
            # 转发到所有VRM连接
            await tts_manager.broadcast_to_vrm({
                'type': message['type'],
                'data': message['data'],
                'timestamp': message.get('timestamp', None)
            })
            
    except WebSocketDisconnect:
        tts_manager.disconnect_main(websocket)
    except Exception as e:
        logging.error(f"WebSocket error in main connection: {e}")
        tts_manager.disconnect_main(websocket)

@app.websocket("/ws/vrm")
async def vrm_websocket_endpoint(websocket: WebSocket):
    """VRM界面的WebSocket连接"""
    await tts_manager.connect_vrm(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logging.info(f"Received from VRM: {message['type']}")
            
            # 处理VRM请求音频数据
            if message['type'] == 'requestAudioData':
                audio_id = message['data']['audioId']
                expressions = message['data']['expressions']
                text = message['data']['text']
                cached_audio = tts_manager.get_cached_audio(audio_id)
                
                if cached_audio:
                    await websocket.send_text(json.dumps({
                        'type': 'audioData',
                        'data': {
                            'audioId': audio_id,
                            'audioData': base64.b64encode(cached_audio).decode('utf-8'),
                            'expressions':expressions,
                            'text':text
                        }
                    }))
            
            # 可以处理VRM发送的状态信息
            elif message['type'] == 'animationComplete':
                await tts_manager.send_to_main({
                    'type': 'vrmAnimationComplete',
                    'data': message['data']
                })
            
    except WebSocketDisconnect:
        tts_manager.disconnect_vrm(websocket)
    except Exception as e:
        logging.error(f"WebSocket error in VRM connection: {e}")
        tts_manager.disconnect_vrm(websocket)


@app.get("/tts/status")
async def get_tts_status():
    """获取当前TTS连接状态"""
    return {
        "main_connections": len(tts_manager.main_connections),
        "vrm_connections": len(tts_manager.vrm_connections),
        "total_connections": len(tts_manager.main_connections) + len(tts_manager.vrm_connections)
    }


@app.post("/tts")
async def text_to_speech(request: Request):
    import edge_tts
    try:
        data = await request.json()
        text = data['text']
        if text == "":
            return JSONResponse(status_code=400, content={"error": "Text is empty"})
        
        # 移动端专用：强制使用opus格式
        mobile_optimized = data.get('mobile_optimized', False)
        target_format = "opus" if mobile_optimized else data.get('format', 'mp3')
        
        new_voice = data.get('voice','default')
        tts_settings = data['ttsSettings']
        if new_voice in tts_settings['newtts'] and new_voice!='default':
            # 获取新声音的配置
            voice_settings = tts_settings['newtts'][new_voice]
            parent_settings = tts_settings
            
            # 从父配置继承关键字段（只继承非空值）
            inherited_fields = ['api_key', 'base_url', 'model', 'selectedProvider', 'vendor']
            for field in inherited_fields:
                # 只在子配置中不存在或为空，且父配置中有非空值时继承
                child_value = voice_settings.get(field, '')
                parent_value = parent_settings.get(field, '')
                if not child_value and parent_value:
                    voice_settings[field] = parent_value
            
            # 如果有selectedProvider但仍缺少api_key，从modelProviders中查找
            selected_provider_id = voice_settings.get('selectedProvider')
            if selected_provider_id and not voice_settings.get('api_key'):
                model_providers = parent_settings.get('modelProviders', [])
                for provider in model_providers:
                    if provider.get('id') == selected_provider_id:
                        voice_settings['api_key'] = provider.get('apiKey', '')
                        voice_settings['base_url'] = provider.get('url', '')
                        voice_settings['model'] = provider.get('modelId', '')
                        voice_settings['vendor'] = provider.get('vendor', '')
                        break
            
            tts_settings = voice_settings
        index = data['index']
        tts_engine = tts_settings.get('engine', 'edgetts')
                
        print(f"TTS请求 - 引擎: {tts_engine}, 格式: {target_format}, 移动端优化: {mobile_optimized}")
                
        if tts_engine == 'edgetts':
            edgettsLanguage = tts_settings.get('edgettsLanguage', 'zh-CN')
            edgettsVoice = tts_settings.get('edgettsVoice', 'XiaoyiNeural')
            rate = tts_settings.get('edgettsRate', 1.0)
            full_voice_name = f"{edgettsLanguage}-{edgettsVoice}"
            
            # 飞书优化：稍微降低语速
            if mobile_optimized:
                rate = min(rate * 0.95, 1.1)
            
            rate_text = "+0%"
            if rate >= 1.0:
                rate_pent = (rate - 1.0) * 100
                rate_text = f"+{int(rate_pent)}%"
            elif rate < 1.0:
                rate_pent = (1.0 - rate) * 100
                rate_text = f"-{int(rate_pent)}%"
            
            async def generate_audio():
                communicate = edge_tts.Communicate(text, full_voice_name, rate=rate_text)
                
                if target_format == "opus":
                    # 需要转换为opus，收集完整数据
                    audio_chunks = []
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_chunks.append(chunk["data"])
                    
                    full_audio = b''.join(audio_chunks)
                    opus_audio = await convert_to_opus_simple(full_audio)
                    
                    # 分块返回opus数据
                    chunk_size = 4096
                    for i in range(0, len(opus_audio), chunk_size):
                        yield opus_audio[i:i + chunk_size]
                else:
                    # 真流式：直接返回mp3格式，不等待完整数据
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            yield chunk["data"]
            
            # 设置正确的媒体类型和文件名
            if target_format == "opus":
                media_type = "audio/ogg"  # opus通常包装在ogg容器中
                filename = f"tts_{index}.opus"
            else:
                media_type = "audio/mpeg"  # EdgeTTS默认返回mp3
                filename = f"tts_{index}.mp3"
            
            return StreamingResponse(
                generate_audio(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "X-Audio-Index": str(index),
                    "X-Audio-Format": target_format
                }
            )

        elif tts_engine == 'customTTS':
            # 从 tts_settings 中获取用户配置的键名，如果未配置，则使用默认值
            key_text = tts_settings.get('customTTSKeyText', 'text')
            key_speaker = tts_settings.get('customTTSKeySpeaker', 'speaker')
            key_speed = tts_settings.get('customTTSKeySpeed', 'speed')

            # 获取用户配置的 speaker 和 speed 的值
            speaker_value = tts_settings.get('customTTSspeaker', '')
            speed_value = tts_settings.get('customTTSspeed', 1.0)
            
            # 移动端优化
            if mobile_optimized:
                speed_value = min(speed_value * 0.95, 1.2)

            # 使用用户配置的键名构建 params
            params = {
                key_text: text,
                key_speaker: speaker_value,
                key_speed: speed_value,
            }
            
            custom_tts_servers_list = tts_settings.get('customTTSserver', 'http://127.0.0.1:9880').split('\n')
            custom_tts_servers_list = [server for server in custom_tts_servers_list if server.strip()]
            custom_tt_server = custom_tts_servers_list[index % len(custom_tts_servers_list)]
            
            # 获取流式配置
            custom_streaming = tts_settings.get('customStream', False)
            
            async def generate_audio():
                safe_tts_url = sanitize_url(
                    input_url=custom_tt_server,
                    default_base="http://127.0.0.1:9880", # 这里填你代码里原本的默认 TTS 地址
                    endpoint=""  # 因为 TTS URL 通常已经包含了路径
                )
                async with httpx.AsyncClient(timeout=60.0) as client:
                    try:
                        async with client.stream("GET", safe_tts_url, params=params) as response:
                            response.raise_for_status()
                            
                            if custom_streaming:
                                # 流式模式：直接返回数据，假设服务端能返回正确格式
                                async for chunk in response.aiter_bytes():
                                    yield chunk
                            else:
                                # 非流式模式：收集完整数据，进行格式转换
                                audio_chunks = []
                                async for chunk in response.aiter_bytes():
                                    audio_chunks.append(chunk)
                                
                                full_audio = b''.join(audio_chunks)
                                
                                # 转换为opus
                                if target_format == "opus":
                                    opus_audio = await convert_to_opus_simple(full_audio)
                                    chunk_size = 4096
                                    for i in range(0, len(opus_audio), chunk_size):
                                        yield opus_audio[i:i + chunk_size]
                                else:
                                    chunk_size = 4096
                                    for i in range(0, len(full_audio), chunk_size):
                                        yield full_audio[i:i + chunk_size]
                                        
                    except httpx.RequestError as e:
                        raise HTTPException(status_code=502, detail=f"Custom TTS 连接失败: {str(e)}")

            # 根据流式模式和目标格式设置媒体类型和文件名
            if custom_streaming:
                # 流式模式：假设返回的格式与目标格式一致
                if target_format == "opus":
                    media_type = "audio/ogg"
                    filename = f"tts_{index}.opus"
                else:
                    # 默认假设是wav格式
                    media_type = "audio/wav"
                    filename = f"tts_{index}.wav"
            else:
                # 非流式模式：保持原有逻辑
                if target_format == "opus":
                    media_type = "audio/ogg"
                    filename = f"tts_{index}.opus"
                else:
                    media_type = "audio/wav"
                    filename = f"tts_{index}.wav"

            return StreamingResponse(
                generate_audio(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "X-Audio-Index": str(index),
                    "X-Audio-Format": target_format
                }
            )

        elif tts_engine == 'GSV':
            # GSV生成ogg格式，检查是否可以直接作为opus使用
            audio_path = os.path.join(UPLOAD_FILES_DIR, tts_settings.get('gsvRefAudioPath', ''))
            if not os.path.exists(audio_path):
                audio_path = tts_settings.get('gsvRefAudioPath', '')

            gsv_params = {
                "text": text,
                "text_lang": tts_settings.get('gsvTextLang', 'zh'),
                "ref_audio_path": audio_path,
                "prompt_lang": tts_settings.get('gsvPromptLang', 'zh'),
                "prompt_text": tts_settings.get('gsvPromptText', ''),
                "speed_factor": tts_settings.get('gsvRate', 1.0),
                "sample_steps": tts_settings.get('gsvSample_steps', 4),
                "streaming_mode": True,
                "text_split_method": "cut0",
                "media_type": "ogg",
                "batch_size": 20,
                "seed": 42,
            }
            
            if mobile_optimized:
                gsv_params["speed_factor"] = min(gsv_params["speed_factor"] * 0.95, 1.1)
            
            gsvServer_list = tts_settings.get('gsvServer', 'http://127.0.0.1:9880').split('\n')
            gsvServer_list = [server for server in gsvServer_list if server.strip()]
            gsvServer = gsvServer_list[index % len(gsvServer_list)]
                
            async def generate_audio():
                safe_tts_url = sanitize_url(
                    input_url=gsvServer,
                    default_base="http://127.0.0.1:9880", # 这里填你代码里原本的默认 TTS 地址
                    endpoint="/tts"  # 因为 TTS URL 通常已经包含了路径
                )
                async with httpx.AsyncClient(timeout=60.0) as client:
                    try:
                        async with client.stream("POST", safe_tts_url, json=gsv_params) as response:
                            response.raise_for_status()
                            # 直接流式返回，不管目标格式（假设GSV的ogg内部是opus编码）
                            async for chunk in response.aiter_bytes():
                                yield chunk
                                
                    except httpx.HTTPStatusError as e:
                        error_detail = f"GSV服务错误: {e.response.status_code}"
                        raise HTTPException(status_code=502, detail=error_detail)
            
            # 统一使用ogg媒体类型，但文件名根据目标格式调整
            media_type = "audio/ogg"
            filename = f"tts_{index}.opus" if target_format == "opus" else f"tts_{index}.ogg"
            
            return StreamingResponse(
                generate_audio(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "X-Audio-Index": str(index),
                    "X-Audio-Format": target_format
                }
            )
            
        elif tts_engine == 'openai':
            # OpenAI TTS处理
            openai_config = {
                'api_key': tts_settings.get('api_key', ''),
                'model': tts_settings.get('model', 'tts-1'),
                'voice': tts_settings.get('openaiVoice', 'alloy'),
                'speed': tts_settings.get('openaiSpeed', 1.0),
                'base_url': tts_settings.get('base_url', 'https://api.openai.com/v1'),
                'prompt_text': tts_settings.get('gsvPromptText', ''),
                'ref_audio': tts_settings.get('gsvRefAudioPath', ''),
                'streaming': tts_settings.get('openaiStream', False)
            }
            
            if not openai_config['api_key']:
                raise HTTPException(status_code=400, detail="OpenAI API密钥未配置")
            
            speed = float(openai_config['speed'])
            if mobile_optimized:
                speed = min(speed * 0.95, 1.2)
            
            speed = max(0.25, min(4.0, speed))

            async def generate_audio():
                try:
                    client = AsyncOpenAI(
                        api_key=openai_config['api_key'],
                        base_url=openai_config['base_url']
                    )
                    
                    # 根据目标格式设置response_format
                    response_format = target_format if target_format in ['mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'] else 'mp3'
                    
                    # 准备请求参数
                    request_params = {
                        'model': openai_config['model'],
                        'input': text,
                        'speed': speed,
                        'response_format': response_format
                    }
                    
                    # 处理参考音频
                    if openai_config['ref_audio']:
                        audio_file_path = os.path.join(UPLOAD_FILES_DIR, openai_config['ref_audio'])
                        with open(audio_file_path, "rb") as audio_file:
                            audio_data = audio_file.read()
                        audio_type = Path(audio_file_path).suffix[1:]
                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                        audio_uri = f"data:audio/{audio_type};base64,{audio_base64}"
                        
                        request_params['voice'] = None
                        request_params['extra_body'] = {
                            "references": [{"text": openai_config['prompt_text'], "audio": audio_uri}]
                        }
                    else:
                        request_params['voice'] = openai_config['voice']
                    
                    # 根据流式设置选择调用方式
                    if openai_config['streaming']:
                        # 流式模式 - 真正的流式，无需格式转换
                        async with client.audio.speech.with_streaming_response.create(**request_params) as response:
                            async for chunk in response.iter_bytes(chunk_size=4096):
                                yield chunk
                                await asyncio.sleep(0)
                    else:
                        # 非流式模式
                        response = await client.audio.speech.create(**request_params)
                        content = await response.aread()
                        
                        # 分块返回
                        chunk_size = 4096
                        for i in range(0, len(content), chunk_size):
                            yield content[i:i + chunk_size]
                            await asyncio.sleep(0)
                                
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"OpenAI TTS错误: {str(e)}")
            
            # 根据目标格式设置媒体类型和文件名
            if target_format == "opus":
                media_type = "audio/ogg"  # opus通常用ogg容器
                filename = f"tts_{index}.opus"
            elif target_format == "wav":
                media_type = "audio/wav"
                filename = f"tts_{index}.wav"
            elif target_format == "aac":
                media_type = "audio/aac"
                filename = f"tts_{index}.aac"
            elif target_format == "flac":
                media_type = "audio/flac"
                filename = f"tts_{index}.flac"
            else:  # mp3 或其他
                media_type = "audio/mpeg"
                filename = f"tts_{index}.mp3"
            
            return StreamingResponse(
                generate_audio(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "X-Audio-Index": str(index),
                    "X-Audio-Format": target_format
                }
            )
        elif tts_engine == 'systemtts':
            import platform
            import subprocess
            import uuid
            # 注意：pyttsx3 不要在全局导入，防止在 Mac 上干扰主线程

            # ==========================================
            # System TTS (Cross-Platform) 引擎
            # ==========================================
            
            # 1. 获取配置参数
            system_voice_name = tts_settings.get('systemVoiceName', None)
            system_rate = tts_settings.get('systemRate', 200)
            
            # 移动端优化：适当降低语速
            if mobile_optimized:
                system_rate = int(system_rate * 0.95)
            
            # 2. 定义同步合成函数 (将在线程池中运行)
            def sync_generate_wav(input_text: str, voice_name: str, rate: int, req_index: int) -> bytes:
                """
                跨平台同步合成：
                - Windows/Linux: 使用 pyttsx3
                - macOS: 使用系统原生 'say' 命令 (避开 Cocoa 线程限制)
                """
                unique_suffix = uuid.uuid4().hex[:8]
                temp_file = f"temp_tts_{req_index}_{unique_suffix}.wav"
                # 假设 TOOL_TEMP_DIR 是你全局定义的临时目录，如果没有请改为 "." 或 os.getcwd()
                temp_filename = os.path.join(TOOL_TEMP_DIR, temp_file)
                
                wav_data = b""
                current_os = platform.system()

                try:
                    # -------------------------------------------------
                    # 分支 A: macOS 系统 (使用 subprocess 调用 say)
                    # -------------------------------------------------
                    if current_os == 'Darwin':
                        # --data-format=LEI16@22050 强制输出标准 WAV (16bit Little Endian, 22.05kHz)
                        cmd = ['say', '-o', temp_filename, '--data-format=LEI16@22050', input_text]
                        
                        if voice_name:
                            cmd.extend(['-v', voice_name])
                        
                        if rate:
                            # 简单传递语速，虽然 pyttsx3 和 say 的数值标准不同，但在合理范围内都可用
                            cmd.extend(['-r', str(rate)])

                        # 执行命令
                        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)

                    # -------------------------------------------------
                    # 分支 B: Windows / Linux (使用 pyttsx3)
                    # -------------------------------------------------
                    else:
                        import pyttsx3
                        # 在子线程内初始化，隔离环境
                        engine = pyttsx3.init()
                        engine.setProperty('rate', rate)
                        
                        if voice_name:
                            voices = engine.getProperty('voices')
                            for voice in voices:
                                # 模糊匹配名称或精确匹配ID
                                if voice_name.lower() in voice.name.lower() or voice_name == voice.id:
                                    engine.setProperty('voice', voice.id)
                                    break
                        
                        # save_to_file 是阻塞操作，在 Windows 上安全
                        engine.save_to_file(input_text, temp_filename)
                        engine.runAndWait()

                    # -------------------------------------------------
                    # 读取生成的音频
                    # -------------------------------------------------
                    if os.path.exists(temp_filename):
                        with open(temp_filename, 'rb') as f:
                            wav_data = f.read()
                    else:
                        raise Exception("TTS引擎未能生成音频文件")

                except subprocess.CalledProcessError as e:
                    print(f"[SystemTTS-Mac] 命令执行失败: {e.stderr.decode() if e.stderr else str(e)}")
                    raise Exception("macOS TTS 生成失败")
                except Exception as e:
                    print(f"[SystemTTS] 合成出错 ({current_os}): {str(e)}")
                    raise e
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_filename):
                        try:
                            os.remove(temp_filename)
                        except:
                            pass
                
                return wav_data

            # 3. 异步生成流程
            async def generate_audio():
                try:
                    # 将同步阻塞操作放入线程池
                    wav_content = await asyncio.to_thread(
                        sync_generate_wav, 
                        text, 
                        system_voice_name, 
                        system_rate, 
                        index
                    )
                    
                    if not wav_content:
                        raise HTTPException(status_code=500, detail="SystemTTS 生成内容为空")

                    # 格式转换逻辑 (WAV -> OPUS)
                    final_audio = wav_content
                    if target_format == "opus":
                        # 确保你有 convert_to_opus_simple 函数可用
                        final_audio = await convert_to_opus_simple(wav_content)
                    
                    # 分块返回 (模拟流式)
                    chunk_size = 4096
                    for i in range(0, len(final_audio), chunk_size):
                        yield final_audio[i:i + chunk_size]
                        await asyncio.sleep(0) # 让出控制权
                        
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"SystemTTS 处理失败: {str(e)}")

            # 4. 设置响应头
            if target_format == "opus":
                media_type = "audio/ogg"
                filename = f"tts_{index}.opus"
            else:
                media_type = "audio/wav"
                filename = f"tts_{index}.wav"
            
            return StreamingResponse(
                generate_audio(),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "X-Audio-Index": str(index),
                    "X-Audio-Format": target_format
                }
            )
        
        raise HTTPException(status_code=400, detail="不支持的TTS引擎")
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"服务器内部错误: {str(e)}"})

@app.get("/system/voices")
async def get_system_voices():
    """
    获取系统可用的 pyttsx3 音色列表。
    已针对 macOS 进行特殊过滤，去除特效音和不可用音色。
    """
    import pyttsx3

    def fetch_voices_sync():
        try:
            # 1. 定义 macOS 特有的怪诞音色黑名单 (Novelty Voices)
            # 这些音色通常是用来唱哥、发怪声的，不适合阅读文本
            mac_novelty_voices = {
                'Albert', 'Bad News', 'Bahh', 'Bells', 'Boing', 'Bubbles', 'Cellos',
                'Deranged', 'Good News', 'Hysterical', 'Pipe Organ', 'Trinoids', 
                'Whisper', 'Zarvox', 'Organ'
            }

            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            voice_list = []
            for v in voices:
                voice_name = v.name
                voice_id = v.id

                # -----------------------------
                # macOS 专属过滤逻辑
                # -----------------------------
                if sys.platform == 'darwin':
                    # 过滤策略 A: 排除黑名单中的特效音
                    if voice_name in mac_novelty_voices:
                        continue
                    
                    # 过滤策略 B: 排除 ID 中包含 'siri' 的音色
                    # 原因：pyttsx3 基于旧版 NSSpeechSynthesizer，通常无法驱动 Siri 在线/神经音色，
                    # 强行调用会导致静音或报错。建议只保留本地离线音色。
                    if 'siri' in voice_id.lower():
                        continue
                        
                    # 过滤策略 C (可选): 某些无效音色可能没有语言属性
                    if not v.languages:
                        continue

                # -----------------------------
                # 通用：修复语言解析 (重点修复 Mac 返回 bytes 的问题)
                # -----------------------------
                lang = "Unknown"
                if hasattr(v, 'languages') and v.languages:
                    raw_lang = v.languages[0] if isinstance(v.languages, list) else v.languages
                    
                    # 处理 Mac 上可能返回 bytes 的情况 (如 b'\x05en_US')
                    if isinstance(raw_lang, bytes):
                        try:
                            # 尝试解码，通常是 utf-8 或 mac-roman，这里简单处理转字符串
                            lang = raw_lang.decode('utf-8', errors='ignore')
                            # 移除可能存在的控制字符
                            lang = ''.join([c for c in lang if c.isprintable()])
                        except:
                            lang = str(raw_lang)
                    else:
                        lang = str(raw_lang)

                voice_list.append({
                    "id": voice_id,
                    "name": voice_name,
                    "lang": lang,
                    "gender": getattr(v, 'gender', 'Unknown')
                })
            
            return voice_list
            
        except ImportError:
            print("错误: 未找到 pyttsx3 驱动")
            return []
        except Exception as e:
            print(f"获取系统音色错误: {str(e)}")
            return []

    try:
        available_voices = await asyncio.to_thread(fetch_voices_sync)
        return {
            "count": len(available_voices),
            "voices": available_voices
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
async def convert_to_opus_simple(audio_data):
    """使用pydub将音频转换为opus格式（适合飞书）"""
    from pydub import AudioSegment
    from imageio_ffmpeg import get_ffmpeg_exe   # ① 关键：拿到捆绑的 ffmpeg
    # 设置 converter (利用 getattr 避免重复设置)
    if not getattr(AudioSegment, 'converter_configured', False):
        AudioSegment.converter = get_ffmpeg_exe()
        AudioSegment.converter_configured = True
    try:

        try:
            # ② 先尝试用 pydub 自动探测格式
            audio_io = io.BytesIO(audio_data)
            audio = AudioSegment.from_file(audio_io)          # 会自动调用捆绑的 ffmpeg
        except Exception as e:
            logging.warning(f"pydub 自动探测失败({e})，降级为 WAV 假设")
            audio_io = io.BytesIO(audio_data)
            audio = AudioSegment.from_wav(audio_io)           # 纯 WAV 场景

        # ③ 统一成飞书推荐参数
        audio = (audio
                .set_frame_rate(16000)
                .set_channels(1))

        # ④ 导出 opus
        out_io = io.BytesIO()
        audio.export(
            out_io,
            format="opus",
            codec="libopus",
            parameters=["-b:a", "64k",
                        "-application", "voip",
                        "-compression_level", "3"]
        )
        opus_data = out_io.getvalue()
        logging.info(f"Opus 转换完成：{len(audio_data)} B → {len(opus_data)} B")
        return opus_data

        
    except ImportError:
        logging.error("pydub未安装，无法转换为opus格式")
        return audio_data
    except Exception as e:
        logging.error(f"转换opus格式失败: {e}")
        return audio_data

# 添加状态存储
mcp_status = {}
@app.post("/create_mcp")
async def create_mcp_endpoint(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    mcp_id = data.get("mcpId")
    
    if not mcp_id:
        raise HTTPException(status_code=400, detail="Missing mcpId")
    
    # 将任务添加到后台队列
    background_tasks.add_task(process_mcp, mcp_id)
    
    return {"success": True, "message": "MCP服务器初始化已开始"}

@app.get("/mcp_status/{mcp_id}")
async def get_mcp_status(mcp_id: str):
    global mcp_client_list, mcp_status
    status = mcp_status.get(mcp_id, "not_found")
    if status == "ready":
        # 保证 _tools 里都是可序列化的 dict / list / 基本类型
        tools = await mcp_client_list[mcp_id].get_openai_functions(disable_tools=[])
        tools = json.dumps(mcp_client_list[mcp_id]._tools_list)
        return {"mcp_id": mcp_id, "status": status, "tools": tools}
    return {"mcp_id": mcp_id, "status": status, "tools": []}

async def process_mcp(mcp_id: str):
    """
    初始化单个 MCP 服务器，带失败回调同步，无需 sleep。
    """
    global mcp_client_list, mcp_status

    # 1. 同步原语：事件 + 失败原因
    init_done = asyncio.Event()
    fail_reason: str | None = None

    async def on_failure(error_message: str):
        nonlocal fail_reason
        # 仅第一次生效
        if fail_reason is not None:
            return
        fail_reason = error_message
        mcp_status[mcp_id] = f"failed: {error_message}"

        # 容错：只有客户端已创建才标记 disabled
        if mcp_id in mcp_client_list:
            mcp_client_list[mcp_id].disabled = True
            await mcp_client_list[mcp_id].close()
            print(f"关闭MCP服务器: {mcp_id}")

        init_done.set()          # 唤醒主协程

    # 2. 开始初始化
    mcp_status[mcp_id] = "initializing"
    try:
        cur_settings = await load_settings()
        server_config = cur_settings["mcpServers"][mcp_id]

        mcp_client_list[mcp_id] = McpClient()
        init_task = asyncio.create_task(
            mcp_client_list[mcp_id].initialize(
                mcp_id,
                server_config,
                on_failure_callback=on_failure
            )
        )
        # 2.1 先等初始化本身（最多 6 秒）
        await asyncio.wait_for(init_task, timeout=6)

        # 2.2 再等看 on_failure 会不会被触发（最多 5 秒）
        try:
            await asyncio.wait_for(init_done.wait(), timeout=5)
        except asyncio.TimeoutError:
            # 5 秒内没收到失败回调，认为成功
            pass

        # 3. 最终状态判定
        if fail_reason:
            # 回调里已经关过 client，这里只需保证状态一致
            mcp_client_list[mcp_id].disabled = True
            return
        tool = []
        retry = 0 
        while tool == [] and retry < 10:
            try:
                tool = await mcp_client_list[mcp_id].get_openai_functions(disable_tools=[])
            except Exception as e:
                print(f"获取工具失败: {str(e)}")
            finally:
                retry += 1
                await asyncio.sleep(0.5)
        mcp_status[mcp_id] = "ready"
        mcp_client_list[mcp_id].disabled = False

    except Exception as e:
        # 任何异常（超时、崩溃）都走这里
        mcp_status[mcp_id] = f"failed: {str(e)}"
        mcp_client_list[mcp_id].disabled = True
        await mcp_client_list[mcp_id].close()

    finally:
        # 如果任务还活着，保险起见取消掉
        if "init_task" in locals() and not init_task.done():
            init_task.cancel()
            try:
                await init_task
            except asyncio.CancelledError:
                pass

@app.delete("/remove_mcp")
async def remove_mcp_server(request: Request):
    global settings, mcp_client_list
    try:
        data = await request.json()
        server_name = data.get("serverName", "")

        if not server_name:
            raise HTTPException(status_code=400, detail="No server names provided")

        # 移除指定的MCP服务器
        current_settings = await load_settings()
        if server_name in current_settings['mcpServers']:
            del current_settings['mcpServers'][server_name]
            await save_settings(current_settings)
            settings = current_settings

            # 从mcp_client_list中移除
            if server_name in mcp_client_list:
                mcp_client_list[server_name].disabled = True
                await mcp_client_list[server_name].close()
                del mcp_client_list[server_name]
                print(f"关闭MCP服务器: {server_name}")

            return JSONResponse({"success": True, "removed": server_name})
        else:
            raise HTTPException(status_code=404, detail="Server not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"移除MCP服务器失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/remove_memory")
async def remove_memory_endpoint(request: Request):
    data = await request.json()
    memory_id = data.get("memoryId")
    if memory_id:
        try:
            # 删除MEMORY_CACHE_DIR目录下的memory_id文件夹
            memory_dir = os.path.join(MEMORY_CACHE_DIR, memory_id)
            shutil.rmtree(memory_dir)
            return JSONResponse({"success": True, "message": "Memory removed"})
        except Exception as e:
            return JSONResponse({"success": False, "message": str(e)})
    else:
        return JSONResponse({"success": False, "message": "No memoryId provided"})

@app.delete("/remove_agent")
async def remove_agent_endpoint(request: Request):
    data = await request.json()
    agent_id = data.get("agentId")
    if agent_id:
        try:
            # 删除AGENT_CACHE_DIR目录下的agent_id文件夹
            agent_dir = os.path.join(AGENT_DIR, f"{agent_id}.json")
            shutil.rmtree(agent_dir)
            return JSONResponse({"success": True, "message": "Agent removed"})
        except Exception as e:
            return JSONResponse({"success": False, "message": str(e)})
    else:
        return JSONResponse({"success": False, "message": "No agentId provided"})

@app.post("/a2a")
async def initialize_a2a(request: Request):
    from python_a2a import A2AClient
    data = await request.json()
    try:
        client = A2AClient(data['url'])
        agent_card = client.agent_card.to_json()
        agent_card = json.loads(agent_card)
        return JSONResponse({
            **agent_card,
            "status": "ready",
            "enabled": True
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/start_HA")
async def start_HA(request: Request):
    data = await request.json()
    API_TOKEN = data['data']['api_key']
    ha_config = {
        "type": "sse",
        "url": data['data']['url'].rstrip('/') + "/mcp_server/sse",
        "headers": {"Authorization": f"Bearer {API_TOKEN}"}
    }

    global HA_client
    if HA_client is not None:
        # 已初始化过
        return JSONResponse({"status": "ready", "enabled": True})

    # 用来通知“连接失败”的事件
    conn_failed_event = asyncio.Event()
    failure_reason = None

    async def on_failure(error_message: str):
        nonlocal failure_reason
        failure_reason = error_message
        conn_failed_event.set()

    try:
        HA_client = McpClient()
        await HA_client.initialize("HA", ha_config, on_failure_callback=on_failure)

        # 等一小段时间验证连接确实活了
        try:
            # 5 秒内如果事件被 set，说明连接失败
            await asyncio.wait_for(conn_failed_event.wait(), timeout=5.0)
            # 走到这里说明失败了
            raise RuntimeError(f"HA client connection failed: {failure_reason}")
        except asyncio.TimeoutError:
            # 2 秒无事发生，认为连接成功
            pass

        return JSONResponse({"status": "ready", "enabled": True})

    except Exception as e:
        HA_client = None
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.get("/stop_HA")
async def stop_HA():
    global HA_client
    try:
        if HA_client is not None:
            await HA_client.close()
            HA_client = None
            print(f"HA client stopped")
        return JSONResponse({
            "status": "stopped",
            "enabled": False
        })
    except Exception as e:
        HA_client = None
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/start_ChromeMCP")
async def start_ChromeMCP(request: Request):
    data = await request.json()
    Chrome_config = {
        "type": "stdio",
        "command": "npx",
        "args": ["@browsermcp/mcp@latest"]
    }

    global ChromeMCP_client
    if ChromeMCP_client is not None:
        # 已初始化过
        return JSONResponse({"status": "ready", "enabled": True})

    # 用来通知“连接失败”的事件
    conn_failed_event = asyncio.Event()
    failure_reason = None

    async def on_failure(error_message: str):
        nonlocal failure_reason
        failure_reason = error_message
        conn_failed_event.set()

    try:
        ChromeMCP_client = McpClient()
        await ChromeMCP_client.initialize("ChromeMCP", Chrome_config, on_failure_callback=on_failure)

        # 等一小段时间验证连接确实活了
        try:
            # 5 秒内如果事件被 set，说明连接失败
            await asyncio.wait_for(conn_failed_event.wait(), timeout=5.0)
            # 走到这里说明失败了
            raise RuntimeError(f"ChromeMCP client connection failed: {failure_reason}")
        except asyncio.TimeoutError:
            # 2 秒无事发生，认为连接成功
            pass

        return JSONResponse({"status": "ready", "enabled": True})
    except Exception as e:
        ChromeMCP_client = None
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/stop_ChromeMCP")
async def stop_ChromeMCP():
    global ChromeMCP_client
    try:
        if ChromeMCP_client is not None:
            await ChromeMCP_client.close()
            ChromeMCP_client = None
            print(f"ChromeMCP client stopped")
        return JSONResponse({
            "status": "stopped",
            "enabled": False
        })
    except Exception as e:
        ChromeMCP_client = None
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/start_sql")
async def start_sql(request: Request):
    data = await request.json()
    sql_args = []
    user = str(data['data'].get('user', '')).strip()
    password = str(data['data'].get('password', '')).strip()
    host = str(data['data'].get('host', '')).strip()
    port = str(data['data'].get('port', '')).strip()
    dbname = str(data['data'].get('dbname', '')).strip()
    dbpath = str(data['data'].get('dbpath', '')).strip()
    sql_url = ""
    if (data['data']['engine']=='sqlite'):
        sql_args = ["--from", "mcp-alchemy==2025.8.15.91819",
               "--refresh-package", "mcp-alchemy", "mcp-alchemy"]
        sql_url = f"sqlite:///{dbpath}"
        print(sql_url)
    elif (data['data']['engine']=='mysql'):
        sql_args = ["--from", "mcp-alchemy==2025.8.15.91819", "--with", "pymysql",
               "--refresh-package", "mcp-alchemy", "mcp-alchemy"]
        sql_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
    elif (data['data']['engine']=='postgres'):
        sql_args = ["--from", "mcp-alchemy==2025.8.15.91819", "--with", "psycopg2-binary",
               "--refresh-package", "mcp-alchemy", "mcp-alchemy"]
        sql_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    elif (data['data']['engine']=='mssql'):
        sql_args = ["--from", "mcp-alchemy==2025.8.15.91819", "--with", "pymssql",
               "--refresh-package", "mcp-alchemy", "mcp-alchemy"]
        sql_url = f"mssql+pymssql://{user}:{password}@{host}:{port}/{dbname}"
    elif (data['data']['engine']=='oracle'):
        sql_args = ["--from", "mcp-alchemy==2025.8.15.91819", "--with", "oracledb",
               "--refresh-package", "mcp-alchemy", "mcp-alchemy"]
        sql_url = f"oracle+oracledb://{user}:{password}@{host}:{port}/{dbname}"

    sql_config = {
        "type": "stdio",
        "command": "uvx",
        "args": sql_args,
        "env": {
            "DB_URL": sql_url.strip(),
        }
    }

    global sql_client
    if sql_client is not None:
        # 已初始化过
        return JSONResponse({"status": "ready", "enabled": True})

    # 用来通知“连接失败”的事件
    conn_failed_event = asyncio.Event()
    failure_reason = None

    async def on_failure(error_message: str):
        nonlocal failure_reason
        failure_reason = error_message
        conn_failed_event.set()

    try:
        sql_client = McpClient()
        await sql_client.initialize("sqlMCP", sql_config, on_failure_callback=on_failure)

        # 等一小段时间验证连接确实活了
        try:
            # 5 秒内如果事件被 set，说明连接失败
            await asyncio.wait_for(conn_failed_event.wait(), timeout=5.0)
            # 走到这里说明失败了
            raise RuntimeError(f"sqlMCP client connection failed: {failure_reason}")
        except asyncio.TimeoutError:
            # 2 秒无事发生，认为连接成功
            pass

        return JSONResponse({"status": "ready", "enabled": True})
    except Exception as e:
        sql_client = None
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/stop_sql")
async def stop_sql():
    global sql_client
    try:
        if sql_client is not None:
            await sql_client.close()
            sql_client = None
            print(f"sqlMCP client stopped")
        return JSONResponse({
            "status": "stopped",
            "enabled": False
        })
    except Exception as e:
        sql_client = None
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# 在现有路由之后添加health路由
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/load_file")
async def load_file_endpoint(request: Request, files: List[UploadFile] = File(None)):
    fastapi_base_url = str(request.base_url)
    logger.info(f"Received request with content type: {request.headers.get('Content-Type')}")
    file_links = []
    textFiles = []
    imageFiles = []
    content_type = request.headers.get('Content-Type', '')
    try:
        if 'multipart/form-data' in content_type:
            # 处理浏览器上传的文件
            if not files:
                raise HTTPException(status_code=400, detail="No files provided")
            
            for file in files:
                file_extension = os.path.splitext(file.filename)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                destination = os.path.join(UPLOAD_FILES_DIR, unique_filename)
                
                # 保存上传的文件
                with open(destination, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                file_link = {
                    "path": f"{fastapi_base_url}uploaded_files/{unique_filename}",
                    "name": file.filename
                }
                file_links.append(file_link)
                file_meta = {
                    "unique_filename": unique_filename,
                    "original_filename": file.filename,
                }
                # file_extension移除点号
                file_extension = file_extension[1:]
                if file_extension in ALLOWED_EXTENSIONS:
                    textFiles.append(file_meta)
                elif file_extension in ALLOWED_IMAGE_EXTENSIONS:
                    imageFiles.append(file_meta)
        elif 'application/json' in content_type:
            # 处理Electron发送的JSON文件路径
            data = await request.json()
            logger.info(f"Processing JSON data: {data}")
            
            for file_info in data.get("files", []):
                file_path = file_info.get("path")
                file_name = file_info.get("name", os.path.basename(file_path))
                
                if not os.path.isfile(file_path):
                    logger.error(f"File not found: {file_path}")
                    continue
                
                # 生成唯一文件名
                file_extension = os.path.splitext(file_name)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                destination = os.path.join(UPLOAD_FILES_DIR, unique_filename)
                
                # 复制文件到上传目录
                with open(file_path, "rb") as src, open(destination, "wb") as dst:
                    dst.write(src.read())
                
                file_link = {
                    "path": f"{fastapi_base_url}uploaded_files/{unique_filename}",
                    "name": file_name
                }
                file_links.append(file_link)
                file_meta = {
                    "unique_filename": unique_filename,
                    "original_filename": file_name,
                }
                # file_extension移除点号
                file_extension = file_extension[1:]
                if file_extension in ALLOWED_EXTENSIONS:
                    textFiles.append(file_meta)
                elif file_extension in ALLOWED_IMAGE_EXTENSIONS:
                    imageFiles.append(file_meta)
        else:
            raise HTTPException(status_code=400, detail="Unsupported Content-Type")
        return JSONResponse(content={"success": True, "fileLinks": file_links , "textFiles": textFiles, "imageFiles": imageFiles})
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete_file")
async def delete_file_endpoint(request: Request):
    data = await request.json()
    file_name = data.get("fileName")
    file_path = os.path.join(UPLOAD_FILES_DIR, file_name)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return JSONResponse(content={"success": True})
        else:
            return JSONResponse(content={"success": False, "message": "File not found"})
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)})

class FileNames(BaseModel):
    fileNames: List[str]

@app.delete("/delete_files")
async def delete_files_endpoint(req: FileNames):
    success_files = []
    errors = []
    for name in req.fileNames:
        path = os.path.join(UPLOAD_FILES_DIR, name)
        try:
            if os.path.exists(path):
                os.remove(path)
                success_files.append(name)
            else:
                errors.append(f"{name} not found")
        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    return JSONResponse(content={
        "success": len(success_files) > 0,   # 只要有成功就算成功
        "successFiles": success_files,
        "errors": errors
    })

ALLOWED_AUDIO_EXTENSIONS = ['wav', 'mp3', 'ogg', 'flac', 'aac']

@app.post("/upload_gsv_ref_audio")
async def upload_gsv_ref_audio(
    request: Request,
    file: UploadFile = File(...),
):
    fastapi_base_url = str(request.base_url)
    
    # 检查文件扩展名
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ALLOWED_AUDIO_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"不支持的文件类型: {file_extension}"}
        )
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    destination = os.path.join(UPLOAD_FILES_DIR, unique_filename)
    
    try:
        # 保存文件
        with open(destination, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 构建响应
        file_link = f"{fastapi_base_url}uploaded_files/{unique_filename}"
        
        return JSONResponse(content={
            "success": True,
            "message": "参考音频上传成功",
            "file": {
                "path": file_link,
                "name": file.filename,
                "unique_filename": unique_filename
            }
        })
    
    except Exception as e:
        logger.error(f"参考音频上传失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"文件保存失败: {str(e)}"}
        )

@app.delete("/delete_audio/{filename}")
async def delete_audio(filename: str):
    try:
        file_path = os.path.join(UPLOAD_FILES_DIR, filename)
        
        # 安全检查：确保文件名是UUID格式，防止路径遍历攻击
        if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.\w+$", filename):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid filename"}
            )
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return JSONResponse(content={
                "success": True,
                "message": "音频文件已删除"
            })
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "文件不存在"}
            )
            
    except Exception as e:
        logger.error(f"删除音频失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"删除失败: {str(e)}"}
        )

# 允许的VRM文件扩展名
ALLOWED_VRM_EXTENSIONS = {'vrm'}

@app.post("/upload_vrm_model")
async def upload_vrm_model(
    request: Request,
    file: UploadFile = File(...),
    display_name: str = Form(...)
):
    fastapi_base_url = str(request.base_url)
    
    # 检查文件扩展名
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ALLOWED_VRM_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"不支持的文件类型: {file_extension}，只支持.vrm文件"}
        )
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    destination = os.path.join(UPLOAD_FILES_DIR, unique_filename)
    
    try:
        # 保存文件
        with open(destination, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 构建响应
        file_link = f"{fastapi_base_url}uploaded_files/{unique_filename}"
        
        return JSONResponse(content={
            "success": True,
            "message": "VRM模型上传成功",
            "file": {
                "path": file_link,
                "display_name": display_name,
                "original_name": file.filename,
                "unique_filename": unique_filename
            }
        })
    
    except Exception as e:
        logger.error(f"VRM模型上传失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"文件保存失败: {str(e)}"}
        )

@app.get("/get_default_vrm_models")
async def get_default_vrm_models(request: Request):
    try:
        fastapi_base_url = str(request.base_url)
        models = []
        
        # 确保目录存在
        if not os.path.exists(DEFAULT_VRM_DIR):
            os.makedirs(DEFAULT_VRM_DIR, exist_ok=True)
            return JSONResponse(content={
                "success": True,
                "models": []
            })
        
        # 扫描默认VRM目录中的所有.vrm文件
        vrm_files = glob.glob(os.path.join(DEFAULT_VRM_DIR, "*.vrm"))
        
        for vrm_file in vrm_files:
            file_name = os.path.basename(vrm_file)
            # 使用文件名（不含扩展名）作为显示名称
            display_name = os.path.splitext(file_name)[0]
            
            # 构建文件访问URL
            file_url = f"{fastapi_base_url}vrm/{file_name}"
            
            models.append({
                "id": os.path.splitext(file_name)[0].lower(),  # 使用文件名作为ID
                "name": display_name,
                "path": file_url,
                "type": "default"
            })
        
        # 按名称排序
        models.sort(key=lambda x: x['name'])
        print("models:",models)
        return JSONResponse(content={
            "success": True,
            "models": models
        })
        
    except Exception as e:
        logger.error(f"获取默认VRM模型失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"获取默认模型失败: {str(e)}"}
        )

# 修改删除VRM模型的接口，添加安全检查
@app.delete("/delete_vrm_model/{filename}")
async def delete_vrm_model(filename: str):
    try:
        # 确保只能删除上传目录中的文件，不能删除默认模型
        file_path = os.path.join(UPLOAD_FILES_DIR, filename)
        
        # 安全检查：确保文件名是UUID格式，防止路径遍历攻击
        if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.vrm$", filename):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid filename"}
            )
        
        # 额外检查：确保文件路径在上传目录中，防止删除默认模型
        if not file_path.startswith(os.path.abspath(UPLOAD_FILES_DIR)):
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Cannot delete default models"}
            )
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return JSONResponse(content={
                "success": True,
                "message": "VRM模型文件已删除"
            })
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "文件不存在"}
            )
            
    except Exception as e:
        logger.error(f"删除VRM模型失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"删除失败: {str(e)}"}
        )

ALLOWED_VRMA_EXTENSIONS = {"vrma"}

animation_dir = os.path.join(DEFAULT_VRM_DIR, "animations")

def make_file_url(request: Request, file_path: str) -> str:
    """将本地文件路径转成对外可访问的 URL"""
    return str(request.base_url) + file_path.lstrip("/")


def scan_motion_files(directory: str, allowed_ext: set) -> List[dict]:
    """
    扫描指定目录下所有符合扩展名的文件，返回列表：
    [
      {
        "id": "文件名(不含扩展名)",
        "name": "文件名(不含扩展名)",
        "path": "对外可访问的完整 URL",
        "type": "default" | "user"
      }
    ]
    """
    files = []
    if not os.path.exists(directory):
        return files

    for f in os.listdir(directory):
        if f.lower().endswith(tuple(allowed_ext)):
            file_id = Path(f).stem
            file_path = os.path.join(directory, f)
            # 注意：这里统一返回相对路径，后面再组装成 URL
            files.append({
                "id": file_id,
                "name": file_id,
                "path": file_path,
                "type": "default" if directory == animation_dir else "user"
            })
    # 按文件名排序
    files.sort(key=lambda x: x["name"])
    return files

@app.get("/get_default_vrma_motions")
async def get_default_vrma_motions(request: Request):
    try:
        motions = scan_motion_files(animation_dir, ALLOWED_VRMA_EXTENSIONS)

        # 把磁盘路径转成 URL
        for m in motions:
            file_name = os.path.basename(m["path"])
            m["path"] = str(request.base_url) + f"vrm/animations/{file_name}"

        return {"success": True, "motions": motions}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"获取默认动作失败: {str(e)}"}
        )


@app.get("/get_user_vrma_motions")
async def get_user_vrma_motions(request: Request):
    try:
        motions = scan_motion_files(UPLOAD_FILES_DIR, ALLOWED_VRMA_EXTENSIONS)

        # 把磁盘路径转成 URL
        for m in motions:
            file_name = os.path.basename(m["path"])
            m["path"] = str(request.base_url) + f"uploaded_files/{file_name}"

        return {"success": True, "motions": motions}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"获取用户动作失败: {str(e)}"}
        )


@app.post("/upload_vrma_motion")
async def upload_vrma_motion(
    request: Request,
    file: UploadFile = File(...),
    display_name: str = Form(...)
):
    # 检查扩展名
    file_extension = Path(file.filename).suffix.lower().lstrip(".")
    if file_extension not in ALLOWED_VRMA_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"不支持的文件类型: {file_extension}"}
        )

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}.vrma"
    destination = os.path.join(UPLOAD_FILES_DIR, unique_filename)

    try:
        # 保存文件
        os.makedirs(UPLOAD_FILES_DIR, exist_ok=True)
        with open(destination, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 构建返回数据
        file_url = make_file_url(request, f"uploaded_files/{unique_filename}")

        return JSONResponse(content={
            "success": True,
            "message": "动作上传成功",
            "file": {
                "unique_filename": unique_filename,
                "display_name": display_name,
                "path": file_url
            }
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"保存文件失败: {str(e)}"}
        )


@app.delete("/delete_vrma_motion/{filename}")
async def delete_vrma_motion(filename: str):
    try:
        # 只允许删除 UPLOAD_FILES_DIR 中的文件
        if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.vrma$", filename):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid filename"}
            )

        file_path = os.path.join(UPLOAD_FILES_DIR, filename)
        abs_upload = os.path.abspath(UPLOAD_FILES_DIR)
        abs_file = os.path.abspath(file_path)

        if not abs_file.startswith(abs_upload):
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "禁止删除系统文件"}
            )

        if os.path.exists(file_path):
            os.remove(file_path)
            return {"success": True, "message": "动作文件已删除"}
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "文件不存在"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"删除失败: {str(e)}"}
        )

# -------------- GAUSS 场景相关 --------------
GAUSS_DIR     = os.path.join(DEFAULT_VRM_DIR, "scene")       # 默认场景目录
ALLOWED_GAUSS = {"ply", "spz", "splat", "ksplat", "sog"}     # spark 支持的扩展名

@app.post("/upload_gauss_scene")
async def upload_gauss_scene(
    request: Request,
    file: UploadFile = File(...),
    display_name: str = Form(...)
):
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_GAUSS:
        return JSONResponse(status_code=400, content={
            "success": False,
            "message": f"不支持的文件类型: {ext}"
        })
    unique = f"{uuid.uuid4()}.{ext}"
    destination = os.path.join(UPLOAD_FILES_DIR, unique)
    try:
        os.makedirs(UPLOAD_FILES_DIR, exist_ok=True)
        with open(destination, "wb") as f:
            f.write(await file.read())
        url = str(request.base_url) + f"uploaded_files/{unique}"
        return JSONResponse(content={
            "success": True,
            "file": {
                "unique_filename": unique,
                "display_name": display_name,
                "path": url
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.get("/get_default_gauss_scenes")
async def get_default_gauss_scenes(request: Request):
    try:
        os.makedirs(GAUSS_DIR, exist_ok=True)
        scenes = []
        for f in os.listdir(GAUSS_DIR):
            ext = Path(f).suffix.lower().lstrip(".")
            if ext in ALLOWED_GAUSS:
                scenes.append({
                    "id":   Path(f).stem,
                    "name": Path(f).stem,
                    "path": str(request.base_url) + f"vrm/scene/{f}",
                    "type": "default"
                })
        scenes.sort(key=lambda x: x["name"])
        return {"success": True, "scenes": scenes}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.get("/get_user_gauss_scenes")
async def get_user_gauss_scenes(request: Request):
    try:
        scenes = []
        for f in os.listdir(UPLOAD_FILES_DIR):
            ext = Path(f).suffix.lower().lstrip(".")
            if ext in ALLOWED_GAUSS:
                scenes.append({
                    "id":   Path(f).stem,
                    "name": Path(f).stem,
                    "path": str(request.base_url) + f"uploaded_files/{f}",
                    "type": "user"
                })
        scenes.sort(key=lambda x: x["name"])
        return {"success": True, "scenes": scenes}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.delete("/delete_gauss_scene/{filename}")
async def delete_gauss_scene(filename: str):
    if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(ply|spz|splat|ksplat|sog)$", filename):
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid filename"})
    file_path = os.path.join(UPLOAD_FILES_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"success": True, "message": "场景已删除"}
    return JSONResponse(status_code=404, content={"success": False, "message": "文件不存在"})


@app.get("/update_storage")
async def update_storage_endpoint(request: Request):
    settings = await load_settings()
    textFiles = settings.get("textFiles") or []
    imageFiles = settings.get("imageFiles") or []
    videoFiles = settings.get("videoFiles") or []
    # 检查UPLOAD_FILES_DIR目录中的文件，根据ALLOWED_EXTENSIONS、ALLOWED_IMAGE_EXTENSIONS、ALLOWED_VIDEO_EXTENSIONS分类，如果不存在于textFiles、imageFiles、videoFiles中则添加进去
    # 三个列表的元素是字典，包含"unique_filename"和"original_filename"两个键
    
    for file in os.listdir(UPLOAD_FILES_DIR):
        file_path = os.path.join(UPLOAD_FILES_DIR, file)
        if os.path.isfile(file_path):
            file_extension = os.path.splitext(file)[1][1:]
            if file_extension in ALLOWED_EXTENSIONS:
                if file not in [item["unique_filename"] for item in textFiles]:
                    textFiles.append({"unique_filename": file, "original_filename": file})
            elif file_extension in ALLOWED_IMAGE_EXTENSIONS:
                if file not in [item["unique_filename"] for item in imageFiles]:
                    imageFiles.append({"unique_filename": file, "original_filename": file})
            elif file_extension in ALLOWED_VIDEO_EXTENSIONS:
                if file not in [item["unique_filename"] for item in videoFiles]:
                    videoFiles.append({"unique_filename": file, "original_filename": file})

    # 发给前端
    return JSONResponse(content={"textFiles": textFiles, "imageFiles": imageFiles, "videoFiles": videoFiles})

@app.get("/get_file_content")
async def get_file_content_endpoint(file_url: str):
    file_path = os.path.join(UPLOAD_FILES_DIR, file_url)
    content = await get_file_content(file_path)
    return JSONResponse(content={"content": content})

@app.post("/create_kb")
async def create_kb_endpoint(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    kb_id = data.get("kbId")
    
    if not kb_id:
        raise HTTPException(status_code=400, detail="Missing kbId")
    
    # 将任务添加到后台队列
    background_tasks.add_task(process_kb, kb_id)
    
    return {"success": True, "message": "知识库处理已开始，请稍后查询状态"}

@app.delete("/remove_kb")
async def remove_kb_endpoint(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    kb_id = data.get("kbId")

    if not kb_id:
        raise HTTPException(status_code=400, detail="Missing kbId")
    try:
        background_tasks.add_task(remove_kb, kb_id)
    except Exception as e:
        return {"success": False, "message": str(e)}
    return {"success": True, "message": "知识库已删除"}

# 删除知识库
async def remove_kb(kb_id):
    # 删除KB_DIR/kb_id目录
    kb_dir = os.path.join(KB_DIR, str(kb_id))
    if os.path.exists(kb_dir):
        shutil.rmtree(kb_dir)
    else:
        print(f"KB directory {kb_dir} does not exist.")
    return

# 添加状态存储
kb_status = {}
@app.get("/kb_status/{kb_id}")
async def get_kb_status(kb_id):
    status = kb_status.get(kb_id, "not_found")
    print (f"kb_status: {kb_id} - {status}")
    return {"kb_id": kb_id, "status": status}

# 修改 process_kb
async def process_kb(kb_id):
    kb_status[kb_id] = "processing"
    try:
        from py.know_base import process_knowledge_base
        await process_knowledge_base(kb_id)
        kb_status[kb_id] = "completed"
    except Exception as e:
        kb_status[kb_id] = f"failed: {str(e)}"

@app.post("/create_sticker_pack")
async def create_sticker_pack(
    request: Request,
    files: List[UploadFile] = File(..., description="表情文件列表"),
    pack_name: str = Form(..., description="表情包名称"),
    descriptions: List[str] = Form(..., description="表情描述列表")
):
    """
    创建新表情包
    - files: 上传的图片文件列表
    - pack_name: 表情包名称
    - descriptions: 每个表情的描述列表
    """
    fastapi_base_url = str(request.base_url)
    imageFiles = []
    stickers_data = []
    
    try:
        # 验证输入数据
        if not pack_name:
            raise HTTPException(status_code=400, detail="表情包名称不能为空")
        if len(files) == 0:
            raise HTTPException(status_code=400, detail="至少需要上传一个表情")
        if len(descriptions) != len(files):
            raise HTTPException(
                status_code=400, 
                detail=f"描述数量({len(descriptions)})与文件数量({len(files)})不匹配"
            )

        # 处理上传的表情文件
        for idx, file in enumerate(files):
            # 获取文件扩展名
            file_extension = os.path.splitext(file.filename)[1].lower()
            
            # 验证文件类型
            if file_extension not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的文件类型: {file_extension}"
                )
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            destination = os.path.join(UPLOAD_FILES_DIR, unique_filename)

            # 保存文件
            with open(destination, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # 构建返回数据
            imageFiles.append({
                "unique_filename": unique_filename,
                "original_filename": file.filename,
            })
            
            # 获取对应的描述（处理可能的索引越界）
            description = descriptions[idx] if idx < len(descriptions) else ""

            # 构建表情数据
            stickers_data.append({
                "unique_filename": unique_filename,
                "original_filename": file.filename,
                "url": f"{fastapi_base_url}uploaded_files/{unique_filename}",
                "description": description
            })

        # 创建表情包ID（可替换为数据库存储逻辑）
        sticker_pack_id = str(uuid.uuid4())
        
        return JSONResponse(content={
            "success": True,
            "id": sticker_pack_id,
            "name": pack_name,
            "stickers": stickers_data,
            "imageFiles": imageFiles,
            "cover": stickers_data[0]["url"] if stickers_data else None
        })
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"创建表情包时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

from py.qq_bot_manager import QQBotConfig, QQBotManager
# 全局机器人管理器
qq_bot_manager = QQBotManager()

@app.post("/start_qq_bot")
async def start_qq_bot(config: QQBotConfig):
    try:
        qq_bot_manager.start_bot(config)
        return {
            "success": True,
            "message": "QQ机器人已成功启动",
            "environment": "thread-based"
        }
    except Exception as e:
        logger.error(f"启动QQ机器人失败: {e}")
        return JSONResponse(
            status_code=400,  # 改为 400 表示客户端错误
            content={
                "success": False, 
                "message": f"启动失败: {str(e)}",
                "error_type": "startup_error"
            }
        )

@app.post("/stop_qq_bot")
async def stop_qq_bot():
    try:
        qq_bot_manager.stop_bot()
        return {"success": True, "message": "QQ机器人已停止"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.get("/qq_bot_status")
async def qq_bot_status():
    status = qq_bot_manager.get_status()
    # 如果有启动错误，在状态中包含错误信息
    if status.get("startup_error") and not status.get("is_running"):
        status["error_message"] = f"启动失败: {status['startup_error']}"
    return status

@app.post("/reload_qq_bot")
async def reload_qq_bot(config: QQBotConfig):
    try:
        # 先停止再启动
        qq_bot_manager.stop_bot()
        await asyncio.sleep(1)  # 等待完全停止
        qq_bot_manager.start_bot(config)
        
        return {
            "success": True,
            "message": "QQ机器人已重新加载",
            "config_changed": True
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

# 入口文件部分代码

from py.feishu_bot_manager import FeishuBotConfig, FeishuBotManager

# 全局飞书机器人管理器
feishu_bot_manager = FeishuBotManager()

@app.post("/start_feishu_bot")
async def start_feishu_bot(config: FeishuBotConfig):
    try:
        feishu_bot_manager.start_bot(config)
        return {
            "success": True,
            "message": "飞书机器人已成功启动",
            "environment": "thread-based"
        }
    except Exception as e:
        logger.error(f"启动飞书机器人失败: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False, 
                "message": f"启动失败: {str(e)}",
                "error_type": "startup_error"
            }
        )

@app.post("/stop_feishu_bot")
async def stop_feishu_bot():
    try:
        feishu_bot_manager.stop_bot()
        return {"success": True, "message": "飞书机器人已停止"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.get("/feishu_bot_status")
async def feishu_bot_status():
    status = feishu_bot_manager.get_status()
    # 如果有启动错误，在状态中包含错误信息
    if status.get("startup_error") and not status.get("is_running"):
        status["error_message"] = f"启动失败: {status['startup_error']}"
    return status

@app.post("/reload_feishu_bot")
async def reload_feishu_bot(config: FeishuBotConfig):
    try:
        # 先停止再启动
        feishu_bot_manager.stop_bot()
        await asyncio.sleep(1)  # 等待完全停止
        feishu_bot_manager.start_bot(config)
        
        return {
            "success": True,
            "message": "飞书机器人已重新加载",
            "config_changed": True
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )
    
from py.discord_bot_manager import DiscordBotManager, DiscordBotConfig

discord_bot_manager = DiscordBotManager()

@app.post("/start_discord_bot")
async def start_discord_bot(config: DiscordBotConfig):
    try:
        discord_bot_manager.start_bot(config)
        return {"success": True, "message": "Discord 机器人已启动"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})

@app.post("/stop_discord_bot")
async def stop_discord_bot():
    discord_bot_manager.stop_bot()
    return {"success": True, "message": "Discord 机器人已停止"}

@app.get("/discord_bot_status")
async def discord_bot_status():
    return discord_bot_manager.get_status()

@app.post("/reload_discord_bot")
async def reload_discord_bot(config: DiscordBotConfig):
    discord_bot_manager.stop_bot()
    await asyncio.sleep(1)
    discord_bot_manager.start_bot(config)
    return {"success": True, "message": "Discord 机器人已重载"}


from py.telegram_bot_manager import TelegramBotManager, TelegramBotConfig

# 全局 Telegram 机器人管理器
telegram_bot_manager = TelegramBotManager()

@app.post("/start_telegram_bot")
async def start_telegram_bot(config: TelegramBotConfig):
    """
    启动 Telegram 机器人（与飞书接口完全对称）
    """
    try:
        telegram_bot_manager.start_bot(config)
        return {
            "success": True,
            "message": "Telegram 机器人已成功启动",
            "environment": "thread-based"
        }
    except Exception as e:
        logger.error(f"启动 Telegram 机器人失败: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"启动失败: {str(e)}",
                "error_type": "startup_error"
            }
        )


@app.post("/stop_telegram_bot")
async def stop_telegram_bot():
    """
    停止 Telegram 机器人
    """
    try:
        telegram_bot_manager.stop_bot()
        return {"success": True, "message": "Telegram 机器人已停止"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@app.get("/telegram_bot_status")
async def telegram_bot_status():
    """
    获取 Telegram 机器人状态
    """
    status = telegram_bot_manager.get_status()
    if status.get("startup_error") and not status.get("is_running"):
        status["error_message"] = f"启动失败: {status['startup_error']}"
    return status


@app.post("/reload_telegram_bot")
async def reload_telegram_bot(config: TelegramBotConfig):
    """
    重新加载 Telegram 机器人（先停后启）
    """
    try:
        telegram_bot_manager.stop_bot()
        await asyncio.sleep(1)  # 等待完全停止
        telegram_bot_manager.start_bot(config)
        return {
            "success": True,
            "message": "Telegram 机器人已重新加载",
            "config_changed": True
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@app.post("/add_workflow")
async def add_workflow(file: UploadFile = File(...), workflow_data: str = Form(...)):
    # 检查文件类型是否为 JSON
    if file.content_type != "application/json":
        raise HTTPException(
            status_code=400,
            detail="Only JSON files are allowed."
        )

    # 生成唯一文件名，uuid.uuid4()，没有连词符
    unique_filename = str(uuid.uuid4()).replace('-', '')

    # 拼接文件路径
    file_path = os.path.join(UPLOAD_FILES_DIR, unique_filename + ".json")

    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

    # 解析 workflow_data
    workflow_data_dict = json.loads(workflow_data)

    # 返回文件信息
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "File uploaded successfully",
            "file": {
                "unique_filename": unique_filename,
                "original_filename": file.filename,
                "url": f"/uploaded_files/{unique_filename}",
                "enabled": True,
                "text_input": workflow_data_dict.get("textInput"),
                "text_input_2": workflow_data_dict.get("textInput2"),
                "image_input": workflow_data_dict.get("imageInput"),
                "image_input_2": workflow_data_dict.get("imageInput2"),
                "seed_input": workflow_data_dict.get("seedInput"),
                "seed_input2": workflow_data_dict.get("seedInput2"),
                "description": workflow_data_dict.get("description")
            }
        }
    )

@app.delete("/delete_workflow/{filename}")
async def delete_workflow(filename: str):
    file_path = os.path.join(UPLOAD_FILES_DIR, filename + ".json")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 删除文件
    try:
        os.remove(file_path)
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "File deleted successfully"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )

@app.get("/cur_language")
async def cur_language():
    settings = await load_settings()
    target_language = settings["currentLanguage"]
    return {"language": target_language}

@app.get("/vrm_config")
async def vrm_config():
    settings = await load_settings()
    return {"VRMConfig": settings.get("VRMConfig", {})}

from py.live_router import router as live_router, ws_router as live_ws_router

# 2. 分别挂载
app.include_router(live_router)     # /api/live/*
app.include_router(live_ws_router)  # /ws/live/*


# ---------- 工具 ----------
def get_dir(mid: str) -> str:
    return os.path.join(MEMORY_CACHE_DIR, mid)

def get_faiss_path(mid: str) -> str:
    return os.path.join(get_dir(mid), "agent-party.faiss")

def get_pkl_path(mid: str) -> str:
    return os.path.join(get_dir(mid), "agent-party.pkl")

def load_index_and_meta(mid: str):
    import faiss
    fpath, ppath = get_faiss_path(mid), get_pkl_path(mid)
    if not (os.path.exists(fpath) and os.path.exists(ppath)):
        raise HTTPException(status_code=404, detail="memory not found")
    index = faiss.read_index(fpath)
    with open(ppath, "rb") as f:
        raw = pickle.load(f)          # 可能是 tuple 也可能是 dict
    # 兼容旧数据：如果是 tuple 取第 0 个，否则直接用
    meta_dict = raw[0] if isinstance(raw, tuple) else raw
    return index, meta_dict

def save_index_and_meta(mid: str, index, meta: List[Dict[Any, Any]]):
    import faiss
    faiss.write_index(index, get_faiss_path(mid))
    with open(get_pkl_path(mid), "wb") as f:
        pickle.dump(meta, f)


def fmt_iso8605_to_local(iso: str) -> str:
    """
    ISO-8601 -> 服务器本地时区 yyyy-MM-dd HH:mm:ss
    """
    try:
        dt = datetime.fromisoformat(iso)      # 读入（可能带时区）
        dt = dt.astimezone()                  # 落到服务器当前时区
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso        # 解析失败就原样返回


def flatten_records(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    flat = []
    for uuid, rec in meta.items():
        flat.append({
            "idx"        : len(flat),
            "uuid"       : uuid,
            "text"       : rec["data"],
            "created_at" : fmt_iso8605_to_local(rec["created_at"]),
            "timetamp"   : rec["timetamp"],
        })
    return flat


# 新增： dict ↔ list 互转工具
def dict_to_list(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """有序化，保证顺序与 Faiss 索引一致"""
    return [{uuid: rec} for uuid, rec in meta.items()]

def list_to_dict(meta_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """列表再压回 dict"""
    new_meta = {}
    for item in meta_list:
        uuid, rec = next(iter(item.items()))
        new_meta[uuid] = rec
    return new_meta

# ---------- 模型 ----------
class TextUpdate(BaseModel):
    new_text: str

# ---------- 1. 读取（平铺） ----------
@app.get("/memory/{memory_id}")
async def read_memory(memory_id: str) -> List[Dict[str, Any]]:
    _, meta_dict = load_index_and_meta(memory_id)   # 拆包
    return flatten_records(meta_dict)               # 传字典

# ---------- 2. 修改（只改 data） ----------
@app.put("/memory/{memory_id}/{idx}")
async def update_text(
    memory_id: str,
    idx: int,
    body: TextUpdate = Body(...)
) -> dict:
    index, meta_dict = load_index_and_meta(memory_id)
    meta_list = dict_to_list(meta_dict)
    if not (0 <= idx < len(meta_list)):
        raise HTTPException(status_code=404, detail="index out of range")
    # 定位 → 改 data
    uuid, rec = next(iter(meta_list[idx].items()))
    rec["data"] = body.new_text
    # 写回
    save_index_and_meta(memory_id, index, list_to_dict(meta_list))
    return {"message": "updated", "idx": idx}


# ---------- 3. 删除（按行号） ----------
@app.delete("/memory/{memory_id}/{idx}")
async def delete_text(memory_id: str, idx: int) -> dict:
    import faiss
    import numpy as np
    index, meta_dict = load_index_and_meta(memory_id)
    meta_list = dict_to_list(meta_dict)
    if not (0 <= idx < len(meta_list)):
        raise HTTPException(status_code=404, detail="index out of range")

    ntotal = index.ntotal
    print("index.ntotal",index.ntotal)
    print("len(meta_list)",len(meta_list))
    if ntotal != len(meta_list):
        raise RuntimeError("index 与 meta 长度不一致")

    # 1. 重建 Faiss 索引（去掉 idx）
    ids_to_keep = np.array([i for i in range(ntotal) if i != idx], dtype=np.int64)
    vecs = np.vstack([index.reconstruct(i) for i in range(ntotal)])
    new_index = faiss.IndexFlatL2(index.d)   # 跟你建索引时保持一致
    if vecs.shape[0] - 1 > 0:
        new_index.add(vecs[ids_to_keep].astype("float32"))

    # 2. 删除列表元素
    del meta_list[idx]

    # 3. 落盘
    save_index_and_meta(memory_id, new_index, list_to_dict(meta_list))
    return {"message": "deleted", "idx": idx}

@app.get("/api/update_proxy")
async def update_proxy():
    try:
        settings = await load_settings()
        if settings:
            if settings["systemSettings"]["proxy"] and settings["systemSettings"]["proxyMode"] == "manual":
                # 设置代理环境变量
                os.environ['http_proxy'] = settings["systemSettings"]["proxy"].strip()
                os.environ['https_proxy'] = settings["systemSettings"]["proxy"].strip()
            elif settings["systemSettings"]["proxyMode"] == "system":
                os.environ.pop('http_proxy', None)
                os.environ.pop('https_proxy', None)
            else:
                os.environ['http_proxy'] = ""
                os.environ['https_proxy'] = ""
        return {"message": "Proxy updated successfully", "success": True}
    except Exception as e:
        return {"message": str(e), "success": False}

@app.get("/api/get_userfile")
async def get_userfile():
    try:
        userfile = USER_DATA_DIR
        return {"message": "Userfile loaded successfully", "userfile": userfile, "success": True}
    except Exception as e:
        return {"message": str(e), "success": False}

@app.get("/api/get_extfile")
async def get_extfile():
    try:
        extfile = EXT_DIR
        return {"message": "Extfile loaded successfully", "extfile": extfile, "success": True}
    except Exception as e:
        return {"message": str(e), "success": False}

def get_internal_ip():
    """获取本机内网 IP 地址"""
    try:
        # 创建一个 socket 连接，目标可以是任何公网地址（不真连接），只是用来获取出口 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))  # 使用 Google DNS，不实际发送数据
        internal_ip = s.getsockname()[0]
        s.close()
        return internal_ip
    except Exception:
        return "127.0.0.1"

@app.get("/api/ip")
def get_ip():
    ip = get_internal_ip()
    return {"ip": ip}


settings_lock = asyncio.Lock()
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    # [关键点 1] 为当前连接生成唯一ID
    connection_id = str(shortuuid.ShortUUID().random(length=8))
    # 标记该连接是否发送过提示词（用于判断断开时是否需要发送移除指令）
    has_sent_prompt = False

    try:
        async with settings_lock:
            current_settings = await load_settings()
            if current_settings.get("conversations", None):
                await save_covs({"conversations": current_settings["conversations"]})
                del current_settings["conversations"]
                await save_settings(current_settings)
            covs = await load_covs()
            current_settings["conversations"] = covs.get("conversations", [])
        
        await websocket.send_json({"type": "settings", "data": current_settings})
        
        while True:
            data = await websocket.receive_json()
            
            # --- 常规逻辑保持不变 ---
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "save_settings":
                await save_settings(data.get("data", {}))
                await websocket.send_json({
                    "type": "settings_saved",
                    "correlationId": data.get("correlationId"),
                    "success": True
                })
            elif data.get("type") == "save_conversations":
                await save_covs(data.get("data", {}))
                await websocket.send_json({
                    "type": "conversations_saved",
                    "correlationId": data.get("correlationId"),
                    "success": True
                })
            elif data.get("type") == "get_settings":
                settings = await load_settings()
                if settings.get("conversations", None):
                    await save_covs({"conversations": settings["conversations"]})
                    del settings["conversations"]
                    await save_settings(settings)
                covs = await load_covs()
                settings["conversations"] = covs.get("conversations", [])
                await websocket.send_json({"type": "settings", "data": settings})
            elif data.get("type") == "save_agent":
                current_settings = await load_settings()
                agent_id = str(shortuuid.ShortUUID().random(length=8))
                config_path = os.path.join(AGENT_DIR, f"{agent_id}.json")
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(current_settings, f, indent=4, ensure_ascii=False)
                current_settings['agents'][agent_id] = {
                    "id": agent_id,
                    "name": data['data']['name'],
                    "system_prompt": data['data']['system_prompt'],
                    "config_path": config_path,
                    "enabled": False,
                }
                await save_settings(current_settings)
                await websocket.send_json({"type": "settings", "data": current_settings})
            
            elif data.get("type") == "set_user_input":
                user_input = data.get("data", {}).get("text", "")
                for connection in active_connections:
                    await connection.send_json({
                        "type": "update_user_input",
                        "data": {"text": user_input}
                    })

            # --- [关键修改] 处理扩展页面发送的系统提示 ---
            elif data.get("type") == "set_system_prompt":
                has_sent_prompt = True # 标记该连接为扩展源
                extension_system_prompt = data.get("data", {}).get("text", "")
                
                # 广播时携带 connection_id
                for connection in active_connections:
                    await connection.send_json({
                        "type": "update_system_prompt",
                        "data": {
                            "id": connection_id,      # 这里传入连接ID
                            "text": extension_system_prompt
                        }
                    })

            elif data.get("type") == "set_tool_input":
                tool_input = data.get("data", {}).get("text", "")
                for connection in active_connections:
                    await connection.send_json({
                        "type": "update_tool_input",
                        "data": {"text": tool_input}
                    })

            elif data.get("type") == "trigger_close_extension":
                for connection in active_connections:
                    await connection.send_json({
                        "type": "trigger_close_extension",
                        "data": {}
                    })

            elif data.get("type") == "trigger_send_message":
                for connection in active_connections:
                    await connection.send_json({
                        "type": "trigger_send_message",
                        "data": {}
                    })
                    
            elif data.get("type") == "trigger_clear_message":
                for connection in active_connections:
                    await connection.send_json({
                        "type": "trigger_clear_message",
                        "data": {}
                    })

            elif data.get("type") == "get_messages":
                for connection in active_connections:
                    await connection.send_json({
                        "type": "request_messages",
                        "data": {}
                    })

            elif data.get("type") == "broadcast_messages":
                messages_data = data.get("data", {})
                for connection in [conn for conn in active_connections if conn != websocket]:
                    await connection.send_json({
                        "type": "messages_update",
                        "data": messages_data
                    })

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        
        # --- [关键修改] 连接断开时的处理 ---
        # 只有当该连接曾经发送过 update_system_prompt 时才触发
        # 避免普通客户端断开时误删内容
        if has_sent_prompt:
            print(f"Extension {connection_id} disconnected. Removing prompt.")
            for connection in active_connections:
                try:
                    # 发送移除指令，只携带 ID
                    await connection.send_json({
                        "type": "remove_system_prompt",
                        "data": {
                            "id": connection_id 
                        }
                    })
                except Exception:
                    pass

from py.uv_api import router as uv_router
app.include_router(uv_router)

from py.node_api import router as node_router 
app.include_router(node_router)

from py.git_api import router as git_router
app.include_router(git_router)

from py.extensions import router as extensions_router

app.include_router(extensions_router)

from py.sherpa_model_manager import router as sherpa_model_router
app.include_router(sherpa_model_router)

from py.ebd_model_manager import router as ebd_model_router
app.include_router(ebd_model_router)

from py.minilm_router import router as minilm_router
app.include_router(minilm_router)

from py.ebd_api import router as embedding_router
app.include_router(embedding_router)

mcp = FastApiMCP(
    app,
    name="Agent party MCP - chat with multiple agents",
    include_operations=["get_agents", "chat_with_agent_party"],
)

mcp.mount()

app.mount("/vrm", StaticFiles(directory=DEFAULT_VRM_DIR), name="vrm")
app.mount("/tool_temp", StaticFiles(directory=TOOL_TEMP_DIR), name="tool_temp")
app.mount("/uploaded_files", StaticFiles(directory=UPLOAD_FILES_DIR), name="uploaded_files")
app.mount("/ext", StaticFiles(directory=EXT_DIR), name="ext")
app.mount("/", StaticFiles(directory=os.path.join(base_path, "static"), html=True), name="static")

# 简化main函数
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=HOST,
        port=PORT
    )