
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Any
from PIL import Image
import io
import base64
import logging
from routers.deps import get_vision_service

logger = logging.getLogger("VisionRouter")
router = APIRouter()

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
        try:
            provider = vision_service.get_active_provider()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        
        image_data = None
        
        # 1. Handle File Upload
        if file:
            content = await file.read()
            if len(content) > 10 * 1024 * 1024: # 10MB Limit
                raise HTTPException(status_code=413, detail="Image file too large (Max 10MB)")
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
    provider = vision_service.get_active_provider()
    background_tasks.add_task(provider.load)
    return {"status": "loading_started"}

@router.post("/unload")
async def unload_model(vision_service: Any = Depends(get_vision_service)):
    """Unload the model to free memory."""
    provider = vision_service.get_active_provider()
    provider.unload()
    return {"status": "unloaded"}
