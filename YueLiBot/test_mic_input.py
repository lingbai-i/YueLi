import soundcard as sc
import numpy as np
import time

def test_recording():
    print("=== 麦克风输入测试 ===")
    
    # 1. 查找设备
    target_name = 'CABLE Output'
    mic = None
    
    try:
        mics = sc.all_microphones()
        print(f"系统检测到 {len(mics)} 个输入设备:")
        for m in mics:
            print(f" - {m.name}")
            if target_name.lower() in m.name.lower():
                mic = m
    except Exception as e:
        print(f"❌ 获取设备列表失败: {e}")
        return

    if not mic:
        print(f"\n❌ 未在 Python 中找到 '{target_name}'。驱动可能未正确加载。")
        return

    print(f"\n✅ Python 已找到设备: {mic.name}")
    
    # 2. 尝试录音 (检测权限和独占状态)
    print("正在尝试访问设备进行 1 秒录音测试...")
    try:
        # 录制 1 秒
        # SoundCard 0.4.5 issue with numpy 2.0: The binary mode of fromstring is removed
        # We need to monkey patch it or downgrade numpy, or wait for fix
        # But wait, soundcard internally uses fromstring?
        # Let's try to monkey patch numpy temporarily if possible, or just catch the error and explain.
        
        # Actually, let's try to use raw stream if recorder fails
        import warnings
        warnings.filterwarnings("ignore")
        
        # Monkey patch for soundcard + numpy 2.x
        # numpy 2.0 removed fromstring for binary data
        # soundcard uses it internally
        import numpy
        if not hasattr(numpy, 'fromstring') or True: # Force patch
            def _fromstring_patch(string, dtype=float, count=-1, sep=''):
                if sep == '':
                    return numpy.frombuffer(string, dtype=dtype, count=count)
                # Fallback for actual string parsing if needed (unlikely for audio data)
                # But soundcard uses it for bytes
                return numpy.frombuffer(string, dtype=dtype, count=count)
            
            numpy.fromstring = _fromstring_patch

        with mic.recorder(samplerate=44100) as recorder:
            data = recorder.record(numframes=44100)
            
        max_amp = np.max(np.abs(data))
        print(f"✅ 录音成功！设备访问正常。")
        print(f"   最大振幅: {max_amp:.4f} (如果为0说明全是静音，但设备是可用的)")
        
        print("\n结论: 系统层面设备工作正常，Python 可以访问。")
        print("推测问题出在 VTube Studio 软件本身或其权限设置上。")
        
    except Exception as e:
        print(f"\n❌ 录音失败: {e}")
        print("可能原因:")
        print("1. Windows 麦克风隐私设置禁止了访问。")
        print("2. 设备被其他程序独占。")
        print("3. 驱动程序异常。")

if __name__ == "__main__":
    test_recording()
