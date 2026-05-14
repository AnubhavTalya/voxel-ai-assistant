"""
core/engine.py — Audio capture pipeline + Whisper.cpp offline transcription.

Flow:
  Microphone (PyAudio) → VAD (RMS silence detection) → buffer utterance
  → Whisper.cpp (via faster-whisper or whisper-cpp-python) → text
  → CommandRouter
"""

from __future__ import annotations

import io
import logging
import queue
import threading
import time
import wave
from typing import Optional

import numpy as np

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER = True
except ImportError:
    FASTER_WHISPER = False

try:
    import whisper as openai_whisper
    OPENAI_WHISPER = True
except ImportError:
    OPENAI_WHISPER = False


CHUNK = 1024          # frames per PyAudio buffer read
FORMAT = None         # set at runtime (pyaudio.paInt16)
CHANNELS = 1
MAX_SILENCE_CHUNKS = 999   # hard safety cap


class VoiceEngine:
    """
    Captures microphone audio, detects speech boundaries via VAD,
    transcribes each utterance offline with Whisper, and routes the
    resulting text to the CommandRouter.
    """

    def __init__(
        self,
        model_name: str,
        router,
        tts,
        logger: logging.Logger,
        sample_rate: int = 16_000,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.2,
    ):
        self.model_name = model_name
        self.router = router
        self.tts = tts
        self.log = logger
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self._audio: Optional["pyaudio.PyAudio"] = None
        self._stream = None
        self._model = None
        self._active = threading.Event()
        self._audio_queue: queue.Queue = queue.Queue()

        self._load_model()

    # ── Model Loading ────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        self.log.info(f"Loading Whisper model '{self.model_name}' (offline)...")
        if FASTER_WHISPER:
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",     # quantised — low RAM, fast on CPU
            )
            self._backend = "faster-whisper"
        elif OPENAI_WHISPER:
            self._model = openai_whisper.load_model(self.model_name)
            self._backend = "openai-whisper"
        else:
            self.log.warning(
                "No Whisper backend found. Install faster-whisper or openai-whisper.\n"
                "  pip install faster-whisper"
            )
            self._model = None
            self._backend = "none"
        self.log.info(f"Whisper backend: {self._backend}")

    # ── Public API ───────────────────────────────────────────────────────────

    def activate(self) -> None:
        """Listen for one utterance (called by WakeWordDetector on detection)."""
        self._active.set()
        self.log.debug("Voice engine activated for one utterance.")
        self.tts.speak("Listening.")
        audio_data = self._record_utterance()
        self._active.clear()
        if audio_data is not None and len(audio_data) > 0:
            text = self._transcribe(audio_data)
            if text:
                self.log.info(f"Transcribed: '{text}'")
                self.router.dispatch(text)
            else:
                self.log.debug("Transcription returned empty string.")
                self.tts.speak("Sorry, I didn't catch that.")

    def listen_loop(self) -> None:
        """Continuously listen and dispatch (always-on mode)."""
        self.log.info("Always-on listen loop started.")
        while True:
            audio_data = self._record_utterance()
            if audio_data is not None and len(audio_data) > 0:
                text = self._transcribe(audio_data)
                if text:
                    self.log.info(f"Transcribed: '{text}'")
                    self.router.dispatch(text)

    # ── Audio Capture ────────────────────────────────────────────────────────

    def _open_stream(self):
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError(
                "PyAudio is not installed. Run: pip install pyaudio"
            )
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=CHUNK,
        )
        return pa, stream

    def _record_utterance(self) -> Optional[np.ndarray]:
        """
        Record until we detect speech followed by silence.
        Returns a float32 numpy array normalised to [-1, 1], or None on error.
        """
        try:
            pa, stream = self._open_stream()
        except Exception as exc:
            self.log.error(f"Could not open audio stream: {exc}")
            return None

        frames = []
        silence_chunks = 0
        speaking = False
        silence_limit = int(
            self.silence_duration * self.sample_rate / CHUNK
        )

        self.log.debug("Recording utterance...")
        try:
            while True:
                raw = stream.read(CHUNK, exception_on_overflow=False)
                pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(pcm ** 2)))

                if rms > self.silence_threshold:
                    speaking = True
                    silence_chunks = 0
                    frames.append(raw)
                elif speaking:
                    frames.append(raw)
                    silence_chunks += 1
                    if silence_chunks >= silence_limit:
                        break   # end of utterance
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        if not frames:
            return None

        pcm_all = np.frombuffer(b"".join(frames), dtype=np.int16)
        return pcm_all.astype(np.float32) / 32768.0

    # ── Transcription ────────────────────────────────────────────────────────

    def _transcribe(self, audio: np.ndarray) -> str:
        if self._model is None:
            self.log.warning("No Whisper model loaded; returning empty transcript.")
            return ""

        self.log.debug("Transcribing audio...")
        t0 = time.perf_counter()

        try:
            if self._backend == "faster-whisper":
                segments, _ = self._model.transcribe(
                    audio,
                    language="en",
                    beam_size=5,
                    vad_filter=True,          # built-in VAD to skip silence
                )
                text = " ".join(s.text for s in segments).strip()

            elif self._backend == "openai-whisper":
                result = self._model.transcribe(
                    audio,
                    language="en",
                    fp16=False,
                )
                text = result["text"].strip()
            else:
                text = ""

        except Exception as exc:
            self.log.error(f"Transcription error: {exc}")
            return ""

        elapsed = (time.perf_counter() - t0) * 1000
        self.log.debug(f"Transcription done in {elapsed:.0f} ms: '{text}'")
        return text

    # ── Helpers ──────────────────────────────────────────────────────────────

    def audio_to_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convert float32 ndarray to WAV bytes (for debugging / logging)."""
        pcm_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_int16.tobytes())
        return buf.getvalue()
