/**
 * src/App.jsx — Root layout: titlebar + sidebar + main panel
 */

import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useVoxelStore } from '@/stores/voxelStore'
import { useVoxelSocket } from '@/hooks/useVoxelSocket'
import TitleBar from '@/components/TitleBar'
import Sidebar from '@/components/Sidebar'
import VoicePanel from '@/components/VoicePanel'
import CommandsPanel from '@/components/CommandsPanel'
import FlowsPanel from '@/components/FlowsPanel'
import LogPanel from '@/components/LogPanel'
import SettingsPanel from '@/components/SettingsPanel'
import './styles/global.css'

const PANELS = {
  voice:    VoicePanel,
  commands: CommandsPanel,
  flows:    FlowsPanel,
  log:      LogPanel,
  settings: SettingsPanel,
}

export default function App() {
  const activeTab = useVoxelStore((s) => s.activeTab)
  const { activate, stop, pushSettings } = useVoxelSocket()

  // Listen for Python log events pushed from Electron main process
  useEffect(() => {
    if (typeof window.voxel === 'undefined') return
    const addLog = useVoxelStore.getState().addLogEntry
    window.voxel.onPythonLog((d) =>
      addLog({ level: d.level, message: d.text.trim(), ts: Date.now() })
    )
    return () => window.voxel.removePythonListeners?.()
  }, [])

  const ActivePanel = PANELS[activeTab] || VoicePanel

  return (
    <div className="app-shell">
      <TitleBar />
      <div className="app-body">
        <Sidebar />
        <main className="app-main">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              className="panel-wrapper"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              <ActivePanel activate={activate} stop={stop} pushSettings={pushSettings} />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
