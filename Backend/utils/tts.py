"""
utils/tts.py — Offline Text-to-Speech engine.

Priority order:
  1. pyttsx3  — cross-platform, uses OS native voices (SAPI5 / espeak / NSSpeechSynthesizer)
  2. espeak   — Linux command-line TTS fallback
  3. Silent   — logs the message, speaks nothing (useful in unit tests)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from typing import Optional

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

log = logging.getLogger("voxel.tts")


class TTSEngine:
    """
    Thread-safe offline TTS wrapper.  All speech is queued and spoken
    on a dedicated thread so it never blocks the main voice loop.
    """

    def __init__(
        self,
        rate: int = 175,
        volume: float = 0.9,
        enabled: bool = True,
    ):
        self.rate = rate
        self.volume = volume
        self.enabled = enabled

        self._engine = None
        self._lock = threading.Lock()
        self._backend = "none"

        if enabled:
            self._setup()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _setup(self) -> None:
        if PYTTSX3_AVAILABLE:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", self.rate)
                self._engine.setProperty("volume", self.volume)
                self._backend = "pyttsx3"
                log.info("TTS backend: pyttsx3")
                return
            except Exception as exc:
                log.warning(f"pyttsx3 init failed: {exc}")

        if shutil.which("espeak"):
            self._backend = "espeak"
            log.info("TTS backend: espeak")
            return

        if shutil.which("say"):   # macOS
            self._backend = "say"
            log.info("TTS backend: macOS 'say'")
            return

        log.warning(
            "No TTS backend found. Install pyttsx3: pip install pyttsx3\n"
            "  or on Linux: sudo apt install espeak"
        )
        self._backend = "none"

    # ── Public API ───────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Speak *text* asynchronously (fire-and-forget)."""
        if not self.enabled or not text.strip():
            return
        log.debug(f"TTS: '{text}'")
        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()

    def speak_sync(self, text: str) -> None:
        """Speak *text* and block until done."""
        if not self.enabled or not text.strip():
            return
        self._speak_sync(text)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _speak_sync(self, text: str) -> None:
        with self._lock:
            if self._backend == "pyttsx3" and self._engine:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as exc:
                    log.error(f"pyttsx3 speech error: {exc}")

            elif self._backend == "espeak":
                rate_arg = str(int(self.rate * 0.9))   # espeak uses wpm ≈ same scale
                subprocess.run(
                    ["espeak", "-s", rate_arg, "-a", str(int(self.volume * 200)), text],
                    capture_output=True,
                )

            elif self._backend == "say":
                subprocess.run(["say", "-r", str(self.rate), text], capture_output=True)

            else:
                log.info(f"[TTS silent] {text}")

    # ── Config ───────────────────────────────────────────────────────────────

    def set_rate(self, wpm: int) -> None:
        self.rate = wpm
        if self._backend == "pyttsx3" and self._engine:
            self._engine.setProperty("rate", wpm)

    def set_volume(self, vol: float) -> None:
        self.volume = max(0.0, min(1.0, vol))
        if self._backend == "pyttsx3" and self._engine:
            self._engine.setProperty("volume", self.volume)

    def list_voices(self) -> list:
        if self._backend == "pyttsx3" and self._engine:
            return self._engine.getProperty("voices")
        return []

    def set_voice(self, voice_id: str) -> None:
        if self._backend == "pyttsx3" and self._engine:
            self._engine.setProperty("voice", voice_id)
