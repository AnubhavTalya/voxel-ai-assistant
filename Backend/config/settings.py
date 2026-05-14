"""
config/settings.py — Loads VOXEL configuration from YAML or environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

DEFAULT_CONFIG_PATH = Path.home() / ".voxel" / "config.yaml"


@dataclass
class Settings:
    # Speech recognition
    whisper_model: str = "base.en"          # tiny.en / base.en / small.en / medium.en
    sample_rate: int = 16_000
    silence_threshold: float = 0.02         # RMS amplitude below this = silence
    silence_duration: float = 1.2           # seconds of silence to end utterance
    language: str = "en"

    # Wake word (openWakeWord / Porcupine keyword)
    wake_word: str = "hey voxel"
    wake_word_sensitivity: float = 0.7
    always_on: bool = False                 # skip wake-word, always listen

    # TTS
    tts_enabled: bool = True
    tts_rate: int = 175                     # words per minute
    tts_volume: float = 0.9

    # Logging
    debug: bool = False
    log_file: Optional[Path] = Path.home() / ".voxel" / "voxel.log"

    # Automation
    automation_delay: float = 0.05          # seconds between simulated key/mouse events
    screenshot_dir: Path = Path.home() / "Desktop"
    backup_dir: Path = Path.home() / "Backups"

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Settings":
        """Load from YAML config file, falling back to defaults then env vars."""
        raw: dict = {}

        if YAML_AVAILABLE and path.exists():
            with open(path) as fh:
                raw = yaml.safe_load(fh) or {}

        # Env-var overrides (VOXEL_WHISPER_MODEL, VOXEL_WAKE_WORD, etc.)
        env_map = {
            "VOXEL_WHISPER_MODEL": "whisper_model",
            "VOXEL_WAKE_WORD": "wake_word",
            "VOXEL_ALWAYS_ON": "always_on",
            "VOXEL_TTS_ENABLED": "tts_enabled",
            "VOXEL_DEBUG": "debug",
            "VOXEL_SAMPLE_RATE": "sample_rate",
        }
        for env_key, attr in env_map.items():
            val = os.getenv(env_key)
            if val is not None:
                # Cast booleans and ints
                if attr in ("always_on", "tts_enabled", "debug"):
                    val = val.lower() in ("1", "true", "yes")
                elif attr == "sample_rate":
                    val = int(val)
                raw[attr] = val

        inst = cls()
        for key, value in raw.items():
            if hasattr(inst, key):
                # Coerce Path fields
                if key in ("log_file", "screenshot_dir", "backup_dir"):
                    value = Path(value)
                setattr(inst, key, value)

        # Ensure directories exist
        for dir_attr in ("screenshot_dir", "backup_dir"):
            getattr(inst, dir_attr).mkdir(parents=True, exist_ok=True)
        if inst.log_file:
            inst.log_file.parent.mkdir(parents=True, exist_ok=True)

        return inst

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        """Persist current settings back to YAML."""
        if not YAML_AVAILABLE:
            raise RuntimeError("PyYAML is required to save settings: pip install pyyaml")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            k: str(v) if isinstance(v, Path) else v
            for k, v in self.__dict__.items()
        }
        with open(path, "w") as fh:
            yaml.dump(data, fh, default_flow_style=False)
