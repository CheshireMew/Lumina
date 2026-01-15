import os
import sys
import time
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

from app_config import MODELS_DIR

# 瀵煎叆 logger
logger = logging.getLogger("ModelManager")

class ModelManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            # Use unified path from app_config (Compatible with packaged/dev modes)
            self.base_dir = str(MODELS_DIR)
        else:
            self.base_dir = base_dir
            
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        self.original_env = {}

    def display_progress_bar(self, percent, message="", mb_downloaded=None, mb_total=None):
        """Display simple progress bar"""
        bar_length = 40
        filled_length = int(bar_length * percent / 100)
        bar = '*' * filled_length + '-' * (bar_length - filled_length)
        
        extra_info = ""
        if mb_downloaded is not None and mb_total is not None:
            extra_info = f" ({mb_downloaded:.2f}MB/{mb_total:.2f}MB)"
            
        sys.stdout.write(f"\r{message}: |{bar}| {percent}% {extra_info}")
        sys.stdout.flush()

    def download_file_with_retry(self, url, target_path, max_retry=3):
        """Download file with retry and progress"""
        session = requests.Session()
        retry = Retry(total=max_retry, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        try:
            logger.info(f"Downloading {url} to {target_path}...")
            response = session.get(url, stream=True, timeout=30)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

        if response.status_code != 200:
            logger.error(f"Download failed with status code: {response.status_code}")
            return False

        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        percent = int(downloaded_size * 100 / total_size)
                        mb_dl = downloaded_size / (1024*1024)
                        mb_tot = total_size / (1024*1024)
                        self.display_progress_bar(percent, "Downloading", mb_dl, mb_tot)
        
        sys.stdout.write("\n") # Newline
        logger.info("Download complete.")
        return True

    def setup_model_env(self, model_subdir_name: str):
        """
        Set environment variables to force model download path to models/{name}.
        Works for ModelScope and HF.
        """
        target_path = os.path.join(self.base_dir, model_subdir_name)
        if not os.path.exists(target_path):
            os.makedirs(target_path)
            
        # Save original env
        self.original_env['MODELSCOPE_CACHE'] = os.environ.get('MODELSCOPE_CACHE')
        self.original_env['HF_HOME'] = os.environ.get('HF_HOME')
        self.original_env['TORCH_HOME'] = os.environ.get('TORCH_HOME')
        
        # Set new env (force local path)
        # Note: ModelScope creates Hub/Cache structure
        os.environ['MODELSCOPE_CACHE'] = target_path
        os.environ['HF_HOME'] = target_path
        os.environ['TORCH_HOME'] = target_path
        
        logger.info(f"Environment variables hijacked. Models will be stored in: {target_path}")
        return target_path

    def restore_model_env(self):
        """Restore original env"""
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        logger.info("Environment variables restored.")

    def download_modelscope_model(self, model_id: str, local_dir: Optional[str] = None):
        """
        Wrap ModelScope download logic.
        If local_dir specified, download flat structure.
        Otherwise use cache structure.
        """
        try:
            from modelscope import snapshot_download
        except ImportError:
            logger.error("modelscope not installed.")
            return None

        logger.info(f"Starting download for {model_id} from ModelScope...")
        
        try:
            # 濡傛灉鎸囧畾 local_dir锛孧odelScope 浼氬皢鏂囦欢涓嬭浇鍒拌鐩綍锛屼笉鍐嶄緷璧?Cache 缁撴瀯
            path = snapshot_download(model_id, local_dir=local_dir) 
            logger.info(f"Model downloaded successfully to: {path}")
            return path
        except Exception as e:
            logger.error(f"ModelScope download failed: {e}")
            return None

    def load_embedding_model(self, model_path: str):
        """
        Load SentenceTransformer from path.
        """
        try:
            # Lazy import to reduce startup time
            from sentence_transformers import SentenceTransformer
            import torch
            
            logger.info(f"Loading Embedding Model from {model_path}...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = SentenceTransformer(model_path, device=device)
            logger.info(f"Model loaded on {device}")
            return model
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
    def ensure_embedding_model(self, model_name: str) -> str:
        """
        Ensure the embedding model exists locally.
        Returns the absolute path to the model directory.
        """
        target_path = os.path.join(self.base_dir, model_name)
        
        # Simple existence check
        if os.path.exists(target_path) and os.listdir(target_path):
             logger.info(f"Embedding model found at {target_path}")
             return target_path
             
        logger.info(f"Embedding model not found at {target_path}. Downloading...")
        
        try:
            from sentence_transformers import SentenceTransformer
            # Use temp load and save to ensure portable folder structure
            # Default to sentence-transformers/ + name if not full path
            hub_name = "sentence-transformers/" + model_name if "/" not in model_name else model_name
            
            temp_model = SentenceTransformer(hub_name)
            temp_model.save(target_path)
            logger.info(f"Model successfully saved to {target_path}")
            return target_path
        except Exception as e:
            logger.error(f"Failed to download embedding model: {e}")
            raise

# 鍏ㄥ眬鍗曚緥
model_manager = ModelManager()
