import torch
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer
from vision.base import VisionProvider
import logging

logger = logging.getLogger("MoondreamProvider")

import os
from huggingface_hub import snapshot_download
from app_config import MODELS_DIR

class MoondreamProvider(VisionProvider):
    def __init__(self, model_id: str = "vikhyatk/moondream2"):
        self._model_id = model_id
        self.model = None
        self.tokenizer = None
        self.device = "cpu" # Force CPU for lightweight requirement
        # self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # [OPTIONAL] Set mirror for China users if speed is slow
        if "HF_ENDPOINT" not in os.environ:
             os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    @property
    def provider_id(self) -> str:
        return "moondream"

    def load(self):
        if self.model is not None:
            return

        logger.info(f"Loading Moondream2 model ({self.device})...")
        
        # Define local path
        local_model_path = MODELS_DIR / "moondream2"
        
        try:
            # Check if we need to download
            if not local_model_path.exists() or not any(local_model_path.iterdir()):
                logger.info(f"Downloading model to {local_model_path} (Mirror: hf-mirror.com)...")
                snapshot_download(
                    repo_id=self._model_id,
                    local_dir=local_model_path,
                    local_dir_use_symlinks=False
                )
            else:
                logger.info(f"Using local model at {local_model_path}")
                
            # Use smaller revision if available, or standard
            self.model = AutoModelForCausalLM.from_pretrained(
                local_model_path, 
                trust_remote_code=True,
                torch_dtype=torch.float32,
                local_files_only=True
            ).to(self.device)
            
            self.tokenizer = AutoTokenizer.from_pretrained(local_model_path, local_files_only=True)
            logger.info("Moondream2 loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Moondream2: {e}")
            raise

    def unload(self):
        if self.model:
            del self.model
            del self.tokenizer
            import gc
            gc.collect()
            self.model = None
            self.tokenizer = None
            logger.info("Moondream2 unloaded.")

    async def analyze(self, image: Image.Image, prompt: str = "Describe this image.") -> str:
        if not self.model:
            self.load()

        return await asyncio.get_event_loop().run_in_executor(
            self._executor,
            self._analyze_sync,
            image,
            prompt
        )

    def _analyze_sync(self, image: Image.Image, prompt: str) -> str:
        try:
            enc_image = self.model.encode_image(image)
            answer = self.model.answer_question(enc_image, prompt, self.tokenizer)
            return answer
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return f"Error analyzing image: {str(e)}"
