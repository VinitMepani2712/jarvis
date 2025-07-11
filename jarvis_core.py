from calendar import c
import ctypes
import glob
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
import speech_recognition as sr
import webbrowser
from threading import Event
from dotenv import load_dotenv
import pvporcupine
import sounddevice as sd
import speech_recognition as sr
from speech_recognition import RequestError, WaitTimeoutError
from win32com.client import Dispatch
import pyautogui
import pygetwindow as gw
import psutil

from jarvis_llm import chat_with_ai

# ─── Env & Keys ───────────────────────────────────────────────────────────────
load_dotenv(override=True)
PV_ACCESS_KEY = os.getenv("PV_ACCESS_KEY")
# NASA_KEY = os.getenv("NASA_API_KEY")

# ─── TTS via Windows SAPI ─────────────────────────────────────────────────────
speaker = Dispatch("SAPI.SpVoice")
speaker.Rate = 0
speaker.Volume = 100

def speak(text: str):
    """Speak text out loud and echo to console."""
    print(f"[jarvis speaking]: {text}")
    try:
        speaker.Speak(text)
    except Exception as e:
        print(f"[TTS error]: {e}")

# ─── STT Setup ────────────────────────────────────────────────────────────────
recognizer = sr.Recognizer()
mic = sr.Microphone()

# ─── WakeWord Detector ─────────────────────────────────────────────────────────
class WakeDetector:
    def __init__(self, keyword="jarvis", model_path=None, sensitivity: float = 0.5):
        access_key = PV_ACCESS_KEY
        self._porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=[keyword],
            sensitivities=[sensitivity],
            model_path=model_path
        )
        self.stop_event = Event()

    def audio_callback(self, indata, frames, time_info, status):
        pcm = struct.unpack_from("h" * frames, indata.tobytes())
        if self._porcupine.process(pcm) >= 0:
            self.stop_event.set()

    def wait_for_wake(self):
        with sd.InputStream(
            device=None,
            samplerate=self._porcupine.sample_rate,
            blocksize=self._porcupine.frame_length,
            channels=1,
            dtype="int16",
            callback=self.audio_callback
        ):
            self.stop_event.wait()
            self.stop_event.clear()
            return True

# Calibrate ambient noise once
with mic as source:
    recognizer.adjust_for_ambient_noise(source, duration=0.5)
    print(f"[DEBUG] energy_threshold set to {recognizer.energy_threshold}")

wake = WakeDetector(keyword="jarvis", sensitivity=0.2)

# ─── Listening Function ─────────────────────────────────────────────────────
def listen(timeout: float = 5, phrase_time_limit: float = 5) -> str:
    """
    Listen on the default mic.
    timeout: seconds to wait for phrase start
    phrase_time_limit: max seconds for the phrase itself
    """
    with mic as source:
        print("[jarvis listening…]")
        try:
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )
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

# ─── Local small-talk Data ────────────────────────────────────────────────────
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
    if any(g in text for g in ("hi","hello","hey","good morning","good afternoon","good evening")):
        return random.choice(GREETINGS)
    if "how are you" in text or "how's it going" in text:
        return random.choice(HOW_ARE_YOU)
    if "joke" in text or "tell me a joke" in text:
        return random.choice(JOKES)
    return ""

# ─── Command Dispatcher ──────────────────────────────────────────────────────
def handle_command(cmd: str) -> bool:
    """
    Returns True if a built-in command handled it;
    False → fall back to LLM.
    """
    cmd = cmd.lower().strip()
    print(f">>> You said: {cmd}")

    # ── small-talk ────────────────────────────────────────────────────────────
    reply = local_small_talk(cmd)
    if reply:
        speak(reply)
        return True

    # ── Context-aware typing ──────────────────────────────────────────────────
    if m := re.match(r"type (.+) on (browser|notepad|word|code)", cmd):
        text, app = m.group(1), m.group(2)
        title_map = {
            "browser": None,
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
                    'notepad':'notepad.exe',
                    'word':'winword.exe',
                    'code':'code'
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

    # ── App control ───────────────────────────────────────────────────────────
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

    # ── Browser & Web Search ───────────────────────────────────────────────────
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
    
    # ── File & Folder Ops ──────────────────────────────────────────────────────
    if m := re.match(r"create folder (.+)", cmd):
        path = m.group(1).strip('"')
        os.makedirs(path, exist_ok=True)
        speak(f"Created folder {path}")
        return True
    if m := re.match(r"delete folder (.+)", cmd):
        path = m.group(1).strip('"')
        if os.path.isdir(path): shutil.rmtree(path); speak(f"Deleted folder {path}")
        else: speak(f"Folder {path} not found")
        return True
    if m := re.match(r"delete file (.+)", cmd):
        path = m.group(1).strip('"')
        if os.path.isfile(path): os.remove(path); speak(f"Deleted file {path}")
        else: speak(f"File {path} not found")
        return True
    if m := re.match(r"open file (.+)", cmd):
        path = m.group(1).strip('"')
        if os.path.exists(path): speak(f"Opening file {path}"); os.startfile(path)
        else: speak(f"File {path} not found")
        return True
    if m := re.match(r"find file (.+) in (.+)", cmd):
        name, folder = m.group(1), m.group(2)
        results = glob(os.path.join(folder, f"*{name}*"))
        if results: speak(f"Found {len(results)} files; opening first."); os.startfile(results[0])
        else: speak("No matching files found.")
        return True

    # ── Media Control ─────────────────────────────────────────────────────────
    if m := re.match(r"play music from (.+)", cmd):
        folder = m.group(1).strip('"')
        if os.path.isdir(folder):
            tracks = glob(os.path.join(folder, "*.mp3"))
            if tracks: speak(f"Playing {os.path.basename(tracks[0])}"); os.startfile(tracks[0])
            else: speak("No mp3 files found.")
        else: speak(f"Folder {folder} not found")
        return True
    if "play" in cmd: pyautogui.press("playpause"); speak("Toggled play/pause"); return True
    if "next" in cmd: pyautogui.press("nexttrack"); speak("Next track"); return True
    if "previous" in cmd: pyautogui.press("prevtrack"); speak("Previous track"); return True

    # ── Volume Control ─────────────────────────────────────────────────────────
    if m := re.match(r"set volume to (\d+)", cmd): 
        vol = max(0,min(100,int(m.group(1)))); 
        speaker.Volume = vol; 
        speak(f"Volume set to {vol}%"); 
        return True
    if "mute" in cmd: 
        pyautogui.press("volumemute"); 
        speak("Muted"); 
        return True
    if "unmute" in cmd: 
        speaker.Volume = 100; 
        speak("Unmuted"); 
        return True
    if "volume up" in cmd: 
        pyautogui.press("volumeup"); 
        speak("Volume up"); 
        return True
    if "volume down" in cmd: 
        pyautogui.press("volumedown"); 
        speak("Volume down"); 
        return True

    # ── Screenshots & Recording ────────────────────────────────────────────────
    if "screenshot" in cmd: 
        fn=f"screenshot_{int(time.time())}.png"; 
        pyautogui.screenshot().save(fn); 
        speak(f"Saved screenshot as {fn}"); 
        return True
    if "record screen" in cmd: 
        fn=f"recording_{int(time.time())}.mp4"; 
        speak("Recording 10 seconds of screen..."); 
        subprocess.Popen(["ffmpeg","-y","-f","gdigrab","-framerate","15","-t","10","-i","desktop",fn]); 
        return True

    # ── System Info ───────────────────────────────────────────────────────────
    if "what time" in cmd: now=time.strftime("%I:%M %p"); speak(f"The time is {now}"); return True
    if "what date" in cmd: today=time.strftime("%B %d, %Y"); speak(f"Today is {today}"); return True
    if "battery" in cmd: batt=psutil.sensors_battery(); speak(f"Battery at {int(batt.percent)}%") if batt else speak("Battery info unavailable"); return True
    if "cpu usage" in cmd: speak(f"CPU at {psutil.cpu_percent()}%"); return True
    if "memory usage" in cmd: speak(f"RAM at {psutil.virtual_memory().percent}%"); return True
    if "ip address" in cmd: ip=socket.gethostbyname(socket.gethostname()); speak(f"Your IP address is {ip}"); return True
    if "system info" in cmd: info=f"{platform.system()} {platform.release()}, {platform.machine()}"; speak(info); return True

    # ── Power & Lock ───────────────────────────────────────────────────────────
    if "shutdown" in cmd: speak("Shutting down in 5 seconds."); os.system("shutdown /s /t 5"); return True
    if "restart" in cmd: speak("Restarting in 5 seconds."); os.system("shutdown /r /t 5"); return True
    if "lock workstation" in cmd: speak("Locking workstation."); ctypes.windll.user32.LockWorkStation(); return True

   
    # ── Exit ───────────────────────────────────────────────────────────────────
    if any(k in cmd for k in ("exit","quit","goodbye")): speak("Goodbye!"); sys.exit(0)

    # ── Fallback → LLM ─────────────────────────────────────────────────────────
    return False

# ─── Startup Greeting ───────────────────────────────────────────────────────────
def greet_on_startup():
    name = "Vinit"
    h = int(time.strftime("%H"))
    if h < 12:
        speak(f"Good morning, {name}!")
    elif h < 18:
        speak(f"Good afternoon, {name}!")
    else:
        speak(f"Good evening, {name}!")
