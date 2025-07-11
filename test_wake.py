# test_wake.py
from dotenv import load_dotenv
load_dotenv()            # loads PV_ACCESS_KEY from .env

from jarvis_wake import WakeDetector

# Force sounddevice to use the same default input
import sounddevice as sd
sd.default.device = 0    # index 0 in / out tuple; 
                         # you can also do sd.default.device = (0, None)

wd = WakeDetector()
print("Listening for wake-word… (say ‘Jarvis’ clearly now)")
wd.wait_for_wake()
print("✅ Detected wake-word!")
