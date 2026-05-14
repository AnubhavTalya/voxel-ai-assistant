/**
 * src/components/Sidebar.jsx
 */

import { useVoxelStore } from '@/stores/voxelStore'
import './Sidebar.css'

const NAV = [
  { id: 'voice',    icon: '◉', label: 'Voice',    group: 'CORE' },
  { id: 'commands', icon: '⚡', label: 'Commands', group: 'CORE', badge: '24' },
  { id: 'flows',    icon: '↻', label: 'Flows',    group: 'AUTOMATION' },
  { id: 'log',      icon: '≡', label: 'Activity', group: 'AUTOMATION' },
  { id: 'settings', icon: '⚙', label: 'Settings', group: 'SYSTEM' },
]

export default function Sidebar() {
  const activeTab   = useVoxelStore((s) => s.activeTab)
  const setActiveTab = useVoxelStore((s) => s.setActiveTab)
  const settings    = useVoxelStore((s) => s.settings)
  const cmdCount    = useVoxelStore((s) => s.commandCount)
  const sessionStart = useVoxelStore((s) => s.sessionStart)

  const uptime = Math.floor((Date.now() - sessionStart) / 1000)
  const uptimeStr = uptime < 60
    ? `${uptime}s`
    : `${Math.floor(uptime / 60)}m ${uptime % 60}s`

  const groups = [...new Set(NAV.map(n => n.group))]

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {groups.map(group => (
          <div key={group} className="nav-group">
            <div className="nav-group-label">{group}</div>
            {NAV.filter(n => n.group === group).map(item => (
              <button
                key={item.id}
                className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => setActiveTab(item.id)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-row">
          <span className="footer-key">MODEL</span>
          <span className="footer-val">{settings.whisperModel}</span>
        </div>
        <div className="footer-row">
          <span className="footer-key">UPTIME</span>
          <span className="footer-val accent">{uptimeStr}</span>
        </div>
        <div className="footer-row">
          <span className="footer-key">EXECUTED</span>
          <span className="footer-val">{cmdCount} cmds</span>
        </div>
        <div className="footer-row">
          <span className="footer-key">PRIVACY</span>
          <span className="footer-val" style={{ color: 'var(--accent)' }}>ON-DEVICE</span>
        </div>
      </div>
    </aside>
  )
}
