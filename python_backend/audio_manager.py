"""
音频管理器 - 后端VAD和音频捕获
基于 Live2D-Virtual-Girlfriend 的架构设计
使用 sounddevice + webrtcvad 实现精确的设备隔离和VAD检测
"""

import sounddevice as sd
import webrtcvad
import numpy as np
import threading
import logging
from collections import deque
from typing import Optional, Callable, Dict, List
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path("audio_config.json")


class AudioManager:
    """
    音频管理器
    
    核心功能：
    1. 设备枚举和选择（支持设备名称持久化）
    2. 实时VAD检测（webrtcvad + 滑动窗口平滑）
    3. 预缓冲区（保留语音前0.5秒）
    4. 状态机管理（silence → speech_start → speech_continue → speech_end）
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 3,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable[[np.ndarray], None]] = None,
        on_vad_status_change: Optional[Callable[[str], None]] = None,
        voiceprint_manager=None,  # 新增
        enable_voiceprint=False,  # 新增  
        voiceprint_threshold=0.6  # 新增
    ):
        """
        初始化音频管理器
        
        Args:
            sample_rate: 采样率（webrtcvad要求16000Hz）
            frame_duration_ms: 帧时长（webrtcvad支持10/20/30ms）
            aggressiveness: VAD激进度（0-3，3最严格）
            on_speech_start: 语音开始回调
            on_speech_end: 语音结束回调（传入完整音频数据）
            on_vad_status_change: VAD状态变化回调
            voiceprint_manager: 声纹管理器实例（可选）
            enable_voiceprint: 是否启用声纹验证（默认False）
            voiceprint_threshold: 声纹相似度阈值 0-1（默认0.6）
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.aggressiveness = aggressiveness
        
        # 回调函数
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_vad_status_change = on_vad_status_change
        self.voiceprint_manager = voiceprint_manager
        self.enable_voiceprint = enable_voiceprint
        self.voiceprint_threshold = voiceprint_threshold
        
        # VAD实例
        self.vad = webrtcvad.Vad(aggressiveness)
        
        # === VAD 参数配置（可调整）===
        # 滑动窗口大小：用于平滑VAD结果，窗口越大越不敏感
        self.window_size = 15  # 帧数（原 10）
        
        # 语音开始阈值：窗口内语音帧比例超过此值才判定为开始说话
        self.speech_start_threshold = 0.8  # 80% 的帧是语音
        
        # 语音结束阈值：窗口内语音帧比例低于此值才判定为停止说话
        # ⚠️ 这个值越小，越容忍用户说话时的停顿
        self.speech_end_threshold = 0.05  # 5% 的帧是语音（原 0.15）
        
        # 最小语音长度（帧数）：低于此长度的音频会被丢弃（防止误触发）
        self.min_speech_frames = 15  # 约 0.45 秒（原 15）
        
        # 滑动窗口缓冲区（用于平滑VAD结果）
        self.speech_buffer = deque(maxlen=self.window_size)
        
        # 预缓冲区（保留语音前0.5秒）
        pre_buffer_frames = int(0.5 * 1000 / frame_duration_ms)  # 0.5s
        self.pre_buffer = deque(maxlen=pre_buffer_frames)
        
        # 音频帧累积
        self.audio_frames: List[np.ndarray] = []
        
        # 状态标志
        self.is_speaking = False
        self.is_running = False
        
        # 音频流
        self.stream: Optional[sd.InputStream] = None
        self.device_index: Optional[int] = None
        self.device_name: Optional[str] = None
        
        # 加载配置
        self.load_config()
        

    
    def load_config(self):
        """从配置文件加载设备设置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.device_name = config.get("device_name")
                    self.speech_start_threshold = config.get("speech_start_threshold", 0.6)
                    self.speech_end_threshold = config.get("speech_end_threshold", 0.05)
                    self.min_speech_frames = config.get("min_speech_frames", 15)
                    logger.info(f"已加载音频配置: Device={self.device_name}, Start={self.speech_start_threshold}, End={self.speech_end_threshold}")
            except Exception as e:
                logger.error(f"加载音频配置失败: {e}")
    
    def save_config(self):
        """保存音频设备配置到文件（保留现有配置）"""
        # 读取现有配置
        config = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"读取配置文件失败: {e}，将创建新配置")
        
        # 更新字段
        config['device_name'] = self.device_name
        config['speech_start_threshold'] = self.speech_start_threshold
        config['speech_end_threshold'] = self.speech_end_threshold
        config['min_speech_frames'] = self.min_speech_frames
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存音频配置")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def update_params(self, start_threshold: float = None, end_threshold: float = None, min_frames: int = None):
        """动态更新 VAD 参数"""
        if start_threshold is not None:
            self.speech_start_threshold = max(0.1, min(1.0, start_threshold))
        if end_threshold is not None:
            self.speech_end_threshold = max(0.01, min(1.0, end_threshold))
        if min_frames is not None:
             self.min_speech_frames = max(5, min(100, min_frames))
        
        self.save_config()
        logger.info(f"VAD 参数更新: Start={self.speech_start_threshold}, End={self.speech_end_threshold}")
    
    def list_devices(self) -> List[Dict]:
        """
        列出所有可用的音频输入设备（只返回真正可用的）
        
        Returns:
            设备列表，每个设备包含 index, name, channels, sample_rate
        """
        devices = []
        try:
            device_list = sd.query_devices()
            for i, dev in enumerate(device_list):
                # 只返回输入设备
                if dev['max_input_channels'] > 0:
                    # 测试设备是否真的可用
                    try:
                        # 尝试打开测试流（不启动）
                        test_stream = sd.InputStream(
                            device=i,
                            channels=1,
                            samplerate=self.sample_rate,
                            blocksize=self.frame_size,
                            dtype='float32'
                        )
                        test_stream.close()
                        
                        # 设备可用，添加到列表
                        devices.append({
                            'index': i,
                            'name': dev['name'],
                            'channels': dev['max_input_channels'],
                            'sample_rate': int(dev['default_samplerate']),
                            'hostapi': sd.query_hostapis(dev['hostapi'])['name']
                        })
                    except Exception as e:
                        # 设备不可用，跳过
                        logger.debug(f"Skipping device {i} ({dev['name']}): {e}")
                        continue
            
            logger.info(f"发现 {len(devices)} 个可用音频输入设备")
        except Exception as e:
            logger.error(f"枚举音频设备失败: {e}")
        
        return devices
    
    def set_device_by_name(self, device_name: str) -> bool:
        """
        通过设备名称设置音频输入设备（避免索引变化问题）
        
        Args:
            device_name: 设备名称
            
        Returns:
            是否设置成功
        """
        devices = self.list_devices()
        for dev in devices:
            if dev['name'] == device_name:
                self.device_index = dev['index']
                self.device_name = device_name
                self.save_config()
                logger.info(f"已设置音频设备: {device_name} (索引: {self.device_index})")
                return True
        
        logger.warning(f"未找到设备: {device_name}")
        return False
    
    def set_device(self, device_index: int) -> bool:
        """
        通过索引设置音频输入设备
        
        Args:
            device_index: 设备索引
            
        Returns:
            是否设置成功
        """
        devices = self.list_devices()
        for dev in devices:
            if dev['index'] == device_index:
                self.device_index = device_index
                self.device_name = dev['name']
                self.save_config()
                logger.info(f"已设置音频设备: {self.device_name} (索引: {device_index})")
                return True
        
        logger.warning(f"设备索引无效: {device_index}")
        return False
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """
        音频回调函数（由sounddevice实时调用）- 必须极快返回！
        
        Args:
            indata: 输入音频数据 (frames, channels) float32 [-1, 1]
            frames: 帧数
            time_info: 时间信息
            status: 状态标志
        """
        if status and status.input_overflow:
            # 静默处理overflow，不在这里log（太慢）
            pass
        
        # 转换为单声道（尽可能快）
        audio_frame = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
        
        # 快速VAD处理（不能有任何阻塞操作）
        result = self._process_frame(audio_frame)
        
        # 简单的状态通知（不log）
        if result == "speech_start" and self.on_speech_start:
            try:
                self.on_speech_start()
            except:
                pass
            
            if self.on_vad_status_change:
                try:
                    self.on_vad_status_change("listening")
                except:
                    pass
        
        elif result == "speech_end":
            audio_data = np.concatenate(self.audio_frames) if self.audio_frames else np.array([])
            self.audio_frames.clear()
            
            # ⚡ 声纹验证（如果启用）
            should_process = True
            if self.enable_voiceprint and self.voiceprint_manager and len(audio_data) > 0:
                try:
                    is_match, similarity = self.voiceprint_manager.verify(
                        audio_data, 
                        self.voiceprint_threshold,
                        self.sample_rate
                    )
                    if not is_match:
                        logger.info(f"[Voiceprint] 拒绝: 相似度 {similarity:.3f} < 阈值 {self.voiceprint_threshold}")
                        should_process = False
                    else:
                        logger.debug(f"[Voiceprint] 通过: 相似度 {similarity:.3f}")
                except Exception as e:
                    logger.warning(f"[Voiceprint] 验证失败: {e}，将继续处理音频")
            
            # 只有声纹验证通过才触发回调
            if should_process and self.on_speech_end and len(audio_data) > 0:
                try:
                    self.on_speech_end(audio_data)
                except:
                    pass
            
            if self.on_vad_status_change:
                try:
                    self.on_vad_status_change("idle")
                except:
                    pass
    
    def _process_frame(self, frame: np.ndarray) -> str:
        """
        处理单帧音频，执行VAD检测和状态机（必须快速返回！）
        
        Args:
            frame: 单帧音频数据 float32 [-1, 1]
            
        Returns:
            状态: "silence" | "speech_start" | "speech_continue" | "speech_end"
        """
        # 转换为 int16 PCM（webrtcvad要求）
        pcm = (frame.clip(-1, 1) * 32767).astype(np.int16).tobytes()
        
        # VAD检测
        try:
            is_speech = self.vad.is_speech(pcm, self.sample_rate)
        except:
            is_speech = False
        
        # 额外的能量检测（过滤低能量噪音）
        rms = np.sqrt(np.mean(frame**2))
        if rms < 0.01:  # 能量太低，认为是噪音
            is_speech = False
        
        # 更新滑动窗口
        self.speech_buffer.append(is_speech)
        
        # 计算语音比例（平滑VAD结果）
        speech_ratio = sum(self.speech_buffer) / len(self.speech_buffer) if self.speech_buffer else 0
        
        # 状态机（更严格的阈值）
        if not self.is_speaking and speech_ratio > 0.8:  # 提高到0.8（原0.7）
            # 检测到语音开始
            self.is_speaking = True
            
            # 将预缓冲区的历史音频加入（避免丢失开头）
            self.audio_frames.extend(list(self.pre_buffer))
            self.audio_frames.append(frame)
            
            return "speech_start"
        
        elif self.is_speaking and speech_ratio < 0.05:  # 降低到0.05（增大停顿容忍度，原0.15）
            # 检测到语音结束 - 检查最小长度
            if len(self.audio_frames) < 15:  # 至少15帧（0.45秒，原10帧）
                # 太短，可能是噪音，丢弃
                self.is_speaking = False
                self.audio_frames.clear()
                return "silence"
            
            self.is_speaking = False
            return "speech_end"
        
        elif self.is_speaking:
            # 语音持续中
            self.audio_frames.append(frame)
            return "speech_continue"
        
        else:
            # 静音状态：维护预缓冲区
            self.pre_buffer.append(frame)
            return "silence"
    
    def start(self):
        """启动音频捕获"""
        if self.is_running:
            logger.warning("音频管理器已在运行")
            return
        
        # 如果配置了设备名称，尝试恢复设备
        if self.device_name and self.device_index is None:
            self.set_device_by_name(self.device_name)
        
        try:
            # 打印设备信息
            if self.device_index is not None:
                device_info = sd.query_devices(self.device_index)
                logger.info(f"📢 即将使用设备: [{self.device_index}] {device_info['name']}")
                logger.info(f"   设备原生采样率: {device_info['default_samplerate']} Hz")
                logger.info(f"   强制使用16000 Hz (sounddevice将自动重采样)")
            else:
                logger.info(f"📢 将使用系统默认输入设备（16000 Hz）")
            
            logger.info(f"启动音频捕获 (device={self.device_index}, rate=16000, frame_size={self.frame_size})")
            
            # sounddevice会自动从设备原生采样率重采样到我们请求的16kHz
            self.stream = sd.InputStream(
                device=self.device_index,
                samplerate=16000,  # 强制16kHz，sounddevice自动重采样
                channels=1,
                dtype='float32',
                blocksize=self.frame_size,
                callback=self._audio_callback
            )
            
            self.stream.start()
            self.is_running = True
            logger.info("音频捕获已启动")
            
        except Exception as e:
            logger.error(f"启动音频捕获失败: {e}")
            self.is_running = False
            self.stream = None
            
            # 如果设备无效，尝试使用默认设备
            if "Invalid device" in str(e) or "PaErrorCode -9996" in str(e):
                logger.warning("设备无效，尝试使用系统默认输入设备")
                self.device_index = None
                self.device_name = None
                try:
                    self.stream = sd.InputStream(
                        samplerate=16000,
                        channels=1,
                        dtype='float32',
                        blocksize=self.frame_size,
                        callback=self._audio_callback
                    )
                    self.stream.start()
                    self.is_running = True
                    logger.info("已切换到系统默认音频设备")
                except Exception as e2:
                    logger.error(f"使用默认设备也失败: {e2}")
    
    def stop(self):
        """停止音频捕获"""
        if not self.is_running:
            return
        
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            self.is_running = False
            self.is_speaking = False
            self.audio_frames.clear()
            self.pre_buffer.clear()
            self.speech_buffer.clear()
            
            logger.info("音频捕获已停止")
        except Exception as e:
            logger.error(f"停止音频捕获失败: {e}")
    
    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            "is_running": self.is_running,
            "is_speaking": self.is_speaking,
            "device_name": self.device_name,
            "device_index": self.device_index,
            "sample_rate": self.sample_rate
        }
