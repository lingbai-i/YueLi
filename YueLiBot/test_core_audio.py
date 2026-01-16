import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.common.audio.audio_manager import AudioManager
from src.config.config import global_config

async def test_audio():
    print("Initializing AudioManager...")
    manager = AudioManager()
    
    # Mock config if needed (but we updated the file so it should load)
    print(f"Output Device: {manager.output_device_name}")
    
    text = "我现在开始循环播放测试语音，方便你调试 VTube Studio 的设置。请尝试调整增益，或者点击‘在模型中进行准备’按钮。一二三，一二三，能看到嘴巴动吗？"
    
    print("开始循环播放测试语音（按 Ctrl+C 停止）...")
    print("请切换到 VTube Studio 进行调试：")
    print("1. 观察右侧绿色音量条是否跳动。")
    print("2. 点击下方的【在模型中进行准备】按钮。")
    print("3. 尝试调整【音频增益】。")
    
    while True:
        print(f"Synthesizing: {text[:10]}...")
        await manager.speak(text)
        await asyncio.sleep(15) # 等待播放完成及一点间隔
    
    print("Waiting for playback...")
    while manager.audio_queue.qsize() > 0 or manager.is_playing:
        await asyncio.sleep(1)
        print(".", end="", flush=True)
    
    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(test_audio())
