import time
from typing import Optional
from src.common.logger import get_module_logger
from src.chat.message_receive.chat_stream import ChatStream
from src.chat.message_receive.message import Message, MessageSending
from maim_message import UserInfo, Seg
from src.chat.message_receive.storage import MessageStorage
from src.config.config import global_config
from rich.traceback import install

install(extra_lines=3)


logger = get_module_logger("message_sender")


class DirectMessageSender:
    """直接消息发送器"""

    def __init__(self, private_name: str):
        self.private_name = private_name
        self.storage = MessageStorage()

    async def send_message(
        self,
        chat_stream: ChatStream,
        content: str,
        reply_to_message: Optional[Message] = None,
    ) -> None:
        """发送消息到聊天流

        Args:
            chat_stream: 聊天流
            content: 消息内容
            reply_to_message: 要回复的消息（可选）
        """
        try:
            # 针对 Bilibili 平台的消息处理逻辑
            if chat_stream.platform == "bilibili":
                # 检查 Core Audio System 是否可用
                # 这里假设外部已经处理了音频播放（如 brain_chat.py 或 heartFC_chat.py 中的集成）
                # 我们主要负责发送逻辑的兼容性
                
                # 如果配置了 only_voice，我们可能不需要发送文本
                # 但这里是 DirectMessageSender，通常用于强制发送，所以我们仍然发送文本
                # 除非明确需要转换为 tts_text 类型（如果下游支持）
                
                # 由于 TTS 插件已移除，我们不再尝试调用它
                # 而是依赖 Core Audio Manager 在上层调用点进行处理
                
                # 如果需要阻止文本发送，应该在上层控制
                # 这里我们保持发送文本的行为，或者转换为 tts_text 如果协议层支持
                
                # 简单回退为发送文本，因为 Core Audio 已经由 brain_chat.py 处理
                segments = Seg(type="seglist", data=[Seg(type="text", data=content)])
                
                # 可选：如果我们想在这里触发 AudioManager，也可以引入
                # from src.common.audio.audio_manager import AudioManager
                # AudioManager().speak(content)
                # 但考虑到这是底层发送器，最好保持单纯
            else:
                # 其他平台正常发送文本
                segments = Seg(type="seglist", data=[Seg(type="text", data=content)])

            # 获取月璃的信息
            bot_user_info = UserInfo(
                user_id=global_config.BOT_QQ,
                user_nickname=global_config.BOT_NICKNAME,
                platform=chat_stream.platform,
            )

            # 用当前时间作为message_id，和之前那套sender一样
            message_id = f"dm{round(time.time(), 2)}"

            # 构建消息对象
            message = MessageSending(
                message_id=message_id,
                chat_stream=chat_stream,
                bot_user_info=bot_user_info,
                sender_info=reply_to_message.message_info.user_info if reply_to_message else None,
                message_segment=segments,
                reply=reply_to_message,
                is_head=True,
                is_emoji=False,
                thinking_start_time=time.time(),
            )

            # 处理消息
            await message.process()

            # 发送消息（直接调用底层 API）
            from src.chat.message_receive.uni_message_sender import _send_message
            
            sent = await _send_message(message, show_log=True)
            
            if sent:
                # 存储消息
                await self.storage.store_message(message, chat_stream)
                logger.info(f"[私聊][{self.private_name}]PFC消息已发送: {content}")
            else:
                logger.error(f"[私聊][{self.private_name}]PFC消息发送失败")
                raise RuntimeError("消息发送失败")

        except Exception as e:
            logger.error(f"[私聊][{self.private_name}]PFC消息发送失败: {str(e)}")
            raise

