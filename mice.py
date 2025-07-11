import speech_recognition as sr

names = sr.Microphone.list_microphone_names()
print("Available devices:")
for i, n in enumerate(names):
    print(f"{i:2d}: {n}")

print("\nTesting each index…")
for idx in range(len(names)):
    try:
        with sr.Microphone(device_index=idx) as source:
            print(f"✅ Index {idx} opened: {names[idx]}")
            break
    except Exception as e:
        print(f"❌ Index {idx} failed: {e.__class__.__name__}: {e}")
else:
    print("😞 No index worked.")
