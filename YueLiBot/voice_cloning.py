import os
import time
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService

# ================= 配置区域 =================

# 1. API Key
# 尝试从配置文件读取，如果读取失败，请手动在此处填入
API_KEY = "" 
try:
    import toml
    config_path = os.path.join(os.path.dirname(__file__), "config", "bot_config.toml")
    config = toml.load(config_path)
    API_KEY = config.get("plugins", {}).get("tts_plugin", {}).get("cosyvoice", {}).get("api_key", "")
except:
    pass

# 2. 音频文件的公网 URL (必须修改！)
# ❌ 不支持本地路径 (如 d:/xxx.wav)
# ✅ 必须是 http:// 或 https:// 开头的链接
# 示例: "https://github.com/yourname/repo/raw/main/my_voice.wav"
AUDIO_URL = "https://gitee.com/lingbaiiii/yue-li-moon-glass/raw/main/TTS/kelala/kelala.wav" 

# 3. 目标模型
# 可选: "cosyvoice-v1" (标准), "cosyvoice-v3-plus" (高品质)
TARGET_MODEL = "cosyvoice-v3-flash"

# 4. 音色前缀
VOICE_PREFIX = "YueLi"

# ===========================================

def clone_voice():
    # 检查 Key
    if API_KEY:
        dashscope.api_key = API_KEY
        print(f"✅ 已加载 API Key: {API_KEY[:6]}******")
    else:
        print("❌ 未找到 API Key，请在脚本或 config/bot_config.toml 中配置。")
        return

    # 检查 URL
    if not AUDIO_URL.startswith("http"):
        print("\n⚠️  错误：AUDIO_URL 未配置或格式不正确！")
        print("------------------------------------------------")
        print("阿里云要求音频必须是公网可访问的 URL。")
        print("请将 'kelala.wav' 上传到 GitHub/OSS/图床，获取直链后填入脚本第 23 行。")
        print("------------------------------------------------")
        return

    print(f"\n🚀 开始创建音色复刻任务...")
    print(f"模型: {TARGET_MODEL}")
    print(f"音频: {AUDIO_URL}")

    service = VoiceEnrollmentService()
    try:
        # 提交任务
        voice_id = service.create_voice(
            target_model=TARGET_MODEL,
            prefix=VOICE_PREFIX,
            url=AUDIO_URL
        )
        print(f"✅ 任务提交成功! Voice ID: {voice_id}")
        
        # 轮询状态
        print("⏳ 正在等待云端处理 (约 5-10 秒)...")
        for i in range(30):
            voice_info = service.query_voice(voice_id=voice_id)
            status = voice_info.get("status")
            print(f"   [{i+1}/30] 状态: {status}")
            
            if status == "Open": # 文档中成功状态通常为 Open 或 SUCCESS，视具体版本
                print(f"\n🎉 复刻成功！")
                print(f"请将 config/bot_config.toml 中的 voice_id 修改为:\n{voice_id}")
                return
            elif status == "Fail":
                print("❌ 复刻失败，请检查音频质量或 URL 是否有效。")
                return
            time.sleep(2)
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    clone_voice()
