import mss
import mss.tools
import base64
import io
import logging
import asyncio
from typing import Optional, Dict

logger = logging.getLogger("VisionService")

class VisionService:
    """
    Provides Active Vision capabilities (Screen Capture).
    """
    def __init__(self):
        self.mss = mss.mss()
        
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
        # Note: This assumes the driver supports OpenAI-style image content
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
            # We use non-streaming call for analysis usually
            # But our driver interface might be standardized on chat_completion generator
            response = ""
            async for token in llm_driver.chat_completion(messages, model="gpt-4o", stream=True):
                if token:
                    response += token
            return response
            
        except Exception as e:
            logger.error(f"Vision Analysis Failed: {e}")
            return f"Error analyzing screen: {e}"

# Singleton
vision_service = VisionService()
