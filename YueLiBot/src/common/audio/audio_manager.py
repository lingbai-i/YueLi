import queue
import threading
import time
import asyncio
import numpy as np
import soundfile as sf
import io
import soundcard as sc
from typing import Optional, List, Union
from src.common.logger import get_logger
from src.config.config import global_config
from .tts_engine import TTSEngine

logger = get_logger("audio_manager")

class AudioManager:
    """
    YueLiBot 核心音频管理器。
    处理音频播放队列、设备路由（虚拟音频线）和并发播放。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AudioManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 音频队列：存储元组 (audio_data, sample_rate)
        # audio_data 可以是 numpy 数组或 bytes (wav 格式)
        self.audio_queue = queue.Queue()
        
        self.is_playing = False
        self.stop_event = threading.Event()
        
        # 输出设备
        self.output_device_name = None
        self.output_device = None
        
        # 低延迟的默认块大小
        self.block_size = 1024
        
        # TTS 引擎
        self.tts_engine = TTSEngine()
        
        # 启动播放线程
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        
        self._load_config()

    async def speak(self, text: str):
        """合成并播放文本（句子级流式处理）"""
        if not text or not text.strip():
            return

        # 简单的分句逻辑
        import re
        # 按标点符号分割，保留分隔符
        sentences = re.split(r'([。！？；!?;])', text)
        
        pending_text = ""
        for part in sentences:
            if not part:
                continue
            
            pending_text += part
            
            # 如果部分是标点符号，或者 pending_text 足够长，则进行合成
            # 检查部分是否为标点符号
            if re.match(r'[。！？；!?;]', part):
                if pending_text.strip():
                     await self._synthesize_and_queue(pending_text)
                pending_text = ""
        
        # 处理剩余文本
        if pending_text.strip():
            await self._synthesize_and_queue(pending_text)

    async def _synthesize_and_queue(self, segment: str):
        """辅助方法：合成并加入队列"""
        logger.info(f"正在合成片段: {segment[:20]}...")
        audio_data = await self.tts_engine.generate_audio_bytes(segment)
        if audio_data:
            self.add_audio(audio_data)
        else:
            logger.warning(f"片段合成失败: {segment[:20]}...")

    def _load_config(self):
        """从 global_config 加载配置"""
        try:
            # 检查 [voice.vtb] 配置
            # 我们假设配置结构已更新，否则回退到默认值
            voice_config = getattr(global_config, "voice", {})
            if hasattr(voice_config, "vtb"):
                vtb_config = voice_config.vtb
                if isinstance(vtb_config, dict):
                     self.output_device_name = vtb_config.get("output_device", "CABLE Input")
                else:
                     # 如果由配置加载器加载，可能是一个对象
                     self.output_device_name = getattr(vtb_config, "output_device", "CABLE Input")
            else:
                self.output_device_name = "CABLE Input" # VTB 默认值
                
            logger.info(f"AudioManager 已初始化。目标输出设备: {self.output_device_name}")
            self._update_output_device()
        except Exception as e:
            logger.error(f"加载 AudioManager 配置出错: {e}")

    def _update_output_device(self):
        """根据名称更新 soundcard 输出设备"""
        if not self.output_device_name:
            self.output_device = sc.default_speaker()
            return

        try:
            speakers = sc.all_speakers()
            target = None
            for s in speakers:
                if self.output_device_name.lower() in s.name.lower():
                    target = s
                    break
            
            if target:
                self.output_device = target
                logger.info(f"音频输出设备设置为: {target.name}")
            else:
                logger.warning(f"未找到设备 '{self.output_device_name}'。使用默认设备。")
                self.output_device = sc.default_speaker()
        except Exception as e:
            logger.error(f"设置输出设备失败: {e}")
            self.output_device = sc.default_speaker()

    def add_audio(self, audio_data: Union[bytes, np.ndarray], sample_rate: int = 48000):
        """
        添加音频到播放队列。
        :param audio_data: Bytes (WAV/PCM) 或 Numpy 数组。
        :param sample_rate: 如果 audio_data 是 numpy 数组或无头 raw bytes，则需要采样率。
        """
        self.audio_queue.put((audio_data, sample_rate))

    def stop_playback(self):
        """清空队列并停止当前播放（如果可能）"""
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
        # 注意：要在没有自定义阻塞逻辑的情况下中断 soundcard 当前正在播放的声音比较棘手。
        # 但是清空队列可以阻止下一句的播放。
        logger.info("播放队列已清空。")

    def _play_loop(self):
        """从队列播放音频的后台循环"""
        while not self.stop_event.is_set():
            try:
                item = self.audio_queue.get(timeout=1)
                audio_data, sample_rate = item
                self.is_playing = True
                
                try:
                    self._play_audio(audio_data, sample_rate)
                except Exception as e:
                    logger.error(f"播放音频出错: {e}")
                finally:
                    self.is_playing = False
                    self.audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"播放循环出错: {e}")
                time.sleep(1)

    def _play_audio(self, audio_data, sample_rate):
        """使用 soundcard 播放音频的内部方法"""
        data_np = None
        sr = sample_rate

        # 如果需要，将 bytes 转换为 numpy
        if isinstance(audio_data, bytes):
            try:
                # 首先尝试读取为 WAV
                with io.BytesIO(audio_data) as f:
                    data_np, sr = sf.read(f)
            except Exception:
                # 如果失败，假设是 raw PCM（16-bit 单声道？通常需要更多信息）
                # 目前假设它是来自 CosyVoice 的 WAV bytes
                logger.warning("解码 WAV bytes 失败，尝试 raw (假设 int16, 1ch)...")
                data_np = np.frombuffer(audio_data, dtype=np.int16)
                # 归一化为 float32 [-1, 1] 以供 soundcard 使用
                data_np = data_np.astype(np.float32) / 32768.0
        elif isinstance(audio_data, np.ndarray):
            data_np = audio_data
        else:
            logger.error(f"不支持的音频数据类型: {type(audio_data)}")
            return

        if data_np is None:
            return

        if self.output_device is None:
            self._update_output_device()

        # 播放
        # logger.debug(f"Playing audio: {data_np.shape}, sr={sr}")
        try:
            self.output_device.play(data_np, samplerate=sr)
        except Exception as e:
             logger.error(f"SoundCard 播放失败: {e}。重试默认设备...")
             try:
                 sc.default_speaker().play(data_np, samplerate=sr)
             except Exception as e2:
                 logger.error(f"默认扬声器播放失败: {e2}")


