"""
Lumina Memory Server - 模块化入口
重构自 memory_server.py，职责清晰分离
"""
import os
import sys
import json
import logging
import asyncio
import uvicorn
from typing import Dict, Optional
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 确保可以导入本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MemoryServer")

# ========== 全局状态 ==========
memory_clients: Dict = {}
dreaming_service = None
soul_client = None
heartbeat_service_instance = None
surreal_system = None
hippocampus_service_instance = None
config_timestamps: Dict = defaultdict(float)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global memory_clients, dreaming_service, heartbeat_service_instance, soul_client, surreal_system
    
    from model_manager import model_manager
    from soul_manager import SoulManager
    from heartbeat_service import HeartbeatService
    from surreal_memory import SurrealMemory
    from hippocampus import Hippocampus
    from graph_curator import GraphCurator
    
    # [Startup] 加载配置
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_config.json")
    if os.path.exists(config_path):
        try:
            logger.info(f"Loading saved config from {config_path}...")
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            character_id = config_data.get("character_id", "hiyori")
            
            # 检查角色是否存在
            char_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters", character_id)
            
            if not os.path.exists(char_dir):
                logger.warning(f"Configured character '{character_id}' not found. Scanning for others...")
                base_char_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")
                found_chars = [d for d in os.listdir(base_char_dir) if os.path.isdir(os.path.join(base_char_dir, d))]
                
                if found_chars:
                    if 'lillian' in found_chars: character_id = 'lillian'
                    elif 'hiyori' in found_chars: character_id = 'hiyori'
                    else: character_id = found_chars[0]
                    logger.info(f"Falling back to existing character: '{character_id}'")
                else:
                    logger.info(f"No characters found. Creating 'lumina_default'...")
                    character_id = "lumina_default"

            # Load Embedding Model Centralized
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "paraphrase-multilingual-MiniLM-L12-v2")
            try:
                # Ensure model exists (or download) - reusing logic from lite_memory used to have
                # For now, assume model_manager handles download if we call setup/download
                # But here we assume it's there or we load from path.
                # Actually, let's just attempt load.
                embedding_model = model_manager.load_embedding_model(model_path)
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                embedding_model = None

            # 初始化 Dreaming (Legacy) - Disabled
    
            dreaming_service = None # Disabling legacy dreaming service
            
            logger.info(f"Auto-initialized memory for '{character_id}' (Surreal Only)")
            
            # 初始化 SurrealDB
            try:
                surreal_system = SurrealMemory(url="ws://127.0.0.1:8000/rpc", user="root", password="root")
                await surreal_system.connect()
                
                # [Injection] Inject Global Encoder into SurrealMemory
                if embedding_model:
                     # Create a lambda or wrapper to match expected interface (encode(text)->list)
                    surreal_system.set_encoder(lambda text: embedding_model.encode(text).tolist())
                    
                logger.info("✅ SurrealMemory initialized (Parallel Backend)")
            except Exception as e:
                logger.warning(f"⚠️ SurrealMemory failed to initialize: {e}")
                surreal_system = None
            
            # 初始化 SoulManager
            should_create = (character_id == "lumina_default") 
            soul_client = SoulManager(character_id=character_id, auto_create=should_create)
            logger.info(f"SoulManager initialized for '{character_id}'")
            
        except Exception as e:
            logger.error(f"Failed to auto-load config: {e}")

    # 初始化 Hippocampus (海马体)
    try:
        if surreal_system and soul_client:
            # ⚡ Pass character_id for isolated memory digestion
            hippocampus_service_instance = Hippocampus(surreal_system, soul_client, character_id=character_id)
            logger.info(f"🧠 Hippocampus initialized for '{character_id}'")
            
            # 注入 Hippocampus 引用到 SurrealMemory，用于自动触发消化
            surreal_system.set_hippocampus(hippocampus_service_instance)
        else:
            logger.warning("⚠️ Hippocampus skipped (missing dependencies)")
    except Exception as e:
        logger.error(f"Failed to init Hippocampus: {e}")
    
    # 启动 Heartbeat
    try:
        logger.info("Starting Heartbeat Service...")
        if soul_client:
            # 初始化图谱维护者 (The Gardener) - Inject Hippocampus for LLM Arbitration
            graph_curator = GraphCurator(surreal_system, hippocampus_service_instance) if surreal_system else None
        
            # 传入 Hippocampus 和 GraphCurator 引用
            heartbeat_service_instance = HeartbeatService(
                soul_client, 
                hippocampus=hippocampus_service_instance,
                graph_curator=graph_curator, 
                main_loop=asyncio.get_running_loop()
            )
            heartbeat_service_instance.start()
    except Exception as e:
        logger.error(f"Failed to start Heartbeat: {e}")

    # 注入依赖到各路由模块
    _inject_all_dependencies()

    yield
    
    # [Shutdown] 清理
    logger.info("Shutting down...")
    if heartbeat_service_instance:
        heartbeat_service_instance.stop()


def _inject_all_dependencies():
    """向所有路由模块注入依赖"""
    from routers import config, memory, characters, soul, debug
    
    # config router
    config.inject_dependencies(
        memory_clients, dreaming_service, soul_client, 
        heartbeat_service_instance, config_timestamps
    )
    
    # memory router
    memory.inject_dependencies(
        memory_clients, dreaming_service, soul_client, surreal_system, 
        hippocampus_service_instance
    )
    
    # characters router
    characters.inject_dependencies(memory_clients, soul_client)
    
    # soul router
    soul.inject_dependencies(
        memory_clients, soul_client, dreaming_service,
        heartbeat_service_instance, config_timestamps
    )
    
    # debug router
    # debug router
    debug.inject_dependencies(memory_clients, surreal_system, hippocampus_service_instance)


# ========== 创建应用 ==========
app = FastAPI(
    title="Lumina Memory Server",
    description="模块化记忆管理服务",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册路由 ==========
from routers import config, memory, characters, soul, debug

app.include_router(config.router)
app.include_router(memory.router)
app.include_router(characters.router)
app.include_router(soul.router)
app.include_router(debug.router)


# ========== 根端点 ==========
@app.get("/")
async def root():
    return {
        "service": "Lumina Memory Server",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "config": "/configure, /health",
            "memory": "/add, /search, /search/hybrid, /all",
            "characters": "/characters/*",
            "soul": "/soul/*, /galgame/*, /dream/*",
            "debug": "/debug/brain_dump, /debug/processing_status, /debug/surreal/*"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
