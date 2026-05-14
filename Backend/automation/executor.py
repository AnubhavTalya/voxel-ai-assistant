"""
automation/executor.py — Cross-platform desktop automation.

Wraps PyAutoGUI + platform-specific calls (xdotool, AppleScript, Win32)
into a clean unified API consumed by the CommandRouter handlers.

Supported platforms:
  - Linux   (X11 / Wayland via xdotool / wmctrl)
  - macOS   (AppleScript via osascript)
  - Windows (pywinauto / Win32 API via ctypes)
"""

from __future__ import annotations

import datetime
import logging
import os
import platform
import shlex
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Optional

try:
    import pyautogui
    pyautogui.FAILSAFE = True      # move mouse to top-left corner to abort
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


OS = platform.system()   # "Linux", "Darwin", "Windows"


class AutomationExecutor:
    """
    Unified desktop automation layer.  All public methods are safe to call
    even if optional dependencies are missing — they log a warning instead
    of raising.
    """

    def __init__(
        self,
        logger: logging.Logger,
        screenshot_dir: Path = Path.home() / "Desktop",
        backup_dir: Path = Path.home() / "Backups",
        automation_delay: float = 0.05,
    ):
        self.log = logger
        self.screenshot_dir = Path(screenshot_dir)
        self.backup_dir = Path(backup_dir)
        self.automation_delay = automation_delay

        if not PYAUTOGUI_AVAILABLE:
            self.log.warning("PyAutoGUI not installed: pip install pyautogui")

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _run(self, cmd: str | list, check: bool = False) -> subprocess.CompletedProcess:
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        self.log.debug(f"$ {' '.join(cmd)}")
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )

    def _require_pyautogui(self, action: str) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            self.log.error(f"PyAutoGUI required for '{action}': pip install pyautogui")
            return False
        return True

    # ── Applications ─────────────────────────────────────────────────────────

    def open_application(self, app: str) -> None:
        """Launch an application by name (cross-platform)."""
        app = app.strip().lower()
        self.log.info(f"Opening application: {app}")

        if OS == "Linux":
            # Try xdg-open / known mappings
            app_map = {
                "chrome": "google-chrome",
                "browser": "xdg-open https://",
                "firefox": "firefox",
                "terminal": "x-terminal-emulator",
                "files": "nautilus",
                "calculator": "gnome-calculator",
                "text editor": "gedit",
                "spotify": "spotify",
                "vscode": "code",
            }
            cmd = app_map.get(app, app)
            self._run(cmd)

        elif OS == "Darwin":
            self._run(f"open -a '{app}'")

        elif OS == "Windows":
            os.startfile(app)   # type: ignore[attr-defined]

    def close_application(self, app: str) -> None:
        self.log.info(f"Closing: {app}")
        if OS == "Linux":
            self._run(f"pkill -f {app}")
        elif OS == "Darwin":
            self._run(f"osascript -e 'quit app \"{app}\"'")
        elif OS == "Windows":
            self._run(f"taskkill /IM {app}.exe /F")

    def open_terminal(self) -> None:
        self.log.info("Opening terminal")
        if OS == "Linux":
            for term in ("x-terminal-emulator", "gnome-terminal", "xterm", "konsole"):
                if shutil.which(term):
                    self._run(term)
                    return
        elif OS == "Darwin":
            self._run("open -a Terminal")
        elif OS == "Windows":
            self._run("start cmd")

    # ── Screen ───────────────────────────────────────────────────────────────

    def take_screenshot(self) -> Optional[Path]:
        self.log.info("Taking screenshot")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.screenshot_dir / f"screenshot_{ts}.png"

        if PYAUTOGUI_AVAILABLE:
            img = pyautogui.screenshot()
            img.save(str(dest))
            self.log.info(f"Screenshot saved: {dest}")
            return dest

        if OS == "Linux" and shutil.which("scrot"):
            self._run(f"scrot '{dest}'")
            return dest

        if OS == "Darwin":
            self._run(f"screencapture '{dest}'")
            return dest

        if OS == "Windows":
            self._run(f"snippingtool /clip")
            return None

        self.log.warning("No screenshot tool available.")
        return None

    def lock_screen(self) -> None:
        self.log.info("Locking screen")
        if OS == "Linux":
            for cmd in ("gnome-screensaver-command -l", "xdg-screensaver lock",
                        "loginctl lock-session", "i3lock"):
                prog = cmd.split()[0]
                if shutil.which(prog):
                    self._run(cmd)
                    return
        elif OS == "Darwin":
            self._run(
                "osascript -e 'tell application \"System Events\" to keystroke \"q\" "
                "using {command down, control down}'"
            )
        elif OS == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()  # type: ignore

    # ── Volume ───────────────────────────────────────────────────────────────

    def volume_up(self, step: int = 10) -> None:
        self.log.info(f"Volume up +{step}%")
        if OS == "Linux":
            self._run(f"amixer -D pulse sset Master {step}%+")
        elif OS == "Darwin":
            # osascript increment by ~step / 100 * 7 ≈ 1 notch
            self._run(
                "osascript -e 'set volume output volume "
                f"(output volume of (get volume settings) + {step})'"
            )
        elif OS == "Windows" and PYAUTOGUI_AVAILABLE:
            for _ in range(step // 2):
                pyautogui.press("volumeup")

    def volume_down(self, step: int = 10) -> None:
        self.log.info(f"Volume down -{step}%")
        if OS == "Linux":
            self._run(f"amixer -D pulse sset Master {step}%-")
        elif OS == "Darwin":
            self._run(
                "osascript -e 'set volume output volume "
                f"(output volume of (get volume settings) - {step})'"
            )
        elif OS == "Windows" and PYAUTOGUI_AVAILABLE:
            for _ in range(step // 2):
                pyautogui.press("volumedown")

    def mute_toggle(self) -> None:
        self.log.info("Toggling mute")
        if OS == "Linux":
            self._run("amixer -D pulse sset Master toggle")
        elif OS == "Darwin":
            self._run("osascript -e 'set volume output muted not (output muted of (get volume settings))'")
        elif OS == "Windows" and PYAUTOGUI_AVAILABLE:
            pyautogui.press("volumemute")

    # ── Files ────────────────────────────────────────────────────────────────

    def create_text_file(self) -> Path:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path.home() / "Desktop" / f"note_{ts}.txt"
        path.touch()
        self.log.info(f"Created text file: {path}")
        # Open in default text editor
        if OS == "Linux":
            self._run(f"xdg-open '{path}'")
        elif OS == "Darwin":
            self._run(f"open '{path}'")
        elif OS == "Windows":
            os.startfile(str(path))   # type: ignore
        return path

    def backup_files(
        self,
        source_dirs: Optional[list] = None,
        max_size_mb: int = 500,
    ) -> str:
        """Zip source_dirs (default: ~/Documents, ~/Desktop) into backup_dir."""
        if source_dirs is None:
            source_dirs = [
                Path.home() / "Documents",
                Path.home() / "Desktop",
            ]
        source_dirs = [Path(d) for d in source_dirs if Path(d).exists()]

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = self.backup_dir / f"backup_{ts}.zip"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        file_count = 0
        total_size = 0

        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for src in source_dirs:
                for fpath in src.rglob("*"):
                    if fpath.is_file():
                        size = fpath.stat().st_size
                        total_size += size
                        if total_size > max_size_mb * 1024 * 1024:
                            self.log.warning("Backup size limit reached; stopping.")
                            break
                        zf.write(fpath, fpath.relative_to(fpath.anchor))
                        file_count += 1

        size_mb = archive.stat().st_size / 1024 / 1024
        msg = f"{file_count} files archived ({size_mb:.1f} MB) → {archive.name}"
        self.log.info(f"Backup complete: {msg}")
        return msg

    def empty_trash(self) -> None:
        self.log.info("Emptying trash")
        if OS == "Linux":
            trash = Path.home() / ".local" / "share" / "Trash"
            for sub in ("files", "info", "expunged"):
                d = trash / sub
                if d.exists():
                    for item in d.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
        elif OS == "Darwin":
            self._run("osascript -e 'tell app \"Finder\" to empty trash'")
        elif OS == "Windows":
            self._run("PowerShell.exe -Command Clear-RecycleBin -Force")

    # ── UI / Windows ─────────────────────────────────────────────────────────

    def show_desktop(self) -> None:
        self.log.info("Showing desktop")
        if OS == "Linux":
            self._run("wmctrl -k on")
        elif OS == "Darwin" and PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("f11")
        elif OS == "Windows" and PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("win", "d")

    def zoom_in(self) -> None:
        if self._require_pyautogui("zoom_in"):
            pyautogui.hotkey("ctrl", "+")

    def zoom_out(self) -> None:
        if self._require_pyautogui("zoom_out"):
            pyautogui.hotkey("ctrl", "-")

    def scroll(self, direction: str = "down", clicks: int = 5) -> None:
        if self._require_pyautogui("scroll"):
            amount = -clicks if direction == "down" else clicks
            pyautogui.scroll(amount)

    def hotkey(self, *keys: str) -> None:
        """Press a keyboard shortcut, e.g. hotkey('ctrl', 't')."""
        if self._require_pyautogui("hotkey"):
            pyautogui.hotkey(*keys)
            self.log.debug(f"Hotkey: {'+'.join(keys)}")

    def type_text(self, text: str) -> None:
        if self._require_pyautogui("type_text"):
            pyautogui.write(text, interval=0.03)

    # ── Dev ──────────────────────────────────────────────────────────────────

    def run_script(self, script: str) -> None:
        path = Path(script).expanduser()
        if not path.exists():
            # Check ~/scripts/ folder too
            alt = Path.home() / "scripts" / script
            if alt.exists():
                path = alt
            else:
                self.log.error(f"Script not found: {script}")
                return
        self.log.info(f"Running script: {path}")
        self._run(f"bash '{path}'")

    # ── Productivity ─────────────────────────────────────────────────────────

    def focus_mode_on(self) -> None:
        self.log.info("Enabling focus mode")
        distracting = ["spotify", "slack", "discord", "telegram", "twitter"]
        for app in distracting:
            if OS == "Linux":
                self._run(f"pkill -f {app}")
            elif OS == "Darwin":
                self._run(f"osascript -e 'quit app \"{app}\"'")
            elif OS == "Windows":
                self._run(f"taskkill /IM {app}.exe /F")
        # Set DND notification on Linux (GNOME)
        if OS == "Linux":
            self._run(
                "gsettings set org.gnome.desktop.notifications show-banners false"
            )
