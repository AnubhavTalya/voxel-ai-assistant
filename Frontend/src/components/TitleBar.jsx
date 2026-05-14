/**
 * src/components/TitleBar.jsx
 * Custom frameless titlebar — draggable, with status indicators & window buttons.
 */

import { useVoxelStore } from '@/stores/voxelStore'
import './TitleBar.css'

const STATUS_LABELS = {
  idle:         { label: 'IDLE',        cls: 'idle'   },
  listening:    { label: 'LISTENING',   cls: 'active' },
  processing:   { label: 'PROCESSING',  cls: 'active' },
  speaking:     { label: 'SPEAKING',    cls: 'active' },
  disconnected: { label: 'OFFLINE',     cls: 'warn'   },
}

export default function TitleBar() {
  const status    = useVoxelStore((s) => s.status)
  const connected = useVoxelStore((s) => s.connected)
  const cmdCount  = useVoxelStore((s) => s.commandCount)
  const s = STATUS_LABELS[status] || STATUS_LABELS.idle

  const ctrl = window.voxel ?? {
    minimize: () => {}, maximize: () => {}, close: () => {},
  }

  return (
    <header className="titlebar" data-tauri-drag-region>
      <div className="titlebar-left">
        <div className="titlebar-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-name">VOXEL</span>
          <span className="logo-sub">/ desktop ai</span>
        </div>
      </div>

      <div className="titlebar-center" data-tauri-drag-region>
        <div className={`status-pill status-${s.cls}`}>
          <span className="dot-pulse" />
          {s.label}
        </div>
        {connected && (
          <div className="status-pill status-teal" style={{ marginLeft: 8 }}>
            <span className="dot-pulse" style={{ background: 'var(--accent)' }} />
            BACKEND LIVE
          </div>
        )}
      </div>

      <div className="titlebar-right">
        <span className="stat-chip">
          <span className="stat-val">{cmdCount}</span>
          <span className="stat-lbl">cmds</span>
        </span>
        <div className="win-btn win-min" onClick={ctrl.minimize} title="Minimise">─</div>
        <div className="win-btn win-max" onClick={ctrl.maximize} title="Maximise">⬜</div>
        <div className="win-btn win-close" onClick={ctrl.close} title="Close">✕</div>
      </div>
    </header>
  )
}
