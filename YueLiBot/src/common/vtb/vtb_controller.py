import pyautogui
from enum import Enum
from typing import Dict, List, Optional
from src.common.logger import get_logger

logger = get_logger("vtb_controller")

# 将 pyautogui 的安全模式设为 False 以允许连续输入，
# 但如果可能的话，保留默认的故障安全机制（鼠标移至角落）。
pyautogui.FAILSAFE = False

class VTBActionType(Enum):
    EXPRESSION = "expression"
    TOGGLE = "toggle"
    POSE = "pose"
    SYSTEM = "system"

class VTBActionConfig:
    def __init__(self, name: str, type: VTBActionType, keys: List[str]):
        self.name = name
        self.type = type
        self.keys = keys

# 基于用户图片定义的映射
VTB_ACTIONS: Dict[str, VTBActionConfig] = {
    # 系统
    "flying_head": VTBActionConfig("飞头", VTBActionType.SYSTEM, ["shift", "1"]),
    "shrink": VTBActionConfig("变小", VTBActionType.SYSTEM, ["shift", "2"]),

    # 表情
    "tongue_out": VTBActionConfig("吐舌", VTBActionType.EXPRESSION, ["ctrl", "0"]),
    "angry": VTBActionConfig("生气", VTBActionType.EXPRESSION, ["num1"]),
    "speechless": VTBActionConfig("无语", VTBActionType.EXPRESSION, ["num2"]),
    "sleepy": VTBActionConfig("ZZZ", VTBActionType.EXPRESSION, ["num3"]),
    "dark_face": VTBActionConfig("脸黑", VTBActionType.EXPRESSION, ["num4"]),
    "blush": VTBActionConfig("脸红", VTBActionType.EXPRESSION, ["num5"]),
    "dizziness": VTBActionConfig("眩晕", VTBActionType.EXPRESSION, ["num6"]),
    "crying": VTBActionConfig("流泪", VTBActionType.EXPRESSION, ["num7"]),
    "star_eyes": VTBActionConfig("星星眼", VTBActionType.EXPRESSION, ["num8"]),
    "heart_eyes": VTBActionConfig("爱心眼", VTBActionType.EXPRESSION, ["num9"]),
    "black_eyes": VTBActionConfig("黑眼", VTBActionType.EXPRESSION, ["ctrl", "1"]),
    "white_eyes": VTBActionConfig("白眼", VTBActionType.EXPRESSION, ["ctrl", "2"]),

    # 切换/饰品
    "shark_tail": VTBActionConfig("鲨鱼尾巴", VTBActionType.TOGGLE, ["ctrl", "3"]),
    "jellyfish": VTBActionConfig("水母", VTBActionType.TOGGLE, ["ctrl", "4"]),
    "ears_gone": VTBActionConfig("兽耳消失", VTBActionType.TOGGLE, ["ctrl", "5"]),
    "hair_gone": VTBActionConfig("碎发消失", VTBActionType.TOGGLE, ["ctrl", "6"]),
    "skirt_gone": VTBActionConfig("后裙摆消失", VTBActionType.TOGGLE, ["ctrl", "7"]),
    "upper_teeth_gone": VTBActionConfig("上牙消失", VTBActionType.TOGGLE, ["ctrl", "8"]),
    "moon_hairclip": VTBActionConfig("月亮发夹", VTBActionType.TOGGLE, ["tab", "1"]),
    "shark_hairclip": VTBActionConfig("鲨鱼发夹", VTBActionType.TOGGLE, ["tab", "2"]),
    "pearl_hairclip": VTBActionConfig("珍珠发夹", VTBActionType.TOGGLE, ["tab", "3"]),
    "normal_hairclip": VTBActionConfig("普通发夹", VTBActionType.TOGGLE, ["tab", "4"]),
    "shark_upper_teeth": VTBActionConfig("鲨鱼上牙", VTBActionType.TOGGLE, ["tab", "5"]),
    "halo": VTBActionConfig("头顶光环", VTBActionType.TOGGLE, ["tab", "6"]),
    "front_hair_length": VTBActionConfig("前发长度", VTBActionType.TOGGLE, ["q", "1"]),

    # 动作/姿势
    "holding_star": VTBActionConfig("手捧星", VTBActionType.POSE, ["shift", "3"]),
    "finger_heart": VTBActionConfig("比心", VTBActionType.POSE, ["shift", "4"]),
    "clutching_chest": VTBActionConfig("捂胸口", VTBActionType.POSE, ["shift", "5"]),
    "praying": VTBActionConfig("祈祷", VTBActionType.POSE, ["shift", "6"]),
    "game_console": VTBActionConfig("游戏机", VTBActionType.POSE, ["q", "2"]),
    "microphone": VTBActionConfig("麦克风", VTBActionType.POSE, ["q", "3"]),
    "leaning_forward": VTBActionConfig("前倾", VTBActionType.POSE, ["q", "4"]),
}

class VTBController:
    """通过模拟键盘控制 VTube Studio 动作"""
    
    @staticmethod
    def trigger_action(action_key: str) -> bool:
        """
        通过键名触发动作 (例如 'angry', 'shark_tail')
        """
        config = VTB_ACTIONS.get(action_key)
        if not config:
            logger.warning(f"未知的 VTB 动作: {action_key}")
            return False
            
        try:
            logger.info(f"触发 VTB 动作: {config.name} ({action_key}) 按键: {config.keys}")
            if len(config.keys) == 1:
                pyautogui.press(config.keys[0])
            else:
                pyautogui.hotkey(*config.keys)
            return True
        except Exception as e:
            logger.error(f"触发 VTB 动作失败 {action_key}: {e}")
            return False

    @staticmethod
    def get_available_actions() -> Dict[str, str]:
        """返回 action_key: action_name 的字典，供 LLM 使用"""
        return {k: v.name for k, v in VTB_ACTIONS.items()}

vtb_controller = VTBController()
