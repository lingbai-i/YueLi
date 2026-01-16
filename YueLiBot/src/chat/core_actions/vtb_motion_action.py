from typing import Dict, Any, Tuple
from src.plugin_system.base.base_action import BaseAction
from src.plugin_system.base.component_types import ActionInfo, ComponentType
from src.common.vtb.vtb_controller import vtb_controller
from src.common.logger import get_logger
from src.common.emotion.decision_engine import decision_engine

logger = get_logger("vtb_motion_action")

class VTBMotionAction(BaseAction):
    """
    VTB动作执行器 (Core Action)
    """
    
    # 静态元数据定义 (模拟插件 Manifest)
    action_name = "vtb_motion"
    action_description = "执行VTB虚拟形象的动作。支持动作参数(motion)包括: angry(生气), blush(脸红), happy(爱心眼), singing(麦克风), gaming(游戏机), crying(流泪), stunned(眩晕), speechless(无语), sleepy(ZZZ), dark_face(脸黑), tongue_out(吐舌), heart_eyes(爱心眼), star_eyes(星星眼), holding_star(手捧星), finger_heart(比心), clutching_chest(捂胸口), praying(祈祷), leaning_forward(前倾). 当你需要表达强烈情绪或进行特定活动(如唱歌、玩游戏)时使用此动作。"
    
    async def execute(self) -> Tuple[bool, str]:
        """
        执行VTB动作
        
        预期 action_data:
        {
            "motion": "angry"  # VTB_ACTIONS 中的键名
        }
        """
        motion_key = self.action_data.get("motion")
        # 注意: 即使没有 motion_key，决策引擎也可以根据情绪自动推荐动作
        
        # --- Emotion Decision Engine Integration ---
        # 使用决策引擎根据 当前情绪 + 回复文本 + 意图动作 进行综合决策
        # 目前 reply_text 暂时传空字符串，后续如果能获取到 reply action 的内容再传入
        stream_id = self.chat_id
        reply_text = "" 
        
        final_motion, reason = await decision_engine.decide_action(stream_id, motion_key, reply_text)
        
        if final_motion:
            if final_motion != motion_key:
                logger.info(f"{self.log_prefix} [VTB决策] 动作已修正: '{motion_key}' -> '{final_motion}' | 原因: {reason}")
            else:
                logger.debug(f"{self.log_prefix} [VTB决策] 动作维持不变: '{motion_key}' | 原因: {reason}")
            motion_key = final_motion
        else:
            if motion_key:
                logger.warning(f"{self.log_prefix} [VTB决策] 引擎未返回有效动作，尝试执行原始意图: '{motion_key}' | 原因: {reason}")
            else:
                return False, f"未指定动作且决策引擎无推荐 (原因: {reason})"

        if not motion_key:
            return False, "未指定动作名称 (motion)"
            
        # 如果找不到键，尝试通过名称查找（模糊匹配或直接名称匹配）
        target_key = motion_key
        available_actions = vtb_controller.get_available_actions()
        
        if motion_key not in available_actions:
            # 尝试通过值（中文名称）或英文键别名查找
            found = False
            
            # 如果需要，将常见的 LLM 意图映射到键
            aliases = {
                "singing": "microphone",
                "gaming": "game_console",
                "happy": "heart_eyes",
                "stunned": "dizziness",
                "shy": "blush",
                "cry": "crying",
                "sad": "crying"
            }
            if motion_key in aliases:
                target_key = aliases[motion_key]
                found = True
            
            if not found:
                for k, name in available_actions.items():
                    if name == motion_key:
                        target_key = k
                        found = True
                        break
            
            if not found:
                 # 尝试不区分大小写匹配
                 for k in available_actions.keys():
                     if k.lower() == motion_key.lower():
                         target_key = k
                         found = True
                         break
                         
            if not found:
                 return False, f"未知的动作: {motion_key}. 可用动作: {', '.join(available_actions.keys())}"
        
        success = vtb_controller.trigger_action(target_key)
        
        if success:
            action_name = available_actions.get(target_key, target_key)
            logger.info(f"{self.log_prefix} 核心动作 VTB Motion 执行成功: {action_name}")
            return True, f"已执行VTB动作: {action_name}"
        else:
            return False, f"执行VTB动作失败: {motion_key}"

    @classmethod
    def get_info(cls) -> ActionInfo:
        """获取动作注册信息"""
        return ActionInfo(
            name=cls.action_name,
            description=cls.action_description,
            component_type=ComponentType.ACTION,
            enabled=True,
            plugin_name="system_core"  # 标识为系统核心组件
        )
