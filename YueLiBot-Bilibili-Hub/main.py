import aiohttp
import asyncio
import logging
import random
import toml
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from mmc_client import MMCClient as BrainClient

# 配置日志
import blivedm
import blivedm.models as web_models

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MaiHub')

# 加载配置
try:
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.toml")
    config = toml.load(config_path)
    ROOM_ID = config["Bilibili"]["room_id"]
except Exception as e:
    logger.error(f"加载配置文件失败: {e}")
    exit(1)

# === 数据结构定义 ===

class EventType(Enum):
    DANMAKU = "danmaku"
    GIFT = "gift"
    SUPER_CHAT = "super_chat"
    GUARD = "guard"

@dataclass(order=True)
class PriorityItem:
    priority: int
    timestamp: float
    event_type: EventType = field(compare=False)
    data: dict = field(compare=False)
    
    # 使得高优先级的数字更大（默认heapq是小顶堆，所以我们要存负数或者重写比较）
    # 这里我们简单约定：priority 越小优先级越高。
    # Config里是分越高越优先，所以初始化时存 -score

# === 核心组件 ===

class DanmakuFilter:
    """弹幕过滤器与评分系统"""
    def __init__(self):
        self.history = []
    
    def score_message(self, message: web_models.DanmakuMessage) -> int:
        score = 0
        text = message.msg
        
        # 基础分
        score += 10
        
        # 长度适中加分
        if 5 <= len(text) <= 20:
            score += 20
            
        # 包含特定关键词加分（模拟）
        if "月璃" in text or "YueLi" in text:
            score += 30
        if "?" in text or "？" in text:
            score += 10
            
        # 过滤垃圾弹幕 (简单的长度过滤)
        if len(text) > 50:
            return 0
            
        return score

class Scheduler:
    """调度器：管理优先级队列"""
    def __init__(self):
        self.queue = asyncio.PriorityQueue()
        
    async def add_event(self, priority: int, event_type: EventType, data: dict):
        # PriorityQueue 是小顶堆，所以用 -priority 让大数排前面
        item = PriorityItem(priority=-priority, timestamp=asyncio.get_event_loop().time(), event_type=event_type, data=data)
        await self.queue.put(item)
        logger.info(f"➕ 入队: [{event_type.name}] 优先级 {priority} - {data.get('user', 'unknown')}: {data.get('content', '')[:20]}")

    async def get_next_event(self) -> PriorityItem:
        return await self.queue.get()

# === Bilibili 监听器 ===

class BilibiliListener(blivedm.BaseHandler):
    def __init__(self, scheduler: Scheduler, filter: DanmakuFilter):
        self.scheduler = scheduler
        self.filter = filter

    async def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        await self._on_danmaku_async(client, message)

    async def _on_danmaku_async(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        # 0. Debug日志
        logger.info(f"👀 收到弹幕: {message.uname}: {message.msg}")
        
        # 1. 评分
        score = self.filter.score_message(message)
        if score < config["Filter"]["min_score"]:
            return # 丢弃低分弹幕
        
        # 2. 入队 (普通弹幕优先级)
        await self.scheduler.add_event(
            priority=config["Priority"]["danmaku"] + score, # 基础分 + 评分
            event_type=EventType.DANMAKU,
            data={
                "user": message.uname,
                "content": message.msg,
                "uid": message.uid
            }
        )

    async def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        await self._on_gift_async(client, message)

    async def _on_gift_async(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        # 过滤掉免费礼物或低价值礼物（可选）
        if message.coin_type == "silver" and message.total_coin < 0: # 银瓜子通常忽略，除非想刷屏
            return

        await self.scheduler.add_event(
            priority=config["Priority"]["gift"],
            event_type=EventType.GIFT,
            data={
                "user": message.uname,
                "content": f"赠送了 {message.gift_name} x {message.num} (价值 {message.total_coin/1000 if message.coin_type == 'gold' else 0} 元)",
                "gift_name": message.gift_name,
                "num": message.num,
                "price": message.total_coin,
                "uid": message.uid
            }
        )
        logger.info(f"🎁 收到礼物: {message.uname} - {message.gift_name} x {message.num}")

    async def _on_guard_buy(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        await self._on_guard_buy_async(client, message)

    async def _on_guard_buy_async(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        await self.scheduler.add_event(
            priority=config["Priority"]["guard"],
            event_type=EventType.GUARD,
            data={
                "user": message.username,
                "content": f"开通了 {message.gift_name} 舰长",
                "gift_name": message.gift_name,
                "num": message.num,
                "price": message.price,
                "uid": message.uid
            }
        )
        logger.info(f"🛡️ 收到大航海: {message.username} - {message.gift_name}")

    async def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        await self._on_super_chat_async(client, message)

    async def _on_super_chat_async(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        await self.scheduler.add_event(
            priority=config["Priority"]["super_chat"],
            event_type=EventType.SUPER_CHAT,
            data={
                "user": message.uname,
                "content": message.message,
                "price": message.price
            }
        )
        logger.info(f"💰 收到 SC: {message.uname} - ¥{message.price}")

    async def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        logger.info(f"❤️ 心跳: 人气值 {message.popularity}")

# === 主控制循环 ===

class MaiHub:
    def __init__(self):
        self.scheduler = Scheduler()
        self.filter = DanmakuFilter()
        self.brain = BrainClient(
            host=config["YueLiBot_Server"]["host"],
            port=config["YueLiBot_Server"]["port"],
            token=config["YueLiBot_Server"]["token"],
            platform_name=config["YueLiBot_Server"].get("platform_name", "bilibili")
        )
        self.brain.set_reply_handler(self.handle_brain_reply)
        
        self.listener = BilibiliListener(self.scheduler, self.filter)
        self.client = None # Delay init

    async def send_danmaku(self, text: str):
        """发送 Bilibili 弹幕"""
        if not self.client or not self.client._session:
            logger.error("❌ 无法发送弹幕: 客户端未初始化")
            return

        url = 'https://api.live.bilibili.com/msg/send'
        csrf = config["Bilibili"].get("bili_jct")
        
        if not csrf:
            logger.error("❌ 无法发送弹幕: 缺少 bili_jct (CSRF Token)")
            return

        data = {
            'bubble': '0',
            'msg': text,
            'color': '16777215',
            'mode': '1',
            'fontsize': '25',
            'rnd': str(int(asyncio.get_event_loop().time())),
            'roomid': ROOM_ID,
            'csrf': csrf,
            'csrf_token': csrf,
        }

        try:
            async with self.client._session.post(url, data=data) as resp:
                result = await resp.json()
                if result['code'] == 0:
                    logger.info(f"✅ 弹幕发送成功: {text}")
                else:
                    logger.error(f"❌ 弹幕发送失败: {result['message']}")
        except Exception as e:
            logger.error(f"❌ 发送异常: {e}")

    async def handle_brain_reply(self, text: str):
        """处理来自 Brain 的回复"""
        logger.info(f"🔊 收到回复 (VTB模式-仅语音): {text}")
        # VTB模式下不需要发送文字弹幕，语音由 Core 的 TTS 插件处理
        # await self.send_danmaku(text)

    async def start(self):
        logger.info("🚀 正在启动 YueLiBot Bilibili Hub...")
        
        # Init Bilibili Client with Cookies
        cookies = {}
        if config["Bilibili"].get("sessdata"):
            cookies["SESSDATA"] = config["Bilibili"]["sessdata"]
        if config["Bilibili"].get("bili_jct"):
            cookies["bili_jct"] = config["Bilibili"]["bili_jct"]
        if config["Bilibili"].get("buvid3"):
            cookies["buvid3"] = config["Bilibili"]["buvid3"]
        if config["Bilibili"].get("dedeuserid"):
            cookies["DedeUserID"] = config["Bilibili"]["dedeuserid"]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://live.bilibili.com/{ROOM_ID}"
        }

        session = aiohttp.ClientSession(cookies=cookies, headers=headers)
        self.client = blivedm.BLiveClient(ROOM_ID, session=session, uid=config["Bilibili"].get("uid", 0))
        self.client.add_handler(self.listener)
        
        # 初始化 Brain
        await self.brain.connect()
        
        # 启动 Bilibili 客户端
        self.client.start()
        
        # 发送启动测试消息
        logger.info("等待连接建立...")
        await asyncio.sleep(5) # 等待连接建立
        await self.brain.chat("Bilibili Hub 已连接到 YueLiBot Core!", "0", "System")
        
        # 启动处理循环
        process_task = asyncio.create_task(self.process_loop())
        
        try:
            # 保持 Bilibili 连接
            await self.client.join()
        except asyncio.CancelledError:
            logger.info("正在停止...")
        finally:
            self.client.stop()
            await session.close()
            process_task.cancel()
            await self.brain.close()

    async def process_loop(self):
        """消费者循环：从队列取出事件并处理"""
        logger.info("⚙️ 处理循环已启动")
        while True:
            # 1. 获取下一个事件
            item = await self.scheduler.get_next_event()
            
            # 2. 处理事件 (模拟发送给 YueLiBot Core)
            await self.handle_event(item)
            
            # 3. 模拟处理耗时 (例如等待 TTS 播放完)
            # 在真实场景中，这里会等待 AudioPlayer 的信号
            await asyncio.sleep(2) 

    async def handle_event(self, item: PriorityItem):
        event_type = item.event_type
        data = item.data
        logger.info(f"🎤 正在处理: [{event_type.name}] {data.get('user')} 说: {data.get('content')}")
        
        # 处理所有类型的事件（只要有 content）
        if event_type in [EventType.DANMAKU, EventType.SUPER_CHAT, EventType.GIFT, EventType.GUARD]:
            await self.brain.chat(
                message=data.get('content'),
                user_id=str(data.get('uid', '0')),
                nickname=data.get('user', 'guest')
            )

async def main():
    hub = MaiHub()
    await hub.start()

if __name__ == '__main__':
    asyncio.run(main())


