import ctypes
import glob as _glob
import os
import re
import sys
import webbrowser
import shutil
import subprocess
import socket
import platform
import random
import time
import struct
from threading import Event

import cv2
import mss
import numpy as np
import psutil
import pvporcupine
import pyautogui
import pygetwindow as gw
import sounddevice as sd
import speech_recognition as sr
from dotenv import load_dotenv
from speech_recognition import RequestError, WaitTimeoutError
from win32com.client import Dispatch

from jarvis_llm import chat_with_ai

# ──────────────────────────────────────────────────────────────────────────────
# Env & Keys
# Load .env from project root (.. relative to this file)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

PV_ACCESS_KEY = (os.getenv("PV_ACCESS_KEY") or "").strip()
WAKEWORD = (os.getenv("WAKEWORD") or "jarvis").strip().lower()
JARVIS_PPN = (os.getenv("JARVIS_PPN") or "").strip()  # absolute path to .ppn if using custom hotword

# ──────────────────────────────────────────────────────────────────────────────
# TTS via Windows SAPI
speaker = Dispatch("SAPI.SpVoice")
speaker.Rate = 0
speaker.Volume = 100

def speak(text: str):
    """Speak text out loud and echo to console."""
    print(f"[Jarvis speaking]: {text}")
    try:
        speaker.Speak(text)
    except Exception as e:
        print(f"[TTS error]: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# STT Setup
recognizer = sr.Recognizer()
mic = sr.Microphone()

def init_audio():
    """Calibrate ambient noise once. MUST be called by your entrypoint before listening."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.1)

def listen(timeout: float = 5, phrase_time_limit: float = 5) -> str:
    """
    Listen on the default mic.
    timeout: seconds to wait for phrase start
    phrase_time_limit: max seconds for the phrase itself
    """
    with mic as source:
        print("[jarvis listening…]")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except WaitTimeoutError:
            speak("I didn't hear anything.")
            return ""

    try:
        text = recognizer.recognize_google(audio)
        print(f"[Recognized]: {text}")
        return text
    except RequestError as e:
        speak(f"Speech service error: {e}")
        return ""
    except sr.UnknownValueError:
        speak("Sorry, I couldn't understand.")
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# Wake Word Detector
_BUILT_INS = {
    "porcupine", "bumblebee", "americano", "blueberry", "terminator",
    "grapefruit", "grasshopper", "picovoice"
    # "jarvis" is not guaranteed; usually requires a custom .ppn
}

class WakeDetector:
    """
    Wake word detector using Porcupine.

    - If `keyword` is a Porcupine built-in (in _BUILT_INS), uses keywords=[keyword].
    - Otherwise, tries a custom .ppn:
        • If `keyword` is an absolute path ending with .ppn, uses that.
        • Else it looks for JARVIS_PPN from .env (absolute path).
    """

    def __init__(self, keyword: str = WAKEWORD, model_path: str | None = None, sensitivity: float = 0.5):
        if not PV_ACCESS_KEY:
            raise RuntimeError(
                "PV_ACCESS_KEY is missing. Add it to your .env:\n"
                "  PV_ACCESS_KEY=pk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
            )

        use_builtin = keyword in _BUILT_INS
        keyword_paths = None

        if not use_builtin:
            # allow absolute path passed directly
            if os.path.isabs(keyword) and keyword.lower().endswith(".ppn"):
                keyword_paths = [keyword]
            else:
                if not JARVIS_PPN:
                    raise RuntimeError(
                        f'The hotword "{keyword}" is not a known built-in. Provide a custom keyword .ppn.\n'
                        "Set JARVIS_PPN in your .env, for example:\n"
                        "  JARVIS_PPN=V:\\Vinit\\jarvis\\jarvis_en_windows.ppn\n"
                        "Or pass an absolute .ppn path as the keyword when creating WakeDetector."
                    )
                if not os.path.isabs(JARVIS_PPN) or not os.path.exists(JARVIS_PPN):
                    raise RuntimeError(f"JARVIS_PPN does not exist or is not absolute: {JARVIS_PPN}")
                keyword_paths = [JARVIS_PPN]

        try:
            if use_builtin:
                self._porcupine = pvporcupine.create(
                    access_key=PV_ACCESS_KEY,
                    keywords=[keyword],
                    sensitivities=[sensitivity],
                    model_path=model_path,
                )
            else:
                self._porcupine = pvporcupine.create(
                    access_key=PV_ACCESS_KEY,
                    keyword_paths=keyword_paths,
                    sensitivities=[sensitivity],
                    model_path=model_path,
                )
        except Exception as e:
            raise RuntimeError(
                "Porcupine init failed.\n"
                f"- Keyword: {keyword}\n"
                f"- Built-in: {use_builtin}\n"
                f"- Model path: {model_path or 'default'}\n"
                "Hints:\n"
                "  • Ensure PV_ACCESS_KEY is valid (no quotes / no spaces) and internet is available on first run.\n"
                "  • If using a custom .ppn, verify the absolute path is correct and for your platform.\n"
                f"Original error: {e}"
            ) from e

        self._stop = Event()

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            # non-fatal audio glitch info
            pass
        # Convert bytes → 16-bit PCM tuple for Porcupine
        pcm = struct.unpack_from("h" * frames, indata.tobytes())
        if self._porcupine.process(pcm) >= 0:
            self._stop.set()

    def wait_for_wake(self) -> bool:
        """Blocks until the wake-word is detected. Returns True if detected; False if stopped."""
        self._stop.clear()
        with sd.InputStream(
            device=None,  # default input
            samplerate=self._porcupine.sample_rate,
            blocksize=self._porcupine.frame_length,
            channels=1,
            dtype="int16",
            callback=self._audio_callback,
        ):
            self._stop.wait()
            return True

    def stop(self):
        self._stop.set()
        try:
            if hasattr(self, "_porcupine") and self._porcupine is not None:
                self._porcupine.delete()
        except Exception:
            pass

# ──────────────────────────────────────────────────────────────────────────────
# Local small-talk data
GREETINGS = ["Hello there!", "Hi!", "Hey!"]
HOW_ARE_YOU = [
    "I'm doing great, thanks! How can I assist you?",
    "All systems go! What can I do for you?"
]
JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "Why did the computer show up late to work? It had a hard drive."
]

def local_small_talk(cmd: str) -> str:
    text = cmd.lower()
    if any(g in text for g in ("hi", "hello", "hey", "good morning", "good afternoon", "good evening")):
        return random.choice(GREETINGS)
    if "how are you" in text or "how's it going" in text:
        return random.choice(HOW_ARE_YOU)
    if "joke" in text or "tell me a joke" in text:
        return random.choice(JOKES)
    return ""

# ──────────────────────────────────────────────────────────────────────────────
# Screen Recording
def record_screen(duration: int, output_file: str, fps: int = 15):
    """Capture the entire virtual desktop for `duration` seconds, with console logs."""
    print(f"[Recorder] Starting capture for {duration}s → {output_file}")
    try:
        with mss.mss() as sct:
            virtual = sct.monitors[0]
            width, height = virtual["width"], virtual["height"]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

            end_time = time.time() + duration
            interval = 1.0 / fps
            frame_count = 0

            while time.time() < end_time:
                start = time.time()
                img = np.array(sct.grab(virtual))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                writer.write(frame)
                frame_count += 1

                # throttle
                elapsed = time.time() - start
                if elapsed < interval:
                    time.sleep(interval - elapsed)

            writer.release()
            print(f"[Recorder] Finished: wrote {frame_count} frames.")
    except Exception as e:
        print(f"[Recorder] ERROR: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# Command Dispatcher
def handle_command(cmd: str) -> bool:
    """
    Returns True if a built-in command handled it;
    False → fall back to LLM.
    """
    cmd = cmd.lower().strip()
    print(f">>> You said: {cmd}")

    # Small-talk
    reply = local_small_talk(cmd)
    if reply:
        speak(reply)
        return True

    # Context-aware typing
    if m := re.match(r"type (.+) on (browser|notepad|word|code)", cmd):
        text, app = m.group(1), m.group(2)
        title_map = {
            "browser": "https://www.google.com",
            "notepad": "Notepad",
            "word": "Microsoft Word",
            "code": "Visual Studio Code"
        }
        title = title_map.get(app)
        if title:
            wins = gw.getWindowsWithTitle(title)
            if wins:
                wins[0].activate(); time.sleep(0.5)
            else:
                subprocess.Popen({
                    'notepad': 'notepad.exe',
                    'word': 'winword.exe',
                    'code': 'code'
                }[app])
                time.sleep(1)
        pyautogui.write(text, interval=0.05)
        speak(f"Typed '{text}' in {app}")
        return True

    if m := re.match(r"type (.+)", cmd):
        text = m.group(1)
        pyautogui.write(text, interval=0.05)
        speak(f"Typed '{text}'")
        return True

    # App control
    if m := re.match(r"(?:open|launch) app (.+)", cmd):
        app = m.group(1).strip()
        speak(f"Opening {app}")
        subprocess.Popen(app.split())
        return True

    if m := re.match(r"close app (.+)", cmd):
        app = m.group(1).strip()
        speak(f"Closing {app}")
        os.system(f"taskkill /im {app}.exe /f")
        return True

    if m := re.match(r"(?:minimize|maximize) window", cmd):
        win = gw.getActiveWindow()
        if win:
            if "minimize" in cmd:
                win.minimize(); speak("Window minimized")
            else:
                win.maximize(); speak("Window maximized")
        return True

    # Browser & Web Search
    if re.match(r"open browser", cmd):
        speak("Opening default browser.")
        webbrowser.open("https://www.google.com")
        return True

    if m := re.match(r"search web for (.+)", cmd):
        q = m.group(1)
        speak(f"Searching the web for {q}")
        webbrowser.open(f"https://www.google.com/search?q={q}")
        return True

    if "recycle bin" in cmd:
        speak("Opening Recycle Bin.")
        subprocess.Popen(["explorer", "shell:RecycleBinFolder"])
        return True

    if "my computer" in cmd or re.match(r"open (?:my )?computer", cmd):
        speak("Opening This PC.")
        subprocess.Popen(["explorer", "shell:MyComputerFolder"])
        return True

    if "open chat" in cmd:
        speak("Opening ChatGPT.")
        webbrowser.open("https://chatgpt.com/")
        return True
    elif "open google" in cmd:
        speak("Opening Google.")
        webbrowser.open("https://google.com/")
        return True
    elif "open insta" in cmd:
        speak("Opening Instagram.")
        webbrowser.open("https://instagram.com/")
        return True
    elif "linkedin" in cmd:
        speak("Opening Linkedin.")
        webbrowser.open("https://linkedin.com/")
        return True
    elif "open youtube" in cmd:
        speak("Opening YouTube.")
        webbrowser.open("https://youtube.com/")
        return True

    # File & Folder Ops
    if m := re.match(r"create folder (.+)", cmd):
        path = m.group(1).strip('"')
        os.makedirs(path, exist_ok=True)
        speak(f"Created folder {path}")
        return True

    if m := re.match(r"delete folder (.+)", cmd):
        path = m.group(1).strip('"')
        if os.path.isdir(path):
            shutil.rmtree(path)
            speak(f"Deleted folder {path}")
        else:
            speak(f"Folder {path} not found")
        return True

    if m := re.match(r"delete file (.+)", cmd):
        path = m.group(1).strip('"')
        if os.path.isfile(path):
            os.remove(path)
            speak(f"Deleted file {path}")
        else:
            speak(f"File {path} not found")
        return True

    if m := re.match(r"open file (.+)", cmd):
        path = m.group(1).strip('"')
        if os.path.exists(path):
            speak(f"Opening file {path}")
            os.startfile(path)
        else:
            speak(f"File {path} not found")
        return True

    if m := re.match(r"find file (.+) in (.+)", cmd):
        name, folder = m.group(1), m.group(2)
        results = _glob.glob(os.path.join(folder, f"*{name}*"))
        if results:
            speak(f"Found {len(results)} files; opening first.")
            os.startfile(results[0])
        else:
            speak("No matching files found.")
        return True

    # Media Control
    if m := re.match(r"play music from (.+)", cmd):
        folder = m.group(1).strip('"')
        if os.path.isdir(folder):
            tracks = _glob.glob(os.path.join(folder, "*.mp3"))
            if tracks:
                speak(f"Playing {os.path.basename(tracks[0])}")
                os.startfile(tracks[0])
            else:
                speak("No mp3 files found.")
        else:
            speak(f"Folder {folder} not found")
        return True

    if "play" in cmd:
        pyautogui.press("playpause")
        speak("Toggled play/pause")
        return True

    if "next" in cmd:
        pyautogui.press("nexttrack")
        speak("Next track")
        return True

    if "previous" in cmd:
        pyautogui.press("prevtrack")
        speak("Previous track")
        return True

    # Volume Control
    if m := re.match(r"set volume to (\d+)", cmd):
        vol = max(0, min(100, int(m.group(1))))
        speaker.Volume = vol
        speak(f"Volume set to {vol}%")
        return True

    if "mute" in cmd:
        pyautogui.press("volumemute")
        speak("Muted")
        return True

    if "unmute" in cmd:
        speaker.Volume = 100
        speak("Unmuted")
        return True

    if "volume up" in cmd:
        pyautogui.press("volumeup")
        speak("Volume up")
        return True

    if "volume down" in cmd:
        pyautogui.press("volumedown")
        speak("Volume down")
        return True

    # Screenshots & Recording
    if "screenshot" in cmd:
        fn = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot().save(fn)
        speak(f"Saved screenshot as {fn}")
        return True

    if any(phrase in cmd for phrase in ["record screen", "start recording", "capture screen", "screen capture", "record video", "start record"]):
        # parse duration or default to 10
        m = re.search(r'(\d+)', cmd)
        duration = int(m.group(1)) if m else 10
        fn = f"recording_{int(time.time())}.mp4"
        speak(f"Recording of {duration} seconds of screen is starting now.")

        # run in background to avoid blocking Jarvis’s main loop
        import threading
        t = threading.Thread(target=record_screen, args=(duration, fn), daemon=True)
        t.start()
        return True

    # System Info
    if "what time" in cmd:
        now = time.strftime("%I:%M %p")
        speak(f"The time is {now}")
        return True

    if "what date" in cmd:
        today = time.strftime("%B %d, %Y")
        speak(f"Today is {today}")
        return True

    if "battery" in cmd:
        batt = psutil.sensors_battery()
        speak(f"Battery at {int(batt.percent)}%") if batt else speak("Battery info unavailable")
        return True

    if "cpu usage" in cmd:
        speak(f"CPU at {psutil.cpu_percent()}%")
        return True

    if "memory usage" in cmd:
        speak(f"RAM at {psutil.virtual_memory().percent}%")
        return True

    if "ip address" in cmd:
        ip = socket.gethostbyname(socket.gethostname())
        speak(f"Your IP address is {ip}")
        return True

    if "system info" in cmd:
        info = f"{platform.system()} {platform.release()}, {platform.machine()}"
        speak(info)
        return True

    # Power & Lock
    shutdown_keywords = ["shutdown", "shut down", "power off"]
    restart_keywords  = ["restart", "reboot"]
    cancel_keywords   = ["cancel shutdown", "abort shutdown", "stop shutdown", "cancel restart", "abort restart", "stop restart"]
    lock_keywords     = ["lock workstation", "lock screen"]

    # Shutdown
    if any(kw in cmd for kw in shutdown_keywords):
        speak("Shutting down in 30 seconds. Say 'cancel shutdown' to abort.")
        os.system("shutdown /s /t 30")  # 30 second delay
        return True

    # Restart
    if any(kw in cmd for kw in restart_keywords):
        speak("Restarting in 30 seconds. Say 'cancel restart' to abort.")
        os.system("shutdown /r /t 30")  # FIXED
        return True

    # Cancel pending shutdown/restart
    if any(kw in cmd for kw in cancel_keywords):
        speak("Shutdown/Restart cancelled.")
        os.system("shutdown /a")
        return True

    # Lock screen
    if any(kw in cmd for kw in lock_keywords):
        speak("Locking workstation.")
        ctypes.windll.user32.LockWorkStation()
        return True

    # Exit
    if any(k in cmd for k in ("exit", "quit", "goodbye")):
        speak("Goodbye!")
        return True

    # Fallback → LLM
    return False

# ──────────────────────────────────────────────────────────────────────────────
# Startup Greeting
def greet_on_startup():
    name = "Vinit"
    h = int(time.strftime("%H"))
    if h < 12:
        speak(f"Good morning, {name}!")
    elif h < 18:
        speak(f"Good afternoon, {name}!")
    else:
        speak(f"Good evening, {name}!")
