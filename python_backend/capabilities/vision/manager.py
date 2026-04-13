
import mss
import mss.tools
import base64
import logging
from typing import Callable, Optional, Dict
from core.interfaces.driver import BaseVisionDriver
import os

logger = logging.getLogger("VisionManager")

class VisionPluginManager:
    """
    Central Vision Manager (previously VisionService).
    Manages Vision Drivers and Screen Capture.
    """
    def __init__(self, model_name_resolver: Callable[[str], str] | None = None):
        self.mss = mss.mss()
        self.model_name_resolver = model_name_resolver
        self.drivers: Dict[str, BaseVisionDriver] = {}
        self.active_driver_id: str = "moondream" # Default, or None
        self.active_driver: Optional[BaseVisionDriver] = None
        self.loading_status: str = "idle"

    async def register_drivers(self, auto_activate: bool = True):
        """Load vision drivers from plugins directory."""
        try:
            from sdk.lumina.loader import PluginLoader
            
            # Resolve root (python_backend)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(os.path.dirname(current_dir))
            
            drivers_dir = os.path.join(backend_root, "plugins", "drivers", "vision")
            if os.path.exists(drivers_dir):
                logger.info(f"Scanning Built-in Vision Drivers: {drivers_dir}")
                loaded = PluginLoader.load_plugins(drivers_dir, BaseVisionDriver)
                for d in loaded:
                    self.drivers[d.id] = d
                    logger.info(f"Loaded Vision Driver: {d.id}")
            else:
                logger.debug(f"Vision drivers directory not found: {drivers_dir}")
                
        except Exception as e:
            logger.error(f"Failed to load Vision drivers: {e}")

        # Active default if possible
        if self.drivers and not self.active_driver:
             # Prefer Moondream if present
             target = "driver.vision.moondream"
             if target not in self.drivers:
                 target = list(self.drivers.keys())[0]
             
             if auto_activate:
                 await self.activate(target)

    async def activate(self, driver_id: str):
        if driver_id not in self.drivers:
            logger.warning(f"Driver {driver_id} not found.")
            return

        logger.info(f"Activating Vision Driver: {driver_id}")
        self.loading_status = "loading"
        try:
            driver = self.drivers[driver_id]
            import inspect
            if inspect.iscoroutinefunction(driver.load):
                await driver.load()
            else:
                driver.load()
            
            self.active_driver = driver
            self.active_driver_id = driver_id
        except Exception as e:
            logger.error(f"Failed to activate vision driver {driver_id}: {e}")
            self.active_driver = None
        finally:
            self.loading_status = "idle"

    def get_active_provider(self) -> BaseVisionDriver:
        """Get the currently active local vision provider."""
        if not self.active_driver:
             if self.drivers:
                 # Auto-activate first available synchronously? 
                 # Better to raise error and expect activate() call
                 raise RuntimeError("No active vision driver. Call activate() first.")
             raise RuntimeError("No vision drivers available.")
        return self.active_driver

    def capture_screen_base64(self) -> Optional[str]:
        """
        Captures the primary monitor and returns it as a Base64 PNG string.
        """
        try:
            # Capture the first monitor
            monitor = self.mss.monitors[1] # 0 is all monitors combined, 1 is primary
            sct_img = self.mss.grab(monitor)
            
            # Convert to PNG bytes
            png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            
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
            # [Fix] Dynamic Model Selection
            model_name = "gpt-4o" # Default fallback
            if self.model_name_resolver:
                model_name = self.model_name_resolver("vision")

            response = ""
            async for token in llm_driver.chat_completion(messages, model=model_name, stream=True):
                if token:
                    response += token
            return response
            
        except Exception as e:
            logger.error(f"Vision Analysis Failed: {e}")
            return f"Error analyzing screen: {e}"
