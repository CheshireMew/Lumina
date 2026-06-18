from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from routers.deps import get_container
from .worker_proxy import proxy_json_request, proxy_multipart_request

router = APIRouter(prefix="/capabilities/vision", tags=["Vision"])


@router.post("/analyze")
async def analyze_image(
    file: UploadFile | None = File(None),
    image_base64: str | None = Form(None),
    prompt: str = Form("Describe this image."),
    container=Depends(get_container),
):
    if file:
        content = await file.read()
        response = await proxy_multipart_request(
            "vision",
            "/analyze",
            files={
                "file": (
                    file.filename or "image",
                    content,
                    file.content_type or "application/octet-stream",
                )
            },
            data={"prompt": prompt},
            timeout=90.0,
            container=container,
        )
        return response.json()

    if image_base64:
        response = await proxy_multipart_request(
            "vision",
            "/analyze",
            files={},
            data={"image_base64": image_base64, "prompt": prompt},
            timeout=90.0,
            container=container,
        )
        return response.json()

    raise HTTPException(status_code=400, detail="No image provided")


@router.post("/load")
async def load_vision_model(container=Depends(get_container)):
    response = await proxy_json_request("vision", "POST", "/load", {}, container=container)
    return response.json()


@router.post("/unload")
async def unload_vision_model(container=Depends(get_container)):
    response = await proxy_json_request("vision", "POST", "/unload", {}, container=container)
    return response.json()
