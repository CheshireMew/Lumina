
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException

LIPP_VERSION = "0.1.0"

# --- 1. Standard Data Models ---

class LippMetaResponse(BaseModel):
    """Identity Handshake"""
    service_name: str
    service_version: str = "1.0.0"
    lipp_version: str = LIPP_VERSION
    capabilities: List[str] = []
    status: Literal["starting", "running", "degraded", "stopped"] = "running"

class LippHealthResponse(BaseModel):
    """Health Check"""
    status: Literal["ok", "error"]
    details: Optional[Dict[str, Any]] = None

class LippLifecycleRequest(BaseModel):
    """Lifecycle command for enabling, disabling, or reloading a worker service target."""
    action: Literal["enable", "disable", "reload"]
    target_id: str
    config: Optional[Dict[str, Any]] = None

class LippConfigRequest(BaseModel):
    """Unified Config Update"""
    target_id: str
    key: str
    value: Any

class LippResponse(BaseModel):
    """Standard Response Wrapper"""
    status: Literal["ok", "error"]
    message: Optional[str] = None
    data: Optional[Any] = None

# --- 2. Protocol Router Generator ---

class LippProtocol:
    """
    Helper to create standardized LIPP routers.
    Worker Services should mixin or delegate to this.
    """
    @staticmethod
    def create_router(
        service_name: str,
        lifecycle_handler: callable,
        config_handler: callable,
        health_handler: callable = None,
        capabilities: List[str] = []
    ) -> APIRouter:
        
        router = APIRouter(prefix="/lipp/v1", tags=["LIPP"])
        
        @router.get("/meta", response_model=LippMetaResponse)
        async def get_meta():
            return LippMetaResponse(
                service_name=service_name,
                capabilities=capabilities,
                status="running" # Dynamic?
            )
            
        @router.get("/health", response_model=LippHealthResponse)
        async def get_health():
            if health_handler:
                return await health_handler()
            return LippHealthResponse(status="ok")
            
        @router.post("/lifecycle", response_model=LippResponse)
        async def on_lifecycle(payload: LippLifecycleRequest, request: Request):
            try:
                # Security: Localhost Only
                if request.client.host not in ["127.0.0.1", "::1", "localhost"]:
                     raise HTTPException(403, "Access Denied")
                     
                await lifecycle_handler(payload)
                return LippResponse(status="ok", message=f"Action {payload.action} executed on {payload.target_id}")
            except Exception as e:
                return LippResponse(status="error", message=str(e))
                
        @router.post("/config", response_model=LippResponse)
        async def on_config(payload: LippConfigRequest, request: Request):
            try:
                 # Security: Localhost Only
                if request.client.host not in ["127.0.0.1", "::1", "localhost"]:
                     raise HTTPException(403, "Access Denied")
                     
                result = await config_handler(payload)
                return LippResponse(status="ok", data=result)
            except Exception as e:
                return LippResponse(status="error", message=str(e))
                
        return router
