"""
声纹识别管理器 - 基于 sherpa-onnx + 3D-Speaker CAM++
参考项目: ai_virtual_mate_web
模型: 阿里巴巴 3D-Speaker CAM++ (ONNX)
"""

import sherpa_onnx
import numpy as np
import soundfile as sf
import torch
import os
import json
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VoiceprintManager:
    """
    声纹特征提取和验证模块
    
    使用 sherpa-onnx + 3D-Speaker CAM++ 模型
    相比 Resemblyzer 优势:
    - 模型更小: 6MB vs 20MB (减少70%)
    - 速度更快: ~100ms vs ~200ms (提升50%)
    - 准确率更高: 专为中文优化
    """
    
    def __init__(
        self,
        model_path: str = "voiceprint_profiles/3dspeaker_campplus.onnx",
        profiles_dir: str = "voiceprint_profiles"
    ):
        """
        初始化声纹管理器
        
        Args:
            model_path: 3D-Speaker 模型路径
            profiles_dir: 声纹Profile存储目录
        """
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)
        
        # 检查模型文件
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"声纹识别模型未找到: {model_path}\n"
                f"请运行: python download_voiceprint_model.py"
            )
        
        # 选择推理设备（GPU优先）
        provider = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"声纹识别使用设备: {provider}")
        
        # 初始化声纹提取器
        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(model_path),
            debug=False,
            provider=provider,
            num_threads=max(1, os.cpu_count() - 1)  # 多线程优化
        )
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        self.user_embedding = None
        
        logger.info(f"声纹识别模型已加载: {model_path}")
    
    def extract_embedding(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        提取声纹特征向量
        
        Args:
            audio: 音频数据 (float32, 单声道)
            sample_rate: 采样率 (默认16kHz)
        
        Returns:
           embedding 向量 (256维)
        """
        # 确保音频是单声道float32
        if audio.ndim > 1:
            audio = audio[:, 0]  # 取第一声道
        audio = audio.astype(np.float32)
        
        # 创建推理流
        stream = self.extractor.create_stream()
        stream.accept_waveform(sample_rate=sample_rate, waveform=audio)
        stream.input_finished()
        
        # 计算embedding
        embedding = self.extractor.compute(stream)
        return np.array(embedding)
    
    def register_voiceprint(
        self, 
        audio: np.ndarray, 
        profile_name: str = "default",
        sample_rate: int = 16000
    ) -> np.ndarray:
        """
        注册用户声纹
        
        Args:
            audio: 音频数据 (建议3-5秒)
            profile_name: Profile名称
            sample_rate: 采样率
        
        Returns:
            embedding 向量
        """
        logger.info(f"正在注册声纹Profile: {profile_name}")
        
        # 提取特征
        embedding = self.extract_embedding(audio, sample_rate)
        
        # 保存到文件
        save_path = self.profiles_dir / f"{profile_name}.npy"
        np.save(save_path, embedding)
        
        # 更新元数据
        self._update_profile_metadata(profile_name, audio.shape[0] / sample_rate)
        
        logger.info(f"声纹已注册: {save_path}")
        return embedding
    
    def load_voiceprint(self, profile_name: str = "default") -> bool:
        """
        加载用户声纹
        
        Args:
            profile_name: Profile名称
        
        Returns:
            是否加载成功
        """
        load_path = self.profiles_dir / f"{profile_name}.npy"
        if load_path.exists():
            self.user_embedding = np.load(load_path)
            logger.info(f"声纹已加载: {profile_name}")
            return True
        else:
            logger.warning(f"声纹Profile不存在: {profile_name}")
            return False
    
    def verify(
        self, 
        audio: np.ndarray, 
        threshold: float = 0.6,
        sample_rate: int = 16000
    ) -> Tuple[bool, float]:
        """
        验证音频是否匹配用户声纹
        
        Args:
            audio: 待验证的音频数据
            threshold: 相似度阈值 (0-1，建议0.5-0.8)
            sample_rate: 采样率
        
        Returns:
            (is_match, similarity_score)
            - is_match: 是否匹配
            - similarity_score: 余弦相似度 (0-1)
        """
        if self.user_embedding is None:
            logger.warning("未加载用户声纹，验证失败")
            return (False, 0.0)
        
        # 提取待验证音频的特征
        test_embedding = self.extract_embedding(audio, sample_rate)
        
        # 计算余弦相似度
        dot_product = np.dot(self.user_embedding, test_embedding)
        norm1 = np.linalg.norm(self.user_embedding)
        norm2 = np.linalg.norm(test_embedding)
        
        if (norm1 * norm2) == 0:
            logger.warning("Embedding向量为零，验证失败")
            return (False, 0.0)
        
        similarity = float(dot_product / (norm1 * norm2))
        is_match = similarity >= threshold
        
        logger.debug(f"声纹验证: similarity={similarity:.4f}, threshold={threshold:.4f}, match={is_match}")
        return (is_match, similarity)
    
    def _update_profile_metadata(self, profile_name: str, duration: float):
        """
        更新Profile元数据
        
        Args:
            profile_name: Profile名称
            duration: 音频时长（秒）
        """
        metadata_path = self.profiles_dir / "profiles.json"
        
        # 加载现有元数据
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # 更新
        metadata[profile_name] = {
            "duration": duration,
            "created_at": str(Path(self.profiles_dir / f"{profile_name}.npy").stat().st_mtime)
        }
        
        # 保存
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def list_profiles(self) -> list:
        """
        列出所有声纹Profile
        
        Returns:
            Profile名称列表
        """
        profiles = [p.stem for p in self.profiles_dir.glob("*.npy")]
        return profiles
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        删除声纹Profile
        
        Args:
            profile_name: Profile名称
        
        Returns:
            是否删除成功
        """
        profile_path = self.profiles_dir / f"{profile_name}.npy"
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"声纹Profile已删除: {profile_name}")
            return True
        return False
