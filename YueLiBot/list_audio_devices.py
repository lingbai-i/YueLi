import soundcard as sc

def list_devices():
    print("--- Output Devices ---")
    try:
        speakers = sc.all_speakers()
        for i, s in enumerate(speakers):
            print(f"{i}: {s.name}")
    except Exception as e:
        print(f"Error listing output devices: {e}")

    print("\n--- Input Devices ---")
    try:
        mics = sc.all_microphones()
        for i, m in enumerate(mics):
            print(f"{i}: {m.name}")
    except Exception as e:
        print(f"Error listing input devices: {e}")

if __name__ == "__main__":
    list_devices()
