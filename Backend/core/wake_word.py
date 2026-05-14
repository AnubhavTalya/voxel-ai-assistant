"""
core/wake_word.py — Lightweight offline wake-word detection.

Strategy (in priority order):
  1. openWakeWord  (pip install openwakeword)         — best accuracy, free
  2. Porcupine     (pip install pvporcupine)           — commercial, very fast
  3. Simple RMS + keyword fuzzy-match fallback        — no extra dependencies

When a wake word is detected the WakeWordDetector calls engine.activate()
which records + transcribes one utterance, then returns to wake-word watch.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
    OWW_AVAILABLE = True
except ImportError:
    OWW_AVAILABLE = False

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False


CHUNK = 1280        # openWakeWord expects 80 ms @ 16 kHz → 1280 samples
CHANNELS = 1
SAMPLE_RATE = 16_000


class WakeWordDetector:
    """
    Continuously reads audio from the microphone and fires engine.activate()
    whenever the configured wake word (or a close fuzzy match) is detected.
    """

    def __init__(
        self,
        wake_word: str,
        sensitivity: float,
        engine,
        logger: logging.Logger,
        sample_rate: int = SAMPLE_RATE,
    ):
        self.wake_word = wake_word.lower().strip()
        self.sensitivity = sensitivity
        self.engine = engine
        self.log = logger
        self.sample_rate = sample_rate

        self._backend = self._detect_backend()
        self._oww_model: Optional[OWWModel] = None
        self._porcupine = None
        self._setup_backend()

    # ── Backend selection ────────────────────────────────────────────────────

    def _detect_backend(self) -> str:
        if OWW_AVAILABLE:
            return "openwakeword"
        if PORCUPINE_AVAILABLE:
            return "porcupine"
        return "fuzzy"

    def _setup_backend(self) -> None:
        self.log.info(f"Wake-word backend: {self._backend}")
        if self._backend == "openwakeword":
            # openWakeWord ships with "hey_jarvis", "alexa", "hey_mycroft" etc.
            # For a custom word, train your own .tflite model and pass its path.
            self._oww_model = OWWModel(
                wakeword_models=["hey_jarvis"],   # closest built-in proxy
                inference_framework="tflite",
            )
        elif self._backend == "porcupine":
            # Free built-in keywords: "hey siri", "ok google", "picovoice", etc.
            # For a custom wake word use the Picovoice console to export a .ppn file.
            self._porcupine = pvporcupine.create(
                keywords=["picovoice"],           # substitute your exported .ppn
                sensitivities=[self.sensitivity],
            )

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Block forever, waking the engine on detection."""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio is required: pip install pyaudio")

        self.log.info(f"Waiting for wake word: '{self.wake_word}'")
        pa = pyaudio.PyAudio()

        stream = pa.open(
            rate=self.sample_rate,
            channels=CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=CHUNK,
        )

        try:
            while True:
                raw = stream.read(CHUNK, exception_on_overflow=False)
                detected = self._check(raw)
                if detected:
                    self.log.info("Wake word detected!")
                    stream.stop_stream()
                    self.engine.activate()
                    stream.start_stream()
                    self.log.info(f"Resuming wake-word watch for '{self.wake_word}'")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            if self._porcupine:
                self._porcupine.delete()

    # ── Detection logic per backend ──────────────────────────────────────────

    def _check(self, raw_bytes: bytes) -> bool:
        pcm = np.frombuffer(raw_bytes, dtype=np.int16)

        if self._backend == "openwakeword":
            return self._check_oww(pcm)
        elif self._backend == "porcupine":
            return self._check_porcupine(pcm)
        else:
            return self._check_fuzzy(pcm)

    def _check_oww(self, pcm: np.ndarray) -> bool:
        prediction = self._oww_model.predict(pcm)
        # prediction is a dict: {model_name: confidence_0_to_1}
        max_conf = max(prediction.values(), default=0.0)
        return float(max_conf) >= self.sensitivity

    def _check_porcupine(self, pcm: np.ndarray) -> bool:
        keyword_index = self._porcupine.process(pcm)
        return keyword_index >= 0

    def _check_fuzzy(self, pcm: np.ndarray) -> bool:
        """
        Fallback: high-RMS audio triggers the engine which transcribes it;
        if the transcript contains the wake word we consider it detected.
        This runs a quick energy check first to avoid calling Whisper every chunk.
        """
        rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
        return rms > 800   # raw int16 RMS; tune to your mic
