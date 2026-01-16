import random
from typing import Dict, List, Tuple, Optional
from src.common.logger import get_logger
from src.common.emotion.emotion_manager import emotion_manager, EmotionState
from src.common.vtb.vtb_controller import vtb_controller

logger = get_logger("vtb_decision_engine")

class VTBActionDecisionEngine:
    """
    VTB 动作决策引擎
    基于 文本语义掩码 (Semantic Mask) + 长期情绪状态 (Emotion State) 进行双流决策
    """
    
    def __init__(self):
        # 定义动作的属性：基础情绪特征、冲突情绪、所需关系阈值(0-100)
        # 格式: ActionKey: { "base_emotion": {emo: weight}, "conflict": [emo], "min_intimacy": int }
        self.action_metadata = {
            "angry": {"base_emotion": {"anger": 0.8}, "conflict": ["joy", "love"], "min_intimacy": 0},
            "blush": {"base_emotion": {"joy": 0.3, "fear": 0.2}, "conflict": ["anger"], "min_intimacy": 30},
            "happy": {"base_emotion": {"joy": 0.8}, "conflict": ["anger", "sorrow"], "min_intimacy": 0},
            "singing": {"base_emotion": {"joy": 0.5}, "conflict": ["sorrow", "fear"], "min_intimacy": 0},
            "gaming": {"base_emotion": {"joy": 0.4, "neutral": 0.5}, "conflict": ["anger"], "min_intimacy": 0},
            "crying": {"base_emotion": {"sorrow": 0.9}, "conflict": ["joy"], "min_intimacy": 0},
            "stunned": {"base_emotion": {"surprise": 0.8, "fear": 0.2}, "conflict": [], "min_intimacy": 0},
            "speechless": {"base_emotion": {"neutral": 0.5, "anger": 0.2}, "conflict": ["joy"], "min_intimacy": 0},
            "sleepy": {"base_emotion": {"neutral": 0.8}, "conflict": ["anger", "fear", "surprise"], "min_intimacy": 0},
            "dark_face": {"base_emotion": {"anger": 0.9}, "conflict": ["joy"], "min_intimacy": 0},
            "tongue_out": {"base_emotion": {"joy": 0.6}, "conflict": ["anger", "sorrow"], "min_intimacy": 20},
            "heart_eyes": {"base_emotion": {"joy": 0.9, "love": 1.0}, "conflict": ["anger", "sorrow", "fear"], "min_intimacy": 50},
            "star_eyes": {"base_emotion": {"joy": 0.8, "surprise": 0.3}, "conflict": ["sorrow"], "min_intimacy": 0},
            "holding_star": {"base_emotion": {"joy": 0.5}, "conflict": ["anger"], "min_intimacy": 10},
            "finger_heart": {"base_emotion": {"joy": 0.7, "love": 0.8}, "conflict": ["anger", "sorrow"], "min_intimacy": 60},
            "clutching_chest": {"base_emotion": {"surprise": 0.4, "fear": 0.3, "joy": 0.3}, "conflict": [], "min_intimacy": 0},
            "praying": {"base_emotion": {"neutral": 0.5, "fear": 0.2}, "conflict": ["anger"], "min_intimacy": 0},
            "leaning_forward": {"base_emotion": {"neutral": 0.5, "joy": 0.3}, "conflict": [], "min_intimacy": 0},
            # 默认兜底
            "neutral": {"base_emotion": {"neutral": 1.0}, "conflict": [], "min_intimacy": 0},
        }

    async def decide_action(self, stream_id: str, intent_motion: Optional[str], reply_text: str) -> Tuple[Optional[str], str]:
        """
        核心决策函数
        
        Args:
            stream_id: 会话ID
            intent_motion: LLM 原始建议的动作 (可能为空)
            reply_text: 当前回复的文本内容
            
        Returns:
            (FinalActionKey, DecisionReason)
        """
        # 1. 获取长期状态
        emotion_state = emotion_manager.get_state(stream_id)
        # TODO: 从 PersonInfo 获取 Intimacy，暂时 Mock 为 50 (普通朋友)
        current_intimacy = 50 
        
        # 2. 文本语义特征提取 (Semantic Masking)
        # 简单实现：基于关键词的情感极性判断
        text_sentiment = self._analyze_text_sentiment_simple(reply_text)
        
        # [Self-Loop] 根据自己的发言内容更新情绪状态
        # 简单的言语行为反馈：说出积极的话会增强积极情绪，反之亦然
        if text_sentiment["intensity"] > 0:
            delta = {}
            if text_sentiment["positive"] > 0:
                delta["joy"] = text_sentiment["positive"] * 0.5
            if text_sentiment["negative"] > 0:
                delta["anger"] = text_sentiment["negative"] * 0.5
            
            if delta:
                emotion_manager.update_state(stream_id, delta)
                logger.debug(f"Emotion updated by text: {delta}")

        # 3. 生成候选动作池
        candidates = self._generate_candidates(intent_motion, emotion_state, text_sentiment)
        
        if not candidates:
            return None, "无有效候选动作"
            
        # 4. 加权打分
        scored_actions = []
        for action in candidates:
            score, reason_parts = self._calculate_utility(action, emotion_state, current_intimacy, text_sentiment)
            scored_actions.append((action, score, reason_parts))
            
        # 按分数排序
        scored_actions.sort(key=lambda x: x[1], reverse=True)
        
        # 5. 决策输出 (Top-1 加上一定的随机性，或者直接 Top-1)
        # 这里使用简单的 Top-1
        best_action, best_score, best_reasons = scored_actions[0]
        
        reason_str = f"Score: {best_score:.2f} [{', '.join(best_reasons)}]"
        return best_action, reason_str

    def _analyze_text_sentiment_simple(self, text: str) -> Dict[str, float]:
        """简单文本情感分析 (Mock)"""
        sentiment = {"positive": 0.0, "negative": 0.0, "intensity": 0.0}
        
        pos_keywords = ["哈哈", "喜欢", "爱", "开心", "棒", "好", "嘿嘿", "嘻嘻"]
        neg_keywords = ["哼", "讨厌", "滚", "不理你", "生气", "烦", "死", "笨蛋"]
        
        for k in pos_keywords:
            if k in text:
                sentiment["positive"] += 0.3
        
        for k in neg_keywords:
            if k in text:
                sentiment["negative"] += 0.4 # 负面词权重稍大
                
        sentiment["intensity"] = min(1.0, sentiment["positive"] + sentiment["negative"])
        return sentiment

    def _generate_candidates(self, intent_motion: Optional[str], state: EmotionState, text_sentiment: Dict[str, float]) -> List[str]:
        """生成候选动作，并执行掩码过滤"""
        available_actions = list(self.action_metadata.keys())
        candidates = []
        
        # 如果 LLM 指定了动作，优先考虑它，但也要经过掩码检查
        # 如果没指定，考虑所有动作
        
        for action in available_actions:
            meta = self.action_metadata.get(action, {})
            
            # --- Masking Logic ---
            
            # 1. 文本极性冲突掩码
            # 如果文本极度负面，禁止极度正面的动作
            if text_sentiment["negative"] > 0.5 and "joy" in meta.get("base_emotion", {}):
                # 特例：如果是嘲讽 (mocking)，可能需要 Joy，这里简化处理先过滤
                continue
            
            # 如果文本极度正面，禁止负面动作
            if text_sentiment["positive"] > 0.5 and "anger" in meta.get("base_emotion", {}):
                # 除非是“打是亲骂是爱”的娇嗔，需要更复杂的 NLP，这里简化
                continue

            candidates.append(action)
            
        # 如果 LLM 指定的动作在候选池里，为了尊重 LLM，我们可以额外加权或确保它在列表前列
        # 但这里我们让它参与公平竞争，只是给予基础分加成
        
        return candidates

    def _calculate_utility(self, action: str, state: EmotionState, intimacy: int, text_sentiment: Dict[str, float]) -> Tuple[float, List[str]]:
        """计算单个动作的效用分"""
        meta = self.action_metadata.get(action, {})
        score = 0.0
        reasons = []
        
        # 1. 基础分 (Base)
        score += 10.0
        
        # 2. 情绪共鸣 (Emotion Resonance)
        # 计算当前情绪状态与动作特征的点积
        emo_score = 0.0
        state_dict = state.to_dict()
        base_emotions = meta.get("base_emotion", {})
        
        for emo, weight in base_emotions.items():
            # 这里的 logic: 如果当前状态中有这个情绪，且动作也表现这个情绪 -> 加分
            # state_dict.get(emo, 0) 是当前情绪值 (0-1)
            # weight 是动作的情绪浓度 (0-1)
            if emo == "love": # 特殊处理 love，映射到 joy 或 intimacy
                 val = state_dict.get("joy", 0) * 0.8
            else:
                 val = state_dict.get(emo, 0)
            
            emo_score += val * weight * 50.0 # 权重系数 50
            
        if emo_score > 0:
            score += emo_score
            reasons.append(f"EmoRes(+{emo_score:.1f})")
            
        # 3. 关系修正 (Relationship Bonus/Penalty)
        req_intimacy = meta.get("min_intimacy", 0)
        if intimacy < req_intimacy:
            # 亲密度不足，大幅扣分 (Soft Constraint)
            penalty = (req_intimacy - intimacy) * 2.0
            score -= penalty
            reasons.append(f"IntimacyLow(-{penalty:.1f})")
        elif intimacy >= req_intimacy + 30:
            # 亲密度远超需求，小幅加分
            score += 10.0
            reasons.append("IntimacyBonus")

        # 4. 文本情感匹配 (Text Match)
        # 简单的 heuristic
        if text_sentiment["positive"] > 0.3 and "joy" in base_emotions:
            score += 20.0
            reasons.append("TextPosMatch")
        if text_sentiment["negative"] > 0.3 and "anger" in base_emotions:
            score += 20.0
            reasons.append("TextNegMatch")
            
        return score, reasons

decision_engine = VTBActionDecisionEngine()
