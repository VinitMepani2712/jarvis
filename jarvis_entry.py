import os
from dotenv import load_dotenv

# Load .env from project root (.. relative to this file)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from jarvis_llm import chat_with_ai
from jarvis_wake import WakeDetector
from jarvis_core import handle_command, speak, listen, greet_on_startup, init_audio

EXIT_KEYWORDS = ("exit", "quit", "goodbye")

def _get_wakeword():
    # Prefer WAKEWORD from .env, fall back to "jarvis"
    return os.getenv("WAKEWORD", "jarvis").strip().lower() or "jarvis"

if __name__ == "__main__":
    # Calibrate mic once (moved out of import-time side effects)
    init_audio()

    # Build exactly one WakeDetector here
    # If you're using a custom .ppn for the "jarvis" hotword, set JARVIS_PPN in .env
    # Example:
    #   JARVIS_PPN=V:\Vinit\jarvis\resources\jarvis_en_windows.ppn
    wake = WakeDetector(keyword=_get_wakeword())

    greet_on_startup()
    speak("I am Jarvis. How can I assist you today?")

    while True:
        # 1) Wait for the wake word
        if not wake.wait_for_wake():
            continue

        # 2) Prompt and listen
        speak("How can I help you?")
        cmd = listen(timeout=8, phrase_time_limit=12) or ""
        cmd = cmd.lower().strip()
        if not cmd:
            speak("Please try again and say 'jarvis' to wake me.")
            continue

        # 2a) Exit command → go back to waiting for wake-word
        if any(k in cmd for k in EXIT_KEYWORDS):
            speak("Goodbye!")
            continue

        # 3) Built-in commands
        if handle_command(cmd):
            continue

        # 4) Small-talk via LLM
        if cmd.split()[0] in ("hi", "hello", "hey", "how"):
            reply = chat_with_ai(cmd)
            speak(reply)
            continue

        # 5) Nothing matched → retry
        speak("Sorry, I didn’t understand that. Please say 'jarvis' to wake me and try again.")
