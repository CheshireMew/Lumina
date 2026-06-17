
import base64
import logging
from typing import Callable, Optional
from core.interfaces.driver import BaseVisionDriver
from services.managers.driver_loader import DriverLoader
from services.managers.provider_host import ProviderHostManager
import os

logger = logging.getLogger("VisionManager")

try:
    import mss as MSS_MODULE
    import mss.tools as MSS_TOOLS
except ModuleNotFoundError:
    MSS_MODULE = None
    MSS_TOOLS = None

class VisionPluginManager(ProviderHostManager):
    """
    Central manager for vision drivers and screen capture.
    """
    def __init__(self, config, model_name_resolver: Callable[[str], str] | None = None):
        super().__init__(config=config, capability="vision")
        self.mss = MSS_MODULE.mss() if MSS_MODULE else None
        self._mss_tools = MSS_TOOLS
        self.model_name_resolver = model_name_resolver

    async def load_drivers(self):
        """Load vision drivers from capability modules."""
        try:
            # Resolve root (python_backend)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(os.path.dirname(current_dir))
            
            drivers_dir = os.path.join(backend_root, "capability_modules", "vision", "drivers", "vision")
            if os.path.exists(drivers_dir):
                logger.info(f"Scanning Built-in Vision Drivers: {drivers_dir}")
                loaded = DriverLoader.load_plugins(drivers_dir, BaseVisionDriver)
                for d in loaded:
                    self.register_driver(d)
                    logger.info(f"Loaded Vision Driver: {d.id}")
            else:
                logger.debug(f"Vision drivers directory not found: {drivers_dir}")
                
        except Exception as e:
            logger.error(f"Failed to load Vision drivers: {e}")

    async def activate_startup_driver(self):
        target_provider = self.resolve_startup_driver_id()
        if target_provider and self.config.is_provider_desired_enabled(target_provider):
            await self.activate(target_provider)

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

    async def analyze_screen(self, llm_driver, prompt: str = "Please describe this screen.") -> str:
        """
        Captures screen and sends it to the LLM for analysis.
        """
        image_b64 = self.capture_screen_base64()
        if not image_b64:
            return "Failed to capture screen."

        # Construct Multi-modal Message
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_b64
                        }
                    }
                ]
            }
        ]
        
        try:
            if not self.model_name_resolver:
                raise RuntimeError("Vision model route resolver is not configured")
            model_name = self.model_name_resolver("vision")

            response = ""
            async for token in llm_driver.chat_completion(messages, model=model_name, stream=True):
                if token:
                    response += token
            return response
            
        except Exception as e:
            logger.error(f"Vision Analysis Failed: {e}")
            return f"Error analyzing screen: {e}"
