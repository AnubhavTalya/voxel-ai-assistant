"""
VOXEL — Offline Voice-Controlled AI Assistant
Entry point: initializes all subsystems and starts the main loop.
"""

import sys
import signal
import logging
import threading
from pathlib import Path

from core.engine import VoiceEngine
from core.command_router import CommandRouter
from core.wake_word import WakeWordDetector
from core.ws_server import WSServer
from automation.executor import AutomationExecutor
from utils.logger import setup_logger
from utils.tts import TTSEngine
from config.settings import Settings


def shutdown_handler(sig, frame):
    logging.getLogger("voxel").info("Shutdown signal received. Stopping VOXEL...")
    sys.exit(0)


def main():
    # ── Setup ────────────────────────────────────────────────────────────────
    settings = Settings.load()
    logger = setup_logger(
        name="voxel",
        log_file=settings.log_file,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )
    logger.info("=" * 60)
    logger.info("  VOXEL — Offline Voice AI Assistant  (v1.0.0)")
    logger.info("=" * 60)
    logger.info(f"Model      : {settings.whisper_model}")
    logger.info(f"Wake word  : {settings.wake_word}")
    logger.info(f"TTS        : {'enabled' if settings.tts_enabled else 'disabled'}")
    logger.info(f"Privacy    : all audio stays on-device")

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # ── Subsystem Init ───────────────────────────────────────────────────────
    tts = TTSEngine(
        rate=settings.tts_rate,
        volume=settings.tts_volume,
        enabled=settings.tts_enabled,
    )

    executor = AutomationExecutor(logger=logger)

    router = CommandRouter(
        executor=executor,
        tts=tts,
        logger=logger,
    )

    engine = VoiceEngine(
        model_name=settings.whisper_model,
        router=router,
        tts=tts,
        logger=logger,
        sample_rate=settings.sample_rate,
        silence_threshold=settings.silence_threshold,
        silence_duration=settings.silence_duration,
    )

    wake_detector = WakeWordDetector(
        wake_word=settings.wake_word,
        sensitivity=settings.wake_word_sensitivity,
        engine=engine,
        logger=logger,
        sample_rate=settings.sample_rate,
    )

    # ── WebSocket Server (frontend bridge) ───────────────────────────────────
    ws_server = WSServer(
        engine=engine,
        router=router,
        tts=tts,
        logger=logger,
    )
    ws_server.start()

    # Wire WebSocket event emitters into the engine and router so the
    # Electron frontend receives live updates for every state change.
    engine.on_status     = ws_server.emit_status
    engine.on_transcript = ws_server.emit_transcript
    engine.on_waveform   = ws_server.emit_waveform
    router.on_response   = ws_server.emit_response
    router.on_command    = ws_server.emit_command

    logger.info(f"WebSocket bridge : ws://localhost:{WSServer.PORT}")

    # ── Start ────────────────────────────────────────────────────────────────
    tts.speak(f"VOXEL is online. Say {settings.wake_word} to activate.")
    ws_server.emit_log("info", f"VOXEL online. Wake word: '{settings.wake_word}'")

    if settings.always_on:
        logger.info("Always-on mode: listening continuously.")
        ws_server.emit_status("idle")
        engine_thread = threading.Thread(target=engine.listen_loop, daemon=True)
        engine_thread.start()
        engine_thread.join()
    else:
        logger.info(f"Wake-word mode: waiting for '{settings.wake_word}'.")
        ws_server.emit_status("idle")
        wake_detector.run()


if __name__ == "__main__":
    main()
