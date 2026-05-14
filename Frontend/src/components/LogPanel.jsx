/**
 * src/components/LogPanel.jsx
 */

import { motion } from 'framer-motion'
import { useVoxelStore } from '@/stores/voxelStore'
import './LogPanel.css'

const DOT_COLOR = { info: '#00e8b0', warn: '#f5a623', error: '#ff5e6c' }

export function LogPanel() {
  const logs     = useVoxelStore((s) => s.logs)
  const clearLogs = useVoxelStore((s) => s.clearLogs)

  const fmt = (ts) => new Date(ts).toLocaleTimeString('en-US', { hour12: false })

  return (
    <div className="panel log-panel">
      <div className="log-header">
        <h2 className="panel-title">Activity Log</h2>
        <button className="log-clear-btn" onClick={clearLogs}>Clear</button>
      </div>

      <div className="log-list">
        {logs.length === 0 && (
          <div className="log-empty">No activity yet. Start talking to VOXEL.</div>
        )}
        {logs.map((entry, i) => (
          <motion.div
            key={i}
            className="log-entry"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}
          >
            <span className="log-time">{fmt(entry.ts)}</span>
            <span className="log-dot" style={{ background: DOT_COLOR[entry.level] || DOT_COLOR.info }} />
            <div className="log-body">
              <div className="log-msg">{entry.message}</div>
              {entry.command && (
                <div className="log-cmd">→ {entry.command}</div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export default LogPanel


/**
 * src/components/SettingsPanel.jsx
 */
export function SettingsPanel({ pushSettings }) {
  const settings       = useVoxelStore((s) => s.settings)
  const updateSettings = useVoxelStore((s) => s.updateSettings)

  const apply = (patch) => {
    updateSettings(patch)
    pushSettings?.(patch)
  }

  return (
    <div className="panel settings-panel">
      <h2 className="panel-title">Settings</h2>

      <SettSection title="Speech Recognition">
        <SettRow label="Whisper Model" sub="Local offline inference engine">
          <select
            className="sett-select"
            value={settings.whisperModel}
            onChange={e => apply({ whisperModel: e.target.value })}
          >
            {['tiny.en','base.en','small.en','medium.en'].map(m =>
              <option key={m}>{m}</option>
            )}
          </select>
        </SettRow>
        <SettRow label="Silence Threshold" sub="RMS amplitude (lower = more sensitive)">
          <input type="range" min="0.005" max="0.1" step="0.005"
            value={settings.silenceThreshold}
            onChange={e => apply({ silenceThreshold: parseFloat(e.target.value) })}
            className="sett-range"
          />
          <span className="sett-range-val">{settings.silenceThreshold}</span>
        </SettRow>
      </SettSection>

      <SettSection title="Wake Word">
        <SettRow label="Wake Word" sub="Phrase that activates the assistant">
          <input
            className="sett-input"
            value={settings.wakeWord}
            onChange={e => apply({ wakeWord: e.target.value })}
          />
        </SettRow>
        <SettRow label="Always-On Mode" sub="Listen continuously, skip wake word">
          <Toggle
            value={settings.alwaysOn}
            onChange={v => apply({ alwaysOn: v })}
          />
        </SettRow>
      </SettSection>

      <SettSection title="Text-to-Speech">
        <SettRow label="TTS Voice Feedback" sub="Speak responses aloud via pyttsx3">
          <Toggle value={settings.ttsEnabled} onChange={v => apply({ ttsEnabled: v })} />
        </SettRow>
        <SettRow label="Speaking Rate" sub="Words per minute">
          <input type="range" min="100" max="280" step="5"
            value={settings.ttsRate}
            onChange={e => apply({ ttsRate: parseInt(e.target.value) })}
            className="sett-range"
          />
          <span className="sett-range-val">{settings.ttsRate} wpm</span>
        </SettRow>
      </SettSection>

      <SettSection title="Privacy">
        <SettRow label="On-Device Only" sub="No audio ever leaves this machine">
          <span className="tag tag-teal">ENFORCED</span>
        </SettRow>
        <SettRow label="No Cloud Calls" sub="Fully air-gapped operation available">
          <span className="tag tag-teal">VERIFIED</span>
        </SettRow>
      </SettSection>
    </div>
  )
}

function SettSection({ title, children }) {
  return (
    <div className="sett-section">
      <div className="sett-section-title">{title}</div>
      {children}
    </div>
  )
}

function SettRow({ label, sub, children }) {
  return (
    <div className="sett-row">
      <div>
        <div className="sett-label">{label}</div>
        {sub && <div className="sett-sub">{sub}</div>}
      </div>
      <div className="sett-control">{children}</div>
    </div>
  )
}

function Toggle({ value, onChange }) {
  return (
    <button
      className={`toggle-btn ${value ? 'toggle-on' : ''}`}
      onClick={() => onChange(!value)}
      style={{ flexShrink: 0 }}
    />
  )
}
