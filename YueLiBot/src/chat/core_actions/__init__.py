from src.plugin_system.core.component_registry import component_registry
from .vtb_motion_action import VTBMotionAction
from src.common.logger import get_logger

logger = get_logger("core_actions")

def register_core_actions():
    """注册系统核心动作"""
    logger.info("正在注册系统核心动作...")
    
    actions = [
        VTBMotionAction
    ]
    
    count = 0
    for action_cls in actions:
        info = action_cls.get_info()
        if component_registry.register_component(info, action_cls):
            count += 1
            
    logger.info(f"系统核心动作注册完成: {count} 个")
