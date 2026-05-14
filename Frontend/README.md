# VOXEL Frontend — Electron + React

Frameless desktop UI for the VOXEL offline voice assistant.

## Stack
- **Electron 30** — native desktop shell, spawns Python backend
- **React 18** — UI framework  
- **Vite 5** — fast dev server + bundler
- **Zustand** — lightweight global state
- **Framer Motion** — animations
- **WebSocket** — real-time bridge to Python backend (`ws://localhost:8765`)

## Project Structure

```
voxel-frontend/
├── electron/
│   ├── main.js        # Electron main process — window + Python spawn
│   └── preload.js     # Secure IPC bridge (contextBridge)
│
├── src/
│   ├── App.jsx                    # Root layout
│   ├── main.jsx                   # React entry
│   ├── styles/global.css          # Design tokens + global styles
│   │
│   ├── hooks/
│   │   └── useVoxelSocket.js      # WebSocket hook → store updates
│   │
│   ├── stores/
│   │   └── voxelStore.js          # Zustand global state
│   │
│   └── components/
│       ├── TitleBar.jsx/css        # Custom frameless titlebar
│       ├── Sidebar.jsx/css         # Navigation + stats footer
│       ├── VoicePanel.jsx/css      # Mic orb, waveform, transcript
│       ├── CommandsPanel.jsx/css   # Searchable command grid
│       ├── FlowsPanel.jsx/css      # Automation flow toggles
│       ├── LogPanel.jsx/css        # Real-time activity log
│       └── SettingsPanel.jsx       # Settings with live backend sync
│
├── ws_server.py       # Copy into Python backend: core/ws_server.py
├── index.html
├── vite.config.js
└── package.json
```

## Setup

```bash
npm install

# Development (opens Electron + hot-reload Vite)
npm run dev

# Production build
npm run build
```

## WebSocket Protocol

The Python backend must run `WSServer` on `ws://localhost:8765`.

**Copy `ws_server.py` → `voxel/core/ws_server.py`** and add to `main.py`:

```python
from core.ws_server import WSServer

ws_server = WSServer(engine=engine, router=router, tts=tts, logger=logger)
ws_server.start()

# Then wire events into engine.py:
ws_server.emit_status("listening")       # when mic activates
ws_server.emit_transcript(text)          # after Whisper
ws_server.emit_response("Opening...")    # after TTS
ws_server.emit_command("open_app", True) # after executor
ws_server.emit_waveform(rms_value)       # every audio chunk
```

## Window Controls

The app uses a **frameless window** (`frame: false`) with a custom titlebar.
The titlebar is `-webkit-app-region: drag` so users can drag the window.
Window buttons (minimise/maximise/close) call Electron IPC via `window.voxel.*`.

## Building for Distribution

```bash
npm run build
# Output: dist-electron/
# Creates: .dmg (macOS), .AppImage/.deb (Linux), .exe (Windows)
```
