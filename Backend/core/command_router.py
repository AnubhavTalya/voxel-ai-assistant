"""
core/command_router.py — Intent recognition + command dispatch.

Uses a hybrid approach (no internet required):
  1. Exact / keyword pattern matching (regex rules, fastest)
  2. Fuzzy similarity scoring (difflib, for noisy/misheard input)
  3. Optional: local LLM via Ollama for complex, multi-step requests

Commands are registered as CommandDefinition objects; the router scores
all of them against the transcript and fires the best match above a
confidence threshold.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple

# Optional: Ollama local LLM for complex intent extraction
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


CONFIDENCE_THRESHOLD = 0.45    # below this → "I don't understand"
LLM_CONFIDENCE_THRESHOLD = 0.3 # fall through to LLM if score is this low


@dataclass
class CommandDefinition:
    """Describes a single voice command and its handler."""
    name: str
    patterns: List[str]             # regex patterns (case-insensitive)
    keywords: List[str]             # keyword bag for fuzzy matching
    handler: Callable[..., Any]
    description: str = ""
    category: str = "general"
    example_phrases: List[str] = field(default_factory=list)

    def compiled_patterns(self):
        return [re.compile(p, re.IGNORECASE) for p in self.patterns]


class CommandRouter:
    """
    Receives transcribed text, finds the best-matching command,
    and calls its handler. Falls back to a local LLM if available.
    """

    def __init__(self, executor, tts, logger: logging.Logger):
        self.executor = executor
        self.tts = tts
        self.log = logger
        self._commands: List[CommandDefinition] = []
        self._register_builtin_commands()

    # ── Public API ───────────────────────────────────────────────────────────

    def register(self, cmd: CommandDefinition) -> None:
        self._commands.append(cmd)
        self.log.debug(f"Registered command: {cmd.name}")

    def dispatch(self, text: str) -> bool:
        """
        Match *text* to the best command and execute it.
        Returns True if a command was dispatched, False otherwise.
        """
        text = text.strip()
        self.log.info(f"Dispatching: '{text}'")

        match, confidence, args = self._best_match(text)

        if match and confidence >= CONFIDENCE_THRESHOLD:
            self.log.info(
                f"Matched '{match.name}' (confidence={confidence:.2f}) args={args}"
            )
            try:
                match.handler(**args)
            except Exception as exc:
                self.log.error(f"Command '{match.name}' raised: {exc}")
                self.tts.speak(f"Sorry, something went wrong running {match.name}.")
            return True

        # Low-confidence fall-through to LLM
        if OLLAMA_AVAILABLE and confidence < LLM_CONFIDENCE_THRESHOLD:
            return self._llm_dispatch(text)

        self.log.info(f"No command matched (best conf={confidence:.2f}).")
        self.tts.speak("Sorry, I didn't understand that command.")
        return False

    def list_commands(self) -> List[CommandDefinition]:
        return list(self._commands)

    # ── Matching ─────────────────────────────────────────────────────────────

    def _best_match(
        self, text: str
    ) -> Tuple[Optional[CommandDefinition], float, dict]:
        best_cmd = None
        best_score = 0.0
        best_args: dict = {}
        text_lower = text.lower()

        for cmd in self._commands:
            # 1. Regex match (score = 1.0 if any pattern hits)
            for pattern in cmd.compiled_patterns():
                m = pattern.search(text_lower)
                if m:
                    return cmd, 1.0, m.groupdict()

            # 2. Fuzzy keyword scoring
            score = self._keyword_score(text_lower, cmd.keywords)
            if score > best_score:
                best_score = score
                best_cmd = cmd
                best_args = {}

        return best_cmd, best_score, best_args

    def _keyword_score(self, text: str, keywords: List[str]) -> float:
        if not keywords:
            return 0.0
        scores = []
        words = text.split()
        for kw in keywords:
            # exact substring
            if kw.lower() in text:
                scores.append(1.0)
                continue
            # fuzzy over each word
            best = max(
                SequenceMatcher(None, kw.lower(), w).ratio()
                for w in words
            ) if words else 0.0
            scores.append(best)
        return sum(scores) / len(scores)

    # ── LLM Fallback ─────────────────────────────────────────────────────────

    def _llm_dispatch(self, text: str) -> bool:
        """Ask a local Ollama LLM to pick the right command."""
        cmd_list = "\n".join(
            f"- {c.name}: {c.description}" for c in self._commands
        )
        prompt = (
            f"Available desktop commands:\n{cmd_list}\n\n"
            f"User said: \"{text}\"\n\n"
            "Reply with ONLY the command name that best matches, or 'none'."
        )
        try:
            response = ollama.chat(
                model="phi3:mini",      # ~2GB, fast on CPU
                messages=[{"role": "user", "content": prompt}],
            )
            chosen = response["message"]["content"].strip().lower()
            self.log.info(f"LLM chose: '{chosen}'")
            for cmd in self._commands:
                if cmd.name.lower() == chosen:
                    cmd.handler()
                    return True
        except Exception as exc:
            self.log.warning(f"LLM dispatch failed: {exc}")
        return False

    # ── Built-in Command Registration ────────────────────────────────────────

    def _register_builtin_commands(self) -> None:
        ex = self.executor
        speak = self.tts.speak

        defs = [
            # ── System ───────────────────────────────────────────────────────
            CommandDefinition(
                name="open_app",
                patterns=[r"open (?P<app>\w[\w\s]*)"],
                keywords=["open", "launch", "start", "run"],
                handler=lambda app="application": (
                    ex.open_application(app),
                    speak(f"Opening {app}."),
                ),
                description="Open an application by name",
                category="system",
                example_phrases=["open chrome", "launch terminal", "start spotify"],
            ),
            CommandDefinition(
                name="close_app",
                patterns=[r"close (?P<app>\w[\w\s]*)", r"quit (?P<app>\w[\w\s]*)"],
                keywords=["close", "quit", "exit", "kill"],
                handler=lambda app="window": (
                    ex.close_application(app),
                    speak(f"Closing {app}."),
                ),
                description="Close a running application",
                category="system",
                example_phrases=["close chrome", "quit terminal"],
            ),
            CommandDefinition(
                name="screenshot",
                patterns=[r"(take a? ?)?screenshot", r"capture (the )?screen"],
                keywords=["screenshot", "capture", "screen", "snap"],
                handler=lambda: (
                    path := ex.take_screenshot(),
                    speak(f"Screenshot saved."),
                ),
                description="Take a screenshot and save to Desktop",
                category="system",
                example_phrases=["take a screenshot", "capture screen"],
            ),
            CommandDefinition(
                name="lock_screen",
                patterns=[r"lock( the)? (screen|computer|pc|machine)"],
                keywords=["lock", "screen", "secure"],
                handler=lambda: (
                    ex.lock_screen(),
                    speak("Locking screen."),
                ),
                description="Lock the screen",
                category="security",
                example_phrases=["lock the screen", "lock computer"],
            ),
            # ── Volume ───────────────────────────────────────────────────────
            CommandDefinition(
                name="volume_up",
                patterns=[r"volume up", r"(turn|crank) (it |the volume )?up", r"louder"],
                keywords=["volume", "up", "louder", "increase"],
                handler=lambda: (
                    ex.volume_up(),
                    speak("Volume up."),
                ),
                description="Increase system volume",
                category="media",
                example_phrases=["volume up", "louder"],
            ),
            CommandDefinition(
                name="volume_down",
                patterns=[r"volume down", r"(turn|crank) (it |the volume )?down", r"quieter"],
                keywords=["volume", "down", "quieter", "decrease"],
                handler=lambda: (
                    ex.volume_down(),
                    speak("Volume down."),
                ),
                description="Decrease system volume",
                category="media",
                example_phrases=["volume down", "quieter"],
            ),
            CommandDefinition(
                name="mute",
                patterns=[r"(mute|unmute)( (the )?(volume|sound|audio))?"],
                keywords=["mute", "unmute", "silence"],
                handler=lambda: (
                    ex.mute_toggle(),
                    speak("Muted."),
                ),
                description="Toggle mute on system audio",
                category="media",
                example_phrases=["mute", "unmute"],
            ),
            # ── Files ────────────────────────────────────────────────────────
            CommandDefinition(
                name="new_note",
                patterns=[r"new (note|text file|document)", r"create a? (note|file)"],
                keywords=["new", "note", "create", "text", "file"],
                handler=lambda: (
                    path := ex.create_text_file(),
                    speak(f"New note created at {path}."),
                ),
                description="Create a new empty text file",
                category="files",
                example_phrases=["new note", "create a text file"],
            ),
            CommandDefinition(
                name="backup",
                patterns=[r"backup( (my )?(files|data|documents))?", r"back up"],
                keywords=["backup", "back", "up", "archive", "save"],
                handler=lambda: (
                    result := ex.backup_files(),
                    speak(f"Backup complete. {result}"),
                ),
                description="Zip and archive important files",
                category="files",
                example_phrases=["backup now", "back up my files"],
            ),
            CommandDefinition(
                name="empty_trash",
                patterns=[r"empty (the )?(trash|recycle ?bin)"],
                keywords=["empty", "trash", "recycle", "bin", "delete"],
                handler=lambda: (
                    ex.empty_trash(),
                    speak("Trash emptied."),
                ),
                description="Empty the system trash/recycle bin",
                category="files",
                example_phrases=["empty trash"],
            ),
            # ── UI / Windows ─────────────────────────────────────────────────
            CommandDefinition(
                name="show_desktop",
                patterns=[r"show (the )?desktop", r"minimize all( windows)?"],
                keywords=["desktop", "minimize", "show", "windows"],
                handler=lambda: (
                    ex.show_desktop(),
                    speak("Showing desktop."),
                ),
                description="Minimize all open windows",
                category="ui",
                example_phrases=["show desktop", "minimize all"],
            ),
            CommandDefinition(
                name="zoom_in",
                patterns=[r"zoom in", r"make (it |this |the screen )?bigger"],
                keywords=["zoom", "in", "bigger", "enlarge"],
                handler=lambda: ex.zoom_in(),
                description="Zoom in (Ctrl + +)",
                category="ui",
                example_phrases=["zoom in", "make it bigger"],
            ),
            CommandDefinition(
                name="zoom_out",
                patterns=[r"zoom out", r"make (it |this |the screen )?smaller"],
                keywords=["zoom", "out", "smaller", "shrink"],
                handler=lambda: ex.zoom_out(),
                description="Zoom out (Ctrl + -)",
                category="ui",
                example_phrases=["zoom out", "make it smaller"],
            ),
            CommandDefinition(
                name="scroll_down",
                patterns=[r"scroll down", r"page down"],
                keywords=["scroll", "down", "page"],
                handler=lambda: ex.scroll(direction="down", clicks=5),
                description="Scroll down in the current window",
                category="ui",
                example_phrases=["scroll down", "page down"],
            ),
            CommandDefinition(
                name="scroll_up",
                patterns=[r"scroll up", r"page up"],
                keywords=["scroll", "up", "page"],
                handler=lambda: ex.scroll(direction="up", clicks=5),
                description="Scroll up in the current window",
                category="ui",
                example_phrases=["scroll up", "page up"],
            ),
            # ── Browser ──────────────────────────────────────────────────────
            CommandDefinition(
                name="new_tab",
                patterns=[r"new tab", r"open (a )?new tab"],
                keywords=["new", "tab", "open"],
                handler=lambda: ex.hotkey("ctrl", "t"),
                description="Open a new browser tab",
                category="browser",
                example_phrases=["new tab", "open a new tab"],
            ),
            CommandDefinition(
                name="close_tab",
                patterns=[r"close (this |the )?tab"],
                keywords=["close", "tab"],
                handler=lambda: ex.hotkey("ctrl", "w"),
                description="Close the current browser tab",
                category="browser",
                example_phrases=["close tab", "close this tab"],
            ),
            CommandDefinition(
                name="next_tab",
                patterns=[r"next tab", r"switch tab"],
                keywords=["next", "tab", "switch"],
                handler=lambda: ex.hotkey("ctrl", "tab"),
                description="Switch to the next tab",
                category="browser",
                example_phrases=["next tab"],
            ),
            # ── Dev ──────────────────────────────────────────────────────────
            CommandDefinition(
                name="open_terminal",
                patterns=[r"open (a? ?(new )?terminal|bash|shell|command ?line)"],
                keywords=["terminal", "bash", "shell", "console", "command"],
                handler=lambda: (
                    ex.open_terminal(),
                    speak("Terminal opened."),
                ),
                description="Open a terminal window",
                category="dev",
                example_phrases=["open terminal", "open bash"],
            ),
            CommandDefinition(
                name="run_script",
                patterns=[r"run (script|file)( (?P<script>\S+))?"],
                keywords=["run", "script", "execute", "file"],
                handler=lambda script="": (
                    ex.run_script(script),
                    speak(f"Running script {script or 'default'}."),
                ),
                description="Execute a shell script by name",
                category="dev",
                example_phrases=["run script deploy.sh"],
            ),
            # ── Input ────────────────────────────────────────────────────────
            CommandDefinition(
                name="type_text",
                patterns=[r"type (?P<text>.+)", r"write (?P<text>.+)"],
                keywords=["type", "write", "input"],
                handler=lambda text="": ex.type_text(text),
                description="Type text into the active field",
                category="input",
                example_phrases=["type hello world", "write my name"],
            ),
            # ── Productivity ─────────────────────────────────────────────────
            CommandDefinition(
                name="focus_mode",
                patterns=[r"(enable|activate|start|turn on) focus( mode)?"],
                keywords=["focus", "mode", "do not disturb", "dnd"],
                handler=lambda: (
                    ex.focus_mode_on(),
                    speak("Focus mode activated. Distractions blocked."),
                ),
                description="Enable focus mode — block distracting apps",
                category="productivity",
                example_phrases=["enable focus mode", "turn on focus"],
            ),
            # ── System info ──────────────────────────────────────────────────
            CommandDefinition(
                name="what_time",
                patterns=[r"what( is|'s) the time", r"current time"],
                keywords=["time", "clock", "what"],
                handler=lambda: (
                    __import__("datetime").datetime.now().strftime("%I:%M %p"),
                    speak(
                        "The time is "
                        + __import__("datetime").datetime.now().strftime("%I:%M %p")
                    ),
                ),
                description="Read the current time aloud",
                category="info",
                example_phrases=["what time is it", "current time"],
            ),
        ]

        for d in defs:
            self.register(d)
