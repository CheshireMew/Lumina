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

from vision_service import router as vision_router # [NEW] Vision API

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MemoryServer")

# ========== 全局状态 ==========
heartbeat_service_instance = None
soul_client = None # [FIX] Ensure defined
surreal_system = None
batch_manager_instance = None  # 批次管理器
dreaming_service_instance = None
bilibili_service_instance = None
config_timestamps: Dict = defaultdict(float)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global heartbeat_service_instance, soul_client, surreal_system
    
    from model_manager import model_manager
    from soul_manager import SoulManager
    from heartbeat_service import HeartbeatService
    from surreal_memory import SurrealMemory
    from dreaming import Dreaming
    
    # [Startup] 加载配置
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_config.json")
    if os.path.exists(config_path):
        try:
            logger.info(f"Loading saved config from {config_path}...")
            with open(config_path, 'r', encoding='utf-8-sig') as f: # [FIX] Handle BOM
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
            from app_config import config, MODELS_DIR
            
            # ⚡ Use central models dir
            model_subpath = config.models.embedding_model_name
            model_path = MODELS_DIR / model_subpath
            
            try:
                # Check if exists locally
                if not os.path.exists(str(model_path)) or not os.listdir(str(model_path)):
                     logger.info(f"Embedding model not found at {model_path}. Downloading...")
                     try:
                         from sentence_transformers import SentenceTransformer
                         # TODO: Consolidate this download logic with stt_server.py or a shared utility
                         # Download from Hub and Save to local portable folder
                         # We use a temporary cache or let it use default cache then save
                         temp_model = SentenceTransformer("sentence-transformers/" + model_subpath)
                         temp_model.save(str(model_path))
                         logger.info(f"Model saved to {model_path}")
                     except Exception as dl_err:
                         logger.error(f"Download failed: {dl_err}")
                         raise dl_err

                embedding_model = model_manager.load_embedding_model(str(model_path))
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                embedding_model = None


    

            
            logger.info(f"Auto-initialized memory for '{character_id}' (Surreal Only)")
            
            # 初始化 SurrealDB (使用 app_config 配置)
            try:
                surreal_system = SurrealMemory(character_id=character_id)
                await surreal_system.connect()
                
                # [Injection] Inject Global Encoder into SurrealMemory
                if embedding_model:
                     # Create a lambda or wrapper to match expected interface (encode(text)->list)
                    surreal_system.set_encoder(lambda text: embedding_model.encode(text).tolist())
                    
                # [Injection] 初始化并注入 BatchManager
                from consolidation_batch import BatchManager
                batch_manager_instance = BatchManager()
                surreal_system.set_batch_manager(batch_manager_instance)
                    
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

    # 初始化 Dreaming (ex-Hippocampus)
    global dreaming_service_instance
    try:
        if surreal_system:
            dreaming_service_instance = Dreaming(memory_client=surreal_system, character_id=character_id)
            logger.info(f"🧠 Dreaming Service initialized for '{character_id}'")
            
            # Inject into SurrealMemory for auto-digestion
            surreal_system.set_dreaming(dreaming_service_instance)
        else:
            logger.warning("⚠️ Dreaming Service skipped (SurrealDB not available)")
    except Exception as e:
        logger.error(f"Failed to init Dreaming: {e}")
    
    # [NEW] 初始化 Bilibili Service
    global bilibili_service_instance
    try:
        from bilibili_service import BilibiliService
        # Default room ID 0, will load from Soul config
        bilibili_service_instance = BilibiliService(soul_client, room_id=0)
        await bilibili_service_instance.start()
    except Exception as e:
        logger.error(f"Failed to start Bilibili Service: {e}")

    # 启动 Heartbeat
    try:
        logger.info("Starting Heartbeat Service...")
        if soul_client:
            # Heartbeat uses Dreaming logic to pulse
            heartbeat_service_instance = HeartbeatService(
                soul_client, 
                dreaming=dreaming_service_instance, 
                main_loop=asyncio.get_running_loop()
            )
            heartbeat_service_instance.start()
    except Exception as e:
        logger.error(f"Failed to start Heartbeat: {e}")

    # 注入依赖到各路由模块
    
    def _inject_all_dependencies():
        """向所有路由模块注入依赖"""
        from routers import config, memory, characters, soul, debug, dream, free_llm, llm_mgmt
        
        # config router
        config.inject_dependencies(
            soul_client, 
            heartbeat_service_instance, config_timestamps,
            dreaming_service_instance
        )
        
        # free llm router (no deps but good to init)
        free_llm.inject_dependencies(soul_client)

        # memory router
        memory.inject_dependencies(
            soul_client, surreal_system, 
            dreaming_service_instance
        )
        
        # characters router
        characters.inject_dependencies(soul_client)

        # soul router
        soul.inject_dependencies(
            soul_client,
            heartbeat_service_instance, config_timestamps
        )

        # llm_mgmt router
        llm_mgmt.inject_dependencies(soul_client)
        
        # debug router
        debug.inject_dependencies(surreal_system, dreaming_service_instance)
        
        # dream router
        dream.inject_dependencies(dreaming_service_instance, surreal_system)

    _inject_all_dependencies()

    yield
    
    # [Shutdown] 清理
    logger.info("Shutting down...")
    
    if bilibili_service_instance:
        await bilibili_service_instance.stop()

    if heartbeat_service_instance:
        heartbeat_service_instance.stop()
    
    if surreal_system:
        logger.info("Closing SurrealDB connection...")
        await surreal_system.close()



    



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
from routers import config, memory, characters, soul, debug, dream, llm_mgmt, free_llm
from fastapi.staticfiles import StaticFiles

app.include_router(config.router)
app.include_router(memory.router)
app.include_router(characters.router)
app.include_router(soul.router)
app.include_router(debug.router)
app.include_router(dream.router)
app.include_router(llm_mgmt.router)
app.include_router(free_llm.router) # ⚡ Free LLM / V1 API
app.include_router(vision_router) # [NEW] Vision API

# Live2D Static Files
current_dir = os.path.dirname(os.path.abspath(__file__))
live2d_path = os.path.join(current_dir, "live2d")

# Fallback for Development (../public/live2d)
if not os.path.exists(live2d_path):
    dev_path = os.path.join(current_dir, "..", "public", "live2d")
    if os.path.exists(dev_path):
        live2d_path = dev_path

if os.path.exists(live2d_path):
    app.mount("/live2d", StaticFiles(directory=live2d_path), name="live2d")
    logger.info(f"Mounted Live2D static files from {live2d_path}")
else:
    logger.warning(f"Live2D directory not found. Checked: {live2d_path}")


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
    from app_config import config
    uvicorn.run(app, host=config.network.host, port=config.network.memory_port)
