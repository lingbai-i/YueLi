import asyncio
import logging
import time
from typing import List, Dict, Any

# 尝试从 maim_message 导入所需的类
try:
    from maim_message import (
        Router,
        RouteConfig,
        TargetConfig,
        MessageBase,
        BaseMessageInfo,
        UserInfo,
        GroupInfo,
        Seg,
        TemplateInfo,
        FormatInfo
    )
except ImportError:
    # 如果导入失败，提供一些 mock 类以防止完全崩溃 (主要用于开发环境没有库的情况)
    # 注意：这只是为了防止 import 错误，如果没有库，实际运行会失败
    logging.getLogger('MMCClient').warning("maim_message library not found, using mocks.")
    class Router:
        def __init__(self, *args): pass
        async def run(self): pass
        async def stop(self): pass
        async def send_message(self, *args): pass
        def register_class_handler(self, *args): pass
    class RouteConfig:
        def __init__(self, *args, **kwargs): pass
    class TargetConfig:
        def __init__(self, *args, **kwargs): pass
    class MessageBase:
        def __init__(self, *args, **kwargs): pass
    class BaseMessageInfo:
        def __init__(self, *args, **kwargs): pass
    class UserInfo:
        def __init__(self, *args, **kwargs): pass
    class GroupInfo:
        def __init__(self, *args, **kwargs): pass
    class Seg:
        def __init__(self, type, data): self.type = type; self.data = data
    class TemplateInfo: pass
    class FormatInfo:
        def __init__(self, *args, **kwargs): pass

logger = logging.getLogger('MMCClient')

# 定义接受的格式
ACCEPT_FORMAT = ["text", "image", "at", "reply", "json", "face"]

class MMCClient:
    def __init__(self, host, port, token, platform_name="bilibili"):
        self.host = host
        self.port = port
        self.platform_name = platform_name
        self.router = None
        self.token = token
        
        # 配置路由
        # 注意：URL 应该是 ws://host:port/ws
        url = f"ws://{host}:{port}/ws"
        logger.info(f"配置 MMC Router 连接至: {url}")
        
        route_config = RouteConfig(
            route_config={
                platform_name: TargetConfig(
                    url=url,
                    token=token or None,
                )
            }
        )
        self.router = Router(route_config, logger)
        self.reply_handler = None  # 回调函数
        
        # 注册一个空的类处理器，或者处理 Core 发来的指令
        self.router.register_class_handler(self.handle_core_message)

    def set_reply_handler(self, handler):
        """设置接收到回复时的回调函数"""
        self.reply_handler = handler

    async def connect(self):
        """连接到 Core"""
        # 启动 Router (后台运行)
        # Router.run() 是一个 async 方法，通常是一个死循环，需要放在后台任务中
        # 注意：Router.run() 通常不接受参数，它会尝试连接所有 target
        # 在 maim_message 中，run() 负责建立连接和保持连接
        
        # 检查是否已有运行的任务
        if self.router and not hasattr(self, '_router_task'):
             self._router_task = asyncio.create_task(self.router.run())
        
        logger.info(f"🧠 MMC Client 正在连接 {self.host}:{self.port} ...")

    async def close(self):
        """关闭连接"""
        if self.router:
            await self.router.stop()

    async def chat(self, message: str, user_id: str, nickname: str):
        """发送消息给 Core"""
        if not self.router:
            logger.warning("Router 未初始化，无法发送消息")
            return

        # 构造消息 ID 和时间
        msg_time = time.time()
        msg_id = str(msg_time)
        
        # 这里暂时硬编码群号，后续可以根据配置
        group_id = "23838688" # 直播间 ID

        try:
            # 构造 UserInfo
            user_info = UserInfo(
                platform=self.platform_name,
                user_id=str(user_id),
                user_nickname=nickname,
                user_cardname=nickname,
            )

            # 构造 GroupInfo
            group_info = GroupInfo(
                platform=self.platform_name,
                group_id=group_id,
                group_name=f"Bilibili直播间_{group_id}",
            )

            # 构造 FormatInfo
            format_info = FormatInfo(
                content_format=["text"], # 目前只发送文本
                accept_format=ACCEPT_FORMAT,
            )

            # 构造 Seg 列表
            # 文档规范：type="text"时data为字符串
            # type="seglist"时data为一个Seg列表
            inner_seg = Seg(type="text", data=message)
            submit_seg = Seg(type="seglist", data=[inner_seg])

            # 构造 BaseMessageInfo
            # 文档规范：BaseMessageInfo 需要 platform, message_id, time, user_info, format_info 等
            message_info = BaseMessageInfo(
                platform=self.platform_name,
                message_id=msg_id,
                time=msg_time,
                user_info=user_info,
                group_info=group_info,
                template_info=None,
                format_info=format_info,
                additional_config={},
            )

            # 构造 MessageBase
            msg_base = MessageBase(
                message_info=message_info,
                message_segment=submit_seg,
                raw_message=message
            )

            await self.router.send_message(msg_base)
            logger.info(f"📤 已发送给 Core: {nickname}({user_id}): {message}")

        except Exception as e:
            logger.error(f"🧠 发送失败: {e}", exc_info=True)

    async def handle_core_message(self, data):
        """处理 Core 发来的指令 (Reply)"""
        try:
            # 1. 如果 data 已经是 MessageBase 对象
            if isinstance(data, MessageBase):
                logger.info(f"📩 收到 Core 消息 (MessageBase): ID={data.message_info.message_id}")
                
                # 提取 Seg 列表
                segments = []
                # MessageBase 的 message_segment 应该是一个 Seg 对象（通常是 seglist 类型）
                top_seg = data.message_segment
                
                if top_seg.type == "seglist":
                    if isinstance(top_seg.data, list):
                        segments = top_seg.data
                else:
                    # 只有单个 Seg
                    segments = [top_seg]
                
                # 遍历提取文本
                reply_text = ""
                voice_data = None
                
                for seg in segments:
                    if seg.type == "text":
                        # seg.data 可能是字符串或者字典
                        if isinstance(seg.data, str):
                            reply_text += seg.data
                        elif isinstance(seg.data, dict) and "text" in seg.data:
                            reply_text += seg.data["text"]
                    elif seg.type == "voice":
                        # 处理语音数据 (Base64)
                        if isinstance(seg.data, str):
                            voice_data = seg.data
                            reply_text += " [语音消息]"
                    elif seg.type == "tts_text":
                        # 兼容旧版 TTS 文本
                        if isinstance(seg.data, str):
                            reply_text += f" [TTS文本: {seg.data}]"
                
                if voice_data:
                    logger.info(f"🔊 收到语音数据，准备播放...")
                    await self._play_audio(voice_data)

                if reply_text:
                    logger.info(f"📝 解析回复内容: {reply_text}")
                    if self.reply_handler:
                        await self.reply_handler(reply_text)
                else:
                    logger.warning("收到消息但未提取到文本内容")

            # 2. 如果是字典 (可能未被反序列化)
            elif isinstance(data, dict):
                logger.info(f"📩 收到 Core 消息 (Dict): {data}")
                # 暂时简单处理，通常 router 会处理成对象
                
            else:
                logger.info(f"📩 收到 Core 消息 (Unknown): {type(data)} - {data}")

        except Exception as e:
            logger.error(f"❌ 处理 Core 消息失败: {e}", exc_info=True)

    async def _play_audio(self, base64_data: str):
        """播放 Base64 编码的音频数据"""
        import base64
        import tempfile
        import os
        import asyncio
        
        try:
            # 1. 解码 Base64
            audio_bytes = base64.b64decode(base64_data)
            
            # 2. 保存到临时文件
            # pygame 通常需要文件路径
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            # 3. 尝试播放
            try:
                # 在线程池中执行播放，避免阻塞 asyncio 循环
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._play_audio_sync, tmp_path)
            finally:
                # 清理临时文件
                try:
                    os.remove(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def _play_audio_sync(self, file_path: str):
        """同步播放音频逻辑"""
        try:
            # 尝试导入 pygame
            import pygame
            
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # 释放资源
            pygame.mixer.quit()
            logger.info("✅ 语音播放完成")
            
        except ImportError:
            logger.warning("⚠️ 未安装 pygame，无法播放语音。请执行: pip install pygame")
            logger.info(f"语音文件已保存至临时路径 (但在本逻辑中已删除): {file_path}")
        except Exception as e:
            logger.error(f"Pygame 播放出错: {e}")
