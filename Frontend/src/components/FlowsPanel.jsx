/**
 * src/components/FlowsPanel.jsx
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import './FlowsPanel.css'

const FLOWS = [
  { id:'morning',  icon:'◑', name:'Morning Briefing',     desc:'Screenshot + weather + calendar on wake-up', color:'teal', on:true },
  { id:'backup',   icon:'⏺', name:'Auto-Backup on Command',desc:'Say "backup now" → zip + move to folder',    color:'violet', on:true },
  { id:'focus',    icon:'◎', name:'Focus Mode',            desc:'Block distracting apps + mute notifications', color:'teal', on:false },
  { id:'night',    icon:'◐', name:'Night Wind-Down',       desc:'Dims screen + closes browser + locks machine', color:'red', on:false },
  { id:'clipboard',icon:'⊞', name:'Clipboard Logger',      desc:'Saves clipboard history to encrypted file',   color:'violet', on:true },
  { id:'meeting',  icon:'◈', name:'Meeting Prep',          desc:'Opens calendar + mutes Slack + DND on',        color:'teal', on:false },
]

export function FlowsPanel() {
  const [flows, setFlows] = useState(FLOWS)

  const toggle = (id) =>
    setFlows(f => f.map(fl => fl.id === id ? { ...fl, on: !fl.on } : fl))

  return (
    <div className="panel">
      <h2 className="panel-title">Automation Flows</h2>
      <div className="flows-list">
        {flows.map((fl, i) => (
          <motion.div
            key={fl.id}
            className="flow-row"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <div className={`flow-icon-box fi-${fl.color}`}>{fl.icon}</div>
            <div className="flow-info">
              <div className="flow-name">{fl.name}</div>
              <div className="flow-desc">{fl.desc}</div>
            </div>
            <button
              className={`toggle-btn ${fl.on ? 'toggle-on' : ''}`}
              onClick={() => toggle(fl.id)}
              aria-label={fl.on ? 'Disable' : 'Enable'}
            />
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export default FlowsPanel
