import os
import sys
import time
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

# 导入 logger
logger = logging.getLogger("ModelManager")

class ModelManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            # 默认为 python_backend 的上一级目录下的 models
            self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
        else:
            self.base_dir = base_dir
            
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        self.original_env = {}

    def display_progress_bar(self, percent, message="", mb_downloaded=None, mb_total=None):
        """显示简单的文本进度条"""
        bar_length = 40
        filled_length = int(bar_length * percent / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        extra_info = ""
        if mb_downloaded is not None and mb_total is not None:
            extra_info = f" ({mb_downloaded:.2f}MB/{mb_total:.2f}MB)"
            
        sys.stdout.write(f"\r{message}: |{bar}| {percent}% {extra_info}")
        sys.stdout.flush()

    def download_file_with_retry(self, url, target_path, max_retry=3):
        """带重试和进度条的文件下载"""
        session = requests.Session()
        retry = Retry(total=max_retry, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        try:
            logger.info(f"Downloading {url} to {target_path}...")
            # 首次尝试不禁用 Verification
            response = session.get(url, stream=True, timeout=30)
        except requests.exceptions.SSLError:
            logger.warning("SSL verification failed, retrying without verification...")
            response = session.get(url, stream=True, verify=False, timeout=30)
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
        
        sys.stdout.write("\n") # 换行
        logger.info("Download complete.")
        return True

    def setup_model_env(self, model_subdir_name: str):
        """
        设置环境变量，将模型下载路径强制指向本项目下的 models/{model_subdir_name}。
        这对 ModelScope 和 HuggingFace 均有效。
        """
        target_path = os.path.join(self.base_dir, model_subdir_name)
        if not os.path.exists(target_path):
            os.makedirs(target_path)
            
        # 保存原始环境变量
        self.original_env['MODELSCOPE_CACHE'] = os.environ.get('MODELSCOPE_CACHE')
        self.original_env['HF_HOME'] = os.environ.get('HF_HOME')
        self.original_env['TORCH_HOME'] = os.environ.get('TORCH_HOME')
        
        # 设置新环境变量 (强制本地路径)
        # 注意：ModelScope 会在指定目录下再创建 Hub/Cache 结构，这是正常的
        os.environ['MODELSCOPE_CACHE'] = target_path
        os.environ['HF_HOME'] = target_path
        os.environ['TORCH_HOME'] = target_path
        
        logger.info(f"Environment variables hijacked. Models will be stored in: {target_path}")
        return target_path

    def restore_model_env(self):
        """恢复原始环境变量"""
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        logger.info("Environment variables restored.")

    def download_modelscope_model(self, model_id: str, local_dir: Optional[str] = None):
        """
        封装 ModelScope 下载逻辑。
        如果指定了 local_dir，则直接下载到该目录（扁平结构）。
        如果不指定，则依赖 setup_model_env 设置的 cache 目录（标准结构）。
        """
        try:
            from modelscope import snapshot_download
        except ImportError:
            logger.error("modelscope not installed.")
            return None

        logger.info(f"Starting download for {model_id} from ModelScope...")
        
        try:
            # 如果指定 local_dir，ModelScope 会将文件下载到该目录，不再依赖 Cache 结构
            path = snapshot_download(model_id, local_dir=local_dir) 
            logger.info(f"Model downloaded successfully to: {path}")
            return path
        except Exception as e:
            logger.error(f"ModelScope download failed: {e}")
            return None

# 全局单例
model_manager = ModelManager()
