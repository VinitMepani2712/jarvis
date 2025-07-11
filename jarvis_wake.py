from dotenv import load_dotenv
load_dotenv()

import os
import pvporcupine, sounddevice as sd, struct
from threading import Event

class WakeDetector:
    def __init__(
        self,
        keyword="bumblebee",
        model_path=None,
        sensitivity: float = 0.5
    ):
        access_key = os.getenv("PV_ACCESS_KEY")
        self._porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=[keyword],
            sensitivities=[sensitivity],
            model_path=model_path
        )
        # Event to signal when the keyword is detected
        self.stop_event = Event()

    def audio_callback(self, indata, frames, time, status):
        pcm = struct.unpack_from("h" * frames, indata.tobytes())
        if self._porcupine.process(pcm) >= 0:
            # wake-word detected → signal the main thread
            self.stop_event.set()

    def wait_for_wake(self):
        # open the audio stream and block until the event is set
        with sd.InputStream(
            device=0,
            samplerate=self._porcupine.sample_rate,
            blocksize=self._porcupine.frame_length,
            channels=1,
            dtype="int16",
            callback=self.audio_callback
        ):
            print("Listening for wake-word…")
            self.stop_event.wait()    # block here until audio_callback sets it
            self.stop_event.clear()   # reset for the next round
            return True
