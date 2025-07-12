import os
import time
from dotenv import load_dotenv

# ─── Configuration ─────────────────────────────────────────────────────────────
EXIT_KEYWORDS = ("exit", "quit", "goodbye")

# ─── Initialization ────────────────────────────────────────────────────────────
def initialize():
    # 1) Load env early
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

    # 2) Create the WakeDetector now (lightweight)
    from jarvis_wake import WakeDetector
    wake = WakeDetector(keyword="jarvis", sensitivity=0.2)

    # 3) Open the Porcupine stream once
    wake.open_stream()

    return wake

# ─── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    wake = initialize()

    # Delay heavy imports until after the audio stream is live
    from jarvis_core import greet_on_startup, speak, listen, handle_command
    from jarvis_llm import chat_with_ai

    # Calibrate noise quickly (200 ms)
    from speech_recognition import Recognizer, Microphone
    recognizer = Recognizer()
    mic = Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.2)

    # Greet
    greet_on_startup()
    speak("I am Jarvis. How can I assist you today?")

    # 4) Wait/wake/session loop
    while True:
        wake.wait_for_wake()  # stream already open, super fast
        speak("How can I help you?")
        cmd = listen(timeout=6, phrase_time_limit=10) or ""
        cmd = cmd.lower().strip()

        if any(k in cmd for k in EXIT_KEYWORDS):
            speak("Goodbye!")
            continue

        if not cmd:
            speak("Please try again and say 'Jarvis' to wake me.")
            continue

        if handle_command(cmd):
            continue

        if cmd.split()[0] in ("hi", "hello", "hey", "how"):
            reply = chat_with_ai(cmd)
            speak(reply)
            continue

        speak("Sorry, I didn’t understand. Say 'Jarvis' to wake me again.")

if __name__ == "__main__":
    start = time.perf_counter()
    main()
