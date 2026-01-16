import time
import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from src.common.logger import get_logger

logger = get_logger("emotion_manager")

@dataclass
class EmotionState:
    """情绪状态向量 (0.0 - 1.0)"""
    joy: float = 0.0      # 喜悦
    anger: float = 0.0    # 愤怒
    sorrow: float = 0.0   # 哀伤
    fear: float = 0.0     # 恐惧
    surprise: float = 0.0 # 惊讶
    neutral: float = 1.0  # 平静 (基准值)

    def normalize(self):
        """归一化情绪向量，使其总和趋近于 1 (可选，取决于具体算法需求)"""
        # 在本系统中，我们允许混合情绪，不强制归一化到1，
        # 但通常会限制每个分量在 0-1 之间
        self.joy = max(0.0, min(1.0, self.joy))
        self.anger = max(0.0, min(1.0, self.anger))
        self.sorrow = max(0.0, min(1.0, self.sorrow))
        self.fear = max(0.0, min(1.0, self.fear))
        self.surprise = max(0.0, min(1.0, self.surprise))
        self.neutral = max(0.0, min(1.0, self.neutral))

    def decay(self, factor: float = 0.95):
        """情绪自然衰减，回归平静"""
        self.joy *= factor
        self.anger *= factor
        self.sorrow *= factor
        self.fear *= factor
        self.surprise *= factor
        
        # Neutral 逐渐恢复到 1.0
        self.neutral = self.neutral + (1.0 - self.neutral) * (1.0 - factor)
        self.normalize()

    def to_dict(self) -> Dict[str, float]:
        return {
            "joy": self.joy,
            "anger": self.anger,
            "sorrow": self.sorrow,
            "fear": self.fear,
            "surprise": self.surprise,
            "neutral": self.neutral
        }

class EmotionManager:
    """
    情绪管理器
    管理每个聊天流 (stream_id) 的情绪状态
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmotionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # 存储每个会话的情绪状态: stream_id -> EmotionState
        self.states: Dict[str, EmotionState] = {}
        # 记录上次更新时间，用于计算衰减
        self.last_update_time: Dict[str, float] = {}
        
        self._initialized = True
        logger.info("EmotionManager 初始化完成")

    def get_state(self, stream_id: str) -> EmotionState:
        """获取指定会话的情绪状态，如果不存在则创建默认状态"""
        if stream_id not in self.states:
            self.states[stream_id] = EmotionState()
            self.last_update_time[stream_id] = time.time()
        
        # 获取时先进行时间衰减计算
        self._apply_time_decay(stream_id)
        return self.states[stream_id]

    def update_state(self, stream_id: str, delta: Dict[str, float]):
        """
        更新情绪状态
        delta: 情绪变化增量，例如 {"joy": 0.2, "anger": -0.1}
        """
        state = self.get_state(stream_id)
        
        for emotion, change in delta.items():
            if hasattr(state, emotion):
                current_val = getattr(state, emotion)
                setattr(state, emotion, current_val + change)
        
        state.normalize()
        self.last_update_time[stream_id] = time.time()
        logger.debug(f"Stream {stream_id} 情绪更新: {delta} -> {state.to_dict()}")

    def _apply_time_decay(self, stream_id: str):
        """根据时间流逝应用情绪衰减"""
        if stream_id not in self.states:
            return

        current_time = time.time()
        last_time = self.last_update_time.get(stream_id, current_time)
        elapsed = current_time - last_time
        
        # 设定衰减周期，例如每分钟衰减一次
        # 这里简化处理：每经过 60秒，衰减系数生效一次
        # decay_steps = elapsed / 60.0
        # 实际上，我们可以使用连续衰减公式: New = Old * (Factor ^ Steps)
        
        # 假设半衰期为 5 分钟 (300秒)，即 300秒后情绪减半
        # Factor ^ 300 = 0.5  => Factor = 0.5 ^ (1/300) ≈ 0.9977
        
        decay_factor_per_sec = 0.998
        total_factor = math.pow(decay_factor_per_sec, elapsed)
        
        self.states[stream_id].decay(total_factor)
        self.last_update_time[stream_id] = current_time

# 全局单例
emotion_manager = EmotionManager()
