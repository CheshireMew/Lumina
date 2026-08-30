import base64
import io
from typing import Any

from core.interfaces.driver import BaseVisionDriver


class MultimodalLLMVisionDriver(BaseVisionDriver):
    """Sends images through Lumina's configured vision LLM route."""

    def __init__(self, llm_manager: Any):
        super().__init__(
            "driver.vision.multimodal",
            "多模态视觉",
            "使用视觉模型路线中已配置的多模态 LLM 分析图片",
        )
        if llm_manager is None:
            raise ValueError("Multimodal vision requires LLMManager")
        self._llm_manager = llm_manager

    async def load(self):
        route = self._llm_manager.get_route("vision")
        provider = self._llm_manager.get_provider_config("vision")
        if route is None or not route.model.strip():
            raise RuntimeError("视觉模型尚未配置：请在模型设置中为 vision 路线选择模型。")
        if not provider.enabled:
            raise RuntimeError("视觉模型尚未配置：vision 路线所选服务已停用。")
        if not provider.base_url.strip():
            raise RuntimeError("视觉模型尚未配置：vision 路线所选服务缺少接口地址。")
        if provider.type == "pollinations" and not provider.api_key.strip():
            raise RuntimeError(
                "视觉模型尚未配置：Pollinations 匿名接口不支持图片输入；"
                "请填写 Pollinations API Key，或把 vision 路线切换到支持图片的 OpenAI 兼容服务。"
            )
        await self._llm_manager.get_driver("vision")

    def unload(self):
        return None

    async def analyze(self, image: Any, prompt: str = "Describe this image.") -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        driver = await self._llm_manager.get_driver("vision")
        result = await driver.chat_completion(
            messages,
            model=self._llm_manager.get_model_name("vision"),
            stream=False,
            **self._llm_manager.get_parameters("vision"),
        )
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("The configured vision model returned no description")
        return result.strip()
