import speech_recognition as sr

MIC_INDEX = 0   # use the one that opened successfully

r = sr.Recognizer()
with sr.Microphone(device_index=MIC_INDEX) as source:
    print(f"Using mic #{MIC_INDEX}: {sr.Microphone.list_microphone_names()[MIC_INDEX]}")
    print("Calibrating for ambient noise…")
    r.adjust_for_ambient_noise(source, duration=1)
    print("Say something now…")
    audio = r.listen(source, timeout=10, phrase_time_limit=5)

try:
    print("✅ You said:", r.recognize_google(audio))
except Exception as e:
    print("❌ Recognition error:", e)
