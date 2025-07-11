from dotenv import load_dotenv
load_dotenv(override=True)

from jarvis_wake import WakeDetector
from jarvis_core import (
    speak, listen, handle_command,
    chat_with_ai, greet_on_startup
)

if __name__ == "__main__":

    wake = WakeDetector(keyword="jarvis")
    greet_on_startup()
    speak("I am Jarvis. How can I assist you today?")

    while True:
        # 1) Wait for the wake word
        if not wake.wait_for_wake():
            continue

        # 2) Prompt and listen
        speak("How can I help you?")
        cmd = listen(timeout=8, phrase_time_limit=12)
        if not cmd:
            speak("Please try again and say 'jarvis' to wake me.")
            continue

        # 3) Built-in commands
        if handle_command(cmd):
            continue

        # 4) Small-talk via LLM
        if cmd.lower().split()[0] in ("hi", "hello", "hey", "how"):
            reply = chat_with_ai(cmd)
            speak(reply)
            continue

        # 5) Nothing matched → retry
        speak("Sorry, I didn’t understand that. Please say 'jarvis' to wake me and try again.")
        # loop back to waiting for wake-word
        continue
