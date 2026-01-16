import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
import toml

# ================= 配置 =================
# 尝试自动从配置文件读取
try:
    config_path = os.path.join(os.path.dirname(__file__), "config", "bot_config.toml")
    config = toml.load(config_path)
    # tts_config = config.get("plugins", {}).get("tts_plugin", {}).get("cosyvoice", {})
    tts_config = config.get("voice", {}).get("cosyvoice", {})
    
    API_KEY = tts_config.get("api_key", "")
    VOICE_ID = tts_config.get("voice_id", "")
    # VOICE_ID = "longxiaochun" # Test standard voice
    # MODEL = tts_config.get("model", "cosyvoice-v1")
    MODEL = "cosyvoice-v3-flash"

except Exception as e:
    print(f"❌ 读取配置文件失败: {e}")
    API_KEY = ""
    VOICE_ID = ""
    MODEL = "cosyvoice-v1"

# =======================================

def test_tts():
    if not API_KEY or not VOICE_ID:
        print("❌ API Key 或 Voice ID 未找到，请检查 config/bot_config.toml")
        return

    dashscope.api_key = API_KEY
    
    text = "你好，我是月璃。这是我的新声音，你喜欢吗？"
    print(f"🚀 开始生成语音...")
    print(f"文本: {text}")
    print(f"模型: {MODEL}")
    print(f"音色ID: {VOICE_ID}")

    try:
        synthesizer = SpeechSynthesizer(model=MODEL, voice=VOICE_ID)
        audio = synthesizer.call(text)
        
        # 修正：synthesizer.call 返回的是 result，需要检查 get_audio_data()
        # 但是 dashscope 文档中，SpeechSynthesizer.call 返回的可能是 bytes (如果 stream=False?)
        # 实际上 DashScope Python SDK 的 SpeechSynthesizer.call 返回的是 Result 对象
        # 但是错误提示 'bytes' object has no attribute 'get_audio_data'
        # 说明 synthesizer.call(text) 直接返回了 bytes 数据 (音频流)
        
        if isinstance(audio, bytes):
             with open("test_output.mp3", 'wb') as f:
                f.write(audio)
             print(f"\n🎉 生成成功！音频已保存为: test_output.mp3")
             print("请在文件列表中找到并播放该文件以确认效果。")
        elif hasattr(audio, 'get_audio_data') and audio.get_audio_data():
            output_file = "test_output.mp3"
            with open(output_file, 'wb') as f:
                f.write(audio.get_audio_data())
            print(f"\n🎉 生成成功！音频已保存为: {output_file}")
            print("请在文件列表中找到并播放该文件以确认效果。")
        else:
            print(f"❌ 生成失败，未返回音频数据。")
            print(f"详情: {audio}")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    test_tts()
