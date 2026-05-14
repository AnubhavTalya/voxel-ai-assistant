# VOXEL — Offline Voice-Controlled AI Assistant

A fully **offline**, privacy-first voice assistant for desktop automation.
Zero cloud calls. All speech recognition, TTS, and automation runs locally.

```
┌─────────────────────────────────────────────────────────────────┐
│  Microphone  →  Whisper.cpp  →  CommandRouter  →  Executor      │
│               (offline STT)   (regex + fuzzy)   (PyAutoGUI)     │
│                                     ↓                           │
│               WakeWordDetector  →  TTS (pyttsx3)                │
│               (openWakeWord)    (offline speech)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/you/voxel
cd voxel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Linux audio:** `sudo apt install portaudio19-dev python3-pyaudio espeak`
> **macOS:** `brew install portaudio`

### 2. Configure

```bash
cp config.yaml.example ~/.voxel/config.yaml
# Edit ~/.voxel/config.yaml to set your whisper model, wake word, etc.
```

### 3. Run

```bash
python main.py
```

Say **"Hey Voxel"** (wake word), then your command.

---

## Project Structure

```
voxel/
├── main.py                   # Entry point
├── requirements.txt
├── config.yaml.example
│
├── config/
│   └── settings.py           # YAML + env-var config loader
│
├── core/
│   ├── engine.py             # Audio capture + Whisper transcription
│   ├── wake_word.py          # openWakeWord / Porcupine / fuzzy fallback
│   └── command_router.py     # Intent matching + dispatch
│
├── automation/
│   └── executor.py           # PyAutoGUI + OS-specific actions
│
├── utils/
│   ├── tts.py                # pyttsx3 / espeak / macOS say
│   └── logger.py             # Coloured rotating logger
│
└── tests/
    └── test_command_router.py
```

---

## Voice Commands

| Category | Say… | Action |
|---|---|---|
| System | "open chrome" | Launch Chrome |
| System | "close terminal" | Kill process |
| System | "screenshot" | Save PNG to Desktop |
| Security | "lock the screen" | Lock workstation |
| Media | "volume up / down" | ±10% system volume |
| Media | "mute" | Toggle mute |
| Files | "new note" | Create text file |
| Files | "backup now" | Zip & archive |
| Files | "empty trash" | Clear recycle bin |
| Browser | "new tab / close tab / next tab" | Tab management |
| Dev | "open terminal" | Launch shell |
| Dev | "run script deploy.sh" | Execute shell script |
| Input | "type hello world" | Type into focused field |
| UI | "zoom in / zoom out" | Ctrl+/- |
| UI | "scroll down / up" | Scroll active window |
| UI | "show desktop" | Minimise all windows |
| Productivity | "enable focus mode" | Block distracting apps |
| Info | "what time is it" | Read current time |

---

## Whisper Model Sizes

| Model | Size | Speed (CPU) | Accuracy |
|---|---|---|---|
| `tiny.en` | ~75 MB | ~30ms | Good |
| `base.en` | ~142 MB | ~80ms | Better ← **default** |
| `small.en` | ~466 MB | ~200ms | Great |
| `medium.en` | ~1.5 GB | ~500ms | Excellent |

Install the model once — it's cached automatically.

---

## Adding Custom Commands

```python
from core.command_router import CommandDefinition

router.register(CommandDefinition(
    name="good_morning",
    patterns=[r"good morning", r"morning routine"],
    keywords=["morning", "routine"],
    handler=lambda: executor.run_script("~/scripts/morning.sh"),
    description="Run morning routine script",
    category="productivity",
    example_phrases=["good morning", "start morning routine"],
))
```

---

## Optional Enhancements

| Feature | Package | Notes |
|---|---|---|
| Better wake word | `pip install openwakeword` | Free, accurate |
| Custom wake word | Picovoice Console | Export `.ppn` file |
| LLM fallback | `pip install ollama` + `ollama pull phi3:mini` | For complex commands |
| Better TTS voices | `pip install TTS` (Coqui) | Neural, offline |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Privacy

- **No audio ever leaves the device.** Whisper runs fully locally.
- No internet access required after initial model download.
- Logs stored at `~/.voxel/voxel.log` (local only).
