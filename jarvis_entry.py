import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from jarvis_llm import chat_with_ai
from jarvis_wake import WakeDetector
from jarvis_core import handle_command, speak, listen, greet_on_startup

EXIT_KEYWORDS = ("exit", "quit", "goodbye")

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
        cmd = listen(timeout=8, phrase_time_limit=12) or ""
        cmd = cmd.lower().strip()
        if not cmd:
            speak("Please try again and say 'jarvis' to wake me.")
            continue

        # 2a) Exit command → go back to waiting for wake-word
        if any(k in cmd for k in EXIT_KEYWORDS):
            speak("Goodbye!")
            # don’t sys.exit(); just drop back to outer loop
            continue

        if handle_command(cmd):
            continue

        if cmd.split()[0] in ("hi", "hello", "hey", "how"):
            reply = chat_with_ai(cmd)
            speak(reply)
            continue

        speak("Sorry, I didn’t understand that. Please say 'jarvis' to wake me and try again.")
