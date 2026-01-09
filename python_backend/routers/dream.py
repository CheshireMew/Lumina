"""
Dream 路由 - 触发 Dreaming 系统处理对话日志
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("DreamRouter")

router = APIRouter(prefix="/dream", tags=["Dream"])

# 全局引用（由 main.py 注入）
dreaming_service = None
surreal_system = None


def inject_dependencies(dreaming, surreal):
    """由 main.py 调用，注入全局依赖"""
    global dreaming_service, surreal_system
    dreaming_service = dreaming
    surreal_system = surreal


class WakeUpRequest(BaseModel):
    character_id: Optional[str] = None
    batch_size: int = 10


@router.post("/wake_up")
async def wake_up(request: WakeUpRequest = WakeUpRequest()):
    """
    唤醒 Dreaming 系统，处理对话日志生成 episodic_memory
    前端启动时自动调用
    """
    global dreaming_service
    
    if not dreaming_service:
        raise HTTPException(status_code=503, detail="Dreaming service not initialized")
    
    try:
        logger.info(f"[Dream] 🌙 Wake up triggered, batch_size={request.batch_size}")
        
        # 处理记忆
        await dreaming_service.process_memories(batch_size=request.batch_size)
        
        return {
            "status": "success",
            "message": "Dreaming cycle completed",
            "character_id": dreaming_service.character_id
        }
        
    except Exception as e:
        logger.error(f"[Dream] Wake up failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """获取 Dreaming 系统状态"""
    global dreaming_service
    
    if not dreaming_service:
        return {"status": "not_initialized", "message": "Dreaming service not available"}
    
    return {
        "status": "ready",
        "character_id": dreaming_service.character_id,
        "model": getattr(dreaming_service, 'model', 'unknown')
    }
