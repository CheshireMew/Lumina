
import base64
import logging
from typing import Callable, Optional
from core.interfaces.driver import BaseVisionDriver
from services.managers.provider_host import ProviderHostManager

logger = logging.getLogger("VisionManager")

try:
    import mss as MSS_MODULE
    import mss.tools as MSS_TOOLS
except ModuleNotFoundError:
    MSS_MODULE = None
    MSS_TOOLS = None

class VisionProviderManager(ProviderHostManager):
    """
    Central manager for vision drivers and screen capture.
    """
    def __init__(
        self,
        config,
        model_name_resolver: Callable[[str], str] | None = None,
        llm_manager=None,
    ):
        super().__init__(config=config, capability="vision")
        self.mss = MSS_MODULE.mss() if MSS_MODULE else None
        self._mss_tools = MSS_TOOLS
        self.model_name_resolver = model_name_resolver
        self.llm_manager = llm_manager

    async def load_drivers(self):
        if self.llm_manager is None:
            logger.warning("Vision LLM manager is unavailable")
            return
        from provider_drivers.vision_llm.drivers.vision import MultimodalLLMVisionDriver

        self.register_driver(MultimodalLLMVisionDriver(self.llm_manager))

    async def activate_startup_driver(self):
        target_provider = self.resolve_startup_driver_id()
        if target_provider and self.config.is_provider_desired_enabled(target_provider):
            try:
                await self.activate(target_provider)
            except RuntimeError:
                logger.warning(
                    "Vision worker started in degraded mode: %s",
                    self.last_error,
                )

    async def register_drivers(self):
        await self.load_drivers()
        await self.activate_startup_driver()

    async def activate(self, driver_id: str):
        logger.info(f"Activating Vision Driver: {driver_id}")
        self.begin_transition(driver_id)
        try:
            driver = self.require_driver(driver_id)
            import inspect
            if inspect.iscoroutinefunction(driver.load):
                await driver.load()
            else:
                driver.load()
            self.mark_ready(driver, driver_id)
        except Exception as e:
            logger.error(f"Failed to activate vision driver {driver_id}: {e}")
            self.mark_error(str(e))
            self.active_driver_id = "none"
            raise
        finally:
            self.loading_status = "idle"

    def get_active_provider(self) -> BaseVisionDriver:
        """Get the currently active local vision provider."""
        if not self.active_driver:
             if self.last_error:
                 raise RuntimeError(self.last_error)
             if self.drivers:
                 raise RuntimeError("No active vision driver. Call activate() first.")
             raise RuntimeError("No vision drivers available.")
        return self.active_driver

    def capture_screen_base64(self) -> Optional[str]:
        """
        Captures the primary monitor and returns it as a Base64 PNG string.
        """
        try:
            if not self.mss or not self._mss_tools:
                raise RuntimeError("mss is not installed")

            # Capture the first monitor
            monitor = self.mss.monitors[1] # 0 is all monitors combined, 1 is primary
            sct_img = self.mss.grab(monitor)
            
            # Convert to PNG bytes
            png_bytes = self._mss_tools.to_png(sct_img.rgb, sct_img.size)
            
            # Encode to Base64
            b64_str = base64.b64encode(png_bytes).decode('utf-8')
            return f"data:image/png;base64,{b64_str}"
            
        except Exception as e:
            logger.error(f"Screen Capture Failed: {e}")
            return None

    async def analyze_screen(self, prompt: str = "请描述当前屏幕内容。") -> str:
        """Capture the primary screen and analyze it with the active provider."""
        image_b64 = self.capture_screen_base64()
        if not image_b64:
            raise RuntimeError("无法截取当前屏幕")

        try:
            import io
            from PIL import Image

            encoded = image_b64.split(",", 1)[-1]
            image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
            return await self.get_active_provider().analyze(image, prompt)
        except Exception as e:
            logger.error("Vision screen analysis failed: %s", e)
            raise
