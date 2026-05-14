"""
tests/test_command_router.py — Unit tests for the CommandRouter.

Run with: pytest tests/ -v
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from core.command_router import CommandRouter, CommandDefinition


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_executor():
    ex = MagicMock()
    ex.take_screenshot.return_value = "/tmp/shot.png"
    ex.backup_files.return_value = "5 files archived (1.2 MB)"
    return ex


@pytest.fixture
def mock_tts():
    tts = MagicMock()
    return tts


@pytest.fixture
def router(mock_executor, mock_tts):
    logger = logging.getLogger("test")
    return CommandRouter(
        executor=mock_executor,
        tts=mock_tts,
        logger=logger,
    )


# ── Tests: command registration ───────────────────────────────────────────────

def test_builtin_commands_registered(router):
    names = [c.name for c in router.list_commands()]
    assert "screenshot" in names
    assert "volume_up" in names
    assert "lock_screen" in names
    assert "open_app" in names


def test_custom_command_registration(router, mock_executor, mock_tts):
    called = []

    def handler():
        called.append(True)

    router.register(CommandDefinition(
        name="test_cmd",
        patterns=[r"run test"],
        keywords=["test", "run"],
        handler=handler,
        description="Test command",
    ))

    router.dispatch("run test now")
    assert called, "Custom command handler should have been called."


# ── Tests: regex matching ─────────────────────────────────────────────────────

@pytest.mark.parametrize("phrase,expected_name", [
    ("take a screenshot", "screenshot"),
    ("screenshot", "screenshot"),
    ("open chrome", "open_app"),
    ("open terminal please", "open_terminal"),
    ("volume up", "volume_up"),
    ("volume down", "volume_down"),
    ("mute the audio", "mute"),
    ("lock the screen", "lock_screen"),
    ("backup now", "backup"),
    ("backup my files", "backup"),
    ("new note", "new_note"),
    ("enable focus mode", "focus_mode"),
    ("zoom in", "zoom_in"),
    ("scroll down", "scroll_down"),
    ("close tab", "close_tab"),
    ("next tab", "next_tab"),
    ("show desktop", "show_desktop"),
    ("what is the time", "what_time"),
    ("empty the trash", "empty_trash"),
    ("type hello world", "type_text"),
])
def test_regex_dispatch(router, mock_executor, mock_tts, phrase, expected_name):
    match, confidence, _ = router._best_match(phrase)
    assert match is not None, f"No match for: '{phrase}'"
    assert match.name == expected_name, (
        f"'{phrase}' → expected '{expected_name}', got '{match.name}' (conf={confidence:.2f})"
    )
    assert confidence == 1.0, "Regex matches should have confidence 1.0"


# ── Tests: fuzzy matching ─────────────────────────────────────────────────────

@pytest.mark.parametrize("phrase", [
    "take screenshoot",   # typo
    "screeenshot",        # double letter
    "backup fil",         # truncated
])
def test_fuzzy_fallback(router, phrase):
    match, confidence, _ = router._best_match(phrase)
    assert match is not None
    assert confidence > 0.2, f"Expected some confidence for '{phrase}'"


# ── Tests: unknown input ──────────────────────────────────────────────────────

def test_unknown_command_speaks(router, mock_tts):
    router.dispatch("xyzzy plugh frobozz")
    mock_tts.speak.assert_called()
    args = mock_tts.speak.call_args[0][0].lower()
    assert "sorry" in args or "understand" in args


# ── Tests: dispatch calls executor ───────────────────────────────────────────

def test_screenshot_calls_executor(router, mock_executor):
    router.dispatch("take a screenshot")
    mock_executor.take_screenshot.assert_called_once()


def test_volume_up_calls_executor(router, mock_executor):
    router.dispatch("volume up")
    mock_executor.volume_up.assert_called_once()


def test_open_app_passes_name(router, mock_executor):
    router.dispatch("open firefox")
    mock_executor.open_application.assert_called_once_with("firefox")


def test_lock_screen_calls_executor(router, mock_executor):
    router.dispatch("lock the screen")
    mock_executor.lock_screen.assert_called_once()
