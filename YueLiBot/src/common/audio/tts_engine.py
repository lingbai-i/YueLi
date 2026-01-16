import asyncio
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from src.common.logger import get_logger
from src.config.config import global_config

logger = get_logger("tts_engine")

class TTSEngine:
    """YueLiBot 核心 TTS 引擎 (CosyVoice)"""
    
    def __init__(self):
        self._load_config()

    def _load_config(self):
        try:
            voice_config = getattr(global_config, "voice", {})
            cosy_config = getattr(voice_config, "cosyvoice", {})
            
            if isinstance(cosy_config, dict):
                self.api_key = cosy_config.get("api_key", "")
                self.voice_id = cosy_config.get("voice_id", "longxiaochun")
                self.model = cosy_config.get("model", "cosyvoice-v1")
            else:
                self.api_key = getattr(cosy_config, "api_key", "")
                self.voice_id = getattr(cosy_config, "voice_id", "longxiaochun")
                self.model = getattr(cosy_config, "model", "cosyvoice-v1")
                
            if self.api_key:
                dashscope.api_key = self.api_key
            else:
                logger.warning("未在配置 [voice.cosyvoice] 中找到 TTS API Key")
                
        except Exception as e:
            logger.error(f"加载 TTS 配置出错: {e}")
            self.api_key = ""

    async def generate_audio_bytes(self, text: str) -> bytes:
        """使用 CosyVoice 生成音频 bytes"""
        if not self.api_key:
            logger.error("未配置 TTS API Key。跳过合成。")
            return None
            
        try:
            def _sync_call():
                synthesizer = SpeechSynthesizer(model=self.model, voice=self.voice_id)
                # 确保文本不为空
                if not text or not text.strip():
                    return None
                audio = synthesizer.call(text)
                return audio

            # 在线程池中执行以避免阻塞 asyncio 循环
            loop = asyncio.get_running_loop()
            audio_result = await loop.run_in_executor(None, _sync_call)
            
            if audio_result is None:
                return None

            # 处理 SDK 的不同返回类型
            if isinstance(audio_result, bytes):
                return audio_result
            elif hasattr(audio_result, 'get_audio_data') and audio_result.get_audio_data():
                return audio_result.get_audio_data()
            else:
                logger.error(f"CosyVoice API 返回了无效数据: {audio_result}")
                return None
                
        except Exception as e:
            logger.error(f"TTS 合成失败: {e}")
            return None

