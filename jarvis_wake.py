import os
import struct
import pvporcupine
import sounddevice as sd
from threading import Event

# Built-in keywords vary by Porcupine build; these are common ones.
BUILT_INS = {
    "porcupine", "bumblebee", "americano", "blueberry", "terminator",
    "grapefruit", "grasshopper", "picovoice"
    # "jarvis" is NOT guaranteed as built-in; usually requires a .ppn
}

class WakeDetector:
    """
    Wake word detector using Porcupine.
    - If `keyword` is one of Porcupine's built-ins, uses `keywords=[keyword]`.
    - Otherwise, tries to load a custom keyword .ppn via env var:
        JARVIS_PPN=<absolute path to .ppn>
      or by passing keyword="path/to/your.ppn" (absolute).
    """

    def __init__(self, keyword: str = "jarvis", sensitivity: float = 0.5, model_path: str | None = None):
        access_key = os.getenv("PV_ACCESS_KEY", "").strip()
        if not access_key:
            raise RuntimeError(
                "PV_ACCESS_KEY is missing. Add it to your .env:\n"
                "  PV_ACCESS_KEY=pk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
            )

        # Decide built-in vs custom keyword
        use_builtin = keyword in BUILT_INS
        keyword_paths = None

        # If user asked for "jarvis" and it's not built-in, try a .ppn path
        if not use_builtin:
            # Allow passing an absolute path as the 'keyword' itself
            if os.path.isabs(keyword) and keyword.lower().endswith(".ppn"):
                keyword_paths = [keyword]
            else:
                # Otherwise read from env (recommended)
                ppn = os.getenv("JARVIS_PPN", "").strip()
                if not ppn:
                    raise RuntimeError(
                        f'The hotword "{keyword}" is not a known built-in. Provide a custom .ppn file.\n'
                        "Set JARVIS_PPN in your .env, e.g.:\n"
                        "  JARVIS_PPN=V:\\Vinit\\jarvis\\jarvis_en_windows.ppn\n"
                        "Or call WakeDetector(keyword=r'V:\\\\path\\\\to\\\\your.ppn')."
                    )
                if not os.path.isabs(ppn) or not os.path.exists(ppn):
                    raise RuntimeError(f"JARVIS_PPN does not exist or is not absolute: {ppn}")
                keyword_paths = [ppn]

        try:
            if use_builtin:
                self._porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=[keyword],
                    sensitivities=[sensitivity],
                    model_path=model_path,
                )
            else:
                self._porcupine = pvporcupine.create(
                    access_key=access_key,
                    keyword_paths=keyword_paths,
                    sensitivities=[sensitivity],
                    model_path=model_path,
                )
        except Exception as e:
            # Most common: 00000136 (activation refused) → bad/missing key, wrong org/project, or quota.
            raise RuntimeError(
                "Porcupine init failed.\n"
                f"- Keyword: {keyword}\n"
                f"- Built-in: {use_builtin}\n"
                f"- Model path: {model_path or 'default'}\n"
                "Hints:\n"
                "  • Ensure PV_ACCESS_KEY is valid (no quotes / no spaces) and internet is available on first run.\n"
                "  • If using a custom .ppn, verify the absolute path is correct and matches your platform.\n"
                f"Original error: {e}"
            ) from e

        # Open default input device. If you must choose a specific device index, change device=None → device=<index>.
        self._stream = sd.InputStream(
            samplerate=self._porcupine.sample_rate,
            channels=1,
            dtype="int16",
            device=None,  # system default
            blocksize=self._porcupine.frame_length,
        )

        self._stopped = Event()
        self._stream.start()

    def wait_for_wake(self) -> bool:
        """Blocks until the wake-word is detected. Returns True if detected; False if stopped."""
        while not self._stopped.is_set():
            # Read one Porcupine frame
            data, _ = self._stream.read(self._porcupine.frame_length)
            pcm = struct.unpack_from("h" * self._porcupine.frame_length, data)
            res = self._porcupine.process(pcm)
            if res >= 0:
                return True
        return False

    def stop(self):
        self._stopped.set()
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        finally:
            if hasattr(self, "_porcupine") and self._porcupine is not None:
                self._porcupine.delete()
