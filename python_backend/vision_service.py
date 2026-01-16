from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from PIL import Image
import io
import base64
import logging
from core.interfaces.driver import BaseVisionDriver
from routers.deps import get_vision_service

# Concrete drivers loaded dynamically


logger = logging.getLogger("VisionService")

router = APIRouter(prefix="/vision", tags=["Vision"])

class VisionPluginManager:
    def __init__(self):
        self.drivers: Dict[str, BaseVisionDriver] = {}
        self.active_driver_id: str = "moondream"
        
        # Dynamic Loading
        try:
            from services.plugin_loader import PluginLoader
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__))
            drivers_dir = os.path.join(base_dir, "plugins", "drivers", "vision")
            
            loaded = PluginLoader.load_plugins(drivers_dir, BaseVisionDriver)
            for d in loaded:
                self.drivers[d.id] = d
                
        except Exception as e:
            logger.error(f"Failed to load dynamic Vision drivers: {e}")
            
        if not self.drivers:
            logger.warning("No Vision drivers found.")
        
    def get_active_provider(self) -> BaseVisionDriver:
        if self.active_driver_id not in self.drivers:
            raise RuntimeError(f"Active vision driver '{self.active_driver_id}' not found.")
        return self.drivers[self.active_driver_id]

# Singleton Manager Removed - Use ServiceContainer
# manager = VisionPluginManager()

class AnalyzeRequest(BaseModel):
    image_base64: Optional[str] = None
    prompt: str = "Describe this image."

@router.post("/analyze")
async def analyze_image(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    prompt: str = Form("Describe this image."),
    vision_service: Any = Depends(get_vision_service)
):
    """
    Analyze an image (from file upload or base64) and return text description.
    """
    try:
        # DI: vision_service is injected
        provider = vision_service.get_active_provider()
        
        image_data = None
        
        # 1. Handle File Upload
        if file:
            content = await file.read()
            image_data = io.BytesIO(content)
        # 2. Handle Base64
        elif image_base64:
            # Remove header if present (e.g., "data:image/png;base64,")
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            image_data = io.BytesIO(base64.b64decode(image_base64))
        else:
            raise HTTPException(status_code=400, detail="No image provided (file or image_base64 required)")

        # Load PIL Image
        try:
            image = Image.open(image_data).convert("RGB") # Moondream needs RGB
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

        # Analyze
        description = await provider.analyze(image, prompt)
        
        return {
            "status": "ok",
            "provider": provider.id,
            "description": description
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load")
async def load_model(background_tasks: BackgroundTasks, vision_service: Any = Depends(get_vision_service)):
    """Explicitly load the model into memory."""
    # [FIX] Use injected service, not 'manager' global
    provider = vision_service.get_active_provider()
    background_tasks.add_task(provider.load)
    return {"status": "loading_started"}

@router.post("/unload")
async def unload_model(vision_service: Any = Depends(get_vision_service)):
    """Unload the model to free memory."""
    # [FIX] Use injected service, not 'manager' global
    provider = vision_service.get_active_provider()
    provider.unload()
    return {"status": "unloaded"}
