"""
core/ws_server.py — WebSocket bridge between Python backend and Electron frontend.

Starts a local WebSocket server on ws://localhost:8765.
The frontend connects to this to receive real-time events and send commands.

Add to main.py:
    from core.ws_server import WSServer
    ws_server = WSServer(engine=engine, router=router, tts=tts, logger=logger)
    ws_server.start()  # starts in background thread
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Set

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False


class WSServer:
    """
    Async WebSocket server that bridges the Python voice engine to the
    Electron/React frontend.

    Frontend → Backend messages:
        { "action": "activate" }
        { "action": "stop" }
        { "action": "settings", "data": {...} }

    Backend → Frontend messages (pushed via broadcast):
        { "type": "status",     "state": "listening" }
        { "type": "transcript", "text": "open chrome" }
        { "type": "response",   "text": "Opening Chrome." }
        { "type": "command",    "name": "open_app", "success": true }
        { "type": "log",        "level": "info", "message": "..." }
        { "type": "waveform",   "rms": 0.08 }
    """

    HOST = "localhost"
    PORT = 8765

    def __init__(self, engine, router, tts, logger: logging.Logger):
        self.engine = engine
        self.router = router
        self.tts = tts
        self.log = logger
        self._clients: Set = set()
        self._loop: asyncio.AbstractEventLoop = None

    # ── Start ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if not WS_AVAILABLE:
            self.log.warning(
                "websockets not installed; frontend bridge disabled.\n"
                "  pip install websockets"
            )
            return
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        self.log.info(f"WebSocket server started at ws://{self.HOST}:{self.PORT}")

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        async with websockets.serve(self._handler, self.HOST, self.PORT):
            await asyncio.Future()   # run forever

    # ── Connection handler ───────────────────────────────────────────────────

    async def _handler(self, ws: "WebSocketServerProtocol") -> None:
        self._clients.add(ws)
        self.log.info(f"Frontend connected: {ws.remote_address}")
        await self._send(ws, {"type": "status", "state": "idle"})

        try:
            async for raw in ws:
                await self._handle_message(raw)
        except Exception:
            pass
        finally:
            self._clients.discard(ws)
            self.log.info("Frontend disconnected.")

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        action = msg.get("action")
        self.log.debug(f"WS message: {msg}")

        if action == "activate":
            threading.Thread(
                target=self.engine.activate,
                daemon=True,
            ).start()

        elif action == "stop":
            self.engine._active.clear()

        elif action == "settings":
            data = msg.get("data", {})
            # Apply relevant settings to live engine
            if "silenceThreshold" in data:
                self.engine.silence_threshold = float(data["silenceThreshold"])
            if "silenceDuration" in data:
                self.engine.silence_duration = float(data["silenceDuration"])
            if "ttsEnabled" in data:
                self.tts.enabled = bool(data["ttsEnabled"])
            if "ttsRate" in data:
                self.tts.set_rate(int(data["ttsRate"]))
            self.log.info(f"Settings updated from frontend: {data}")

    # ── Broadcast helpers ────────────────────────────────────────────────────

    def broadcast(self, payload: dict) -> None:
        """Thread-safe broadcast to all connected clients."""
        if not self._loop or not self._clients:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async(payload), self._loop
        )

    async def _broadcast_async(self, payload: dict) -> None:
        if not self._clients:
            return
        message = json.dumps(payload)
        dead = set()
        for ws in self._clients:
            try:
                await ws.send(message)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    async def _send(self, ws, payload: dict) -> None:
        try:
            await ws.send(json.dumps(payload))
        except Exception:
            pass

    # ── Convenience event emitters (call from engine/router) ─────────────────

    def emit_status(self, state: str) -> None:
        self.broadcast({"type": "status", "state": state})

    def emit_transcript(self, text: str) -> None:
        self.broadcast({"type": "transcript", "text": text})

    def emit_response(self, text: str) -> None:
        self.broadcast({"type": "response", "text": text})

    def emit_command(self, name: str, success: bool, error: str = "") -> None:
        self.broadcast({"type": "command", "name": name, "success": success, "error": error})

    def emit_log(self, level: str, message: str) -> None:
        self.broadcast({"type": "log", "level": level, "message": message})

    def emit_waveform(self, rms: float) -> None:
        self.broadcast({"type": "waveform", "rms": round(rms, 4)})
