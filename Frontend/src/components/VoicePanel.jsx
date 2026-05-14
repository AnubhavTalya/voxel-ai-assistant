/**
 * src/components/VoicePanel.jsx
 * Central voice interaction screen — mic orb, waveform bars, transcript, AI response.
 */

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useVoxelStore } from '@/stores/voxelStore'
import './VoicePanel.css'

const BAR_COUNT = 28

export default function VoicePanel({ activate, stop }) {
  const status     = useVoxelStore((s) => s.status)
  const transcript = useVoxelStore((s) => s.transcript)
  const response   = useVoxelStore((s) => s.response)
  const waveRms    = useVoxelStore((s) => s.waveformRms)
  const connected  = useVoxelStore((s) => s.connected)

  const [bars, setBars] = useState(Array(BAR_COUNT).fill(4))
  const animRef = useRef(null)
  const isListening = status === 'listening'
  const isProcessing = status === 'processing'
  const isActive = isListening || isProcessing

  // Animate waveform bars
  useEffect(() => {
    if (isListening) {
      const tick = () => {
        setBars(prev => prev.map(() =>
          waveRms > 0.01
            ? 4 + Math.random() * waveRms * 200
            : 3 + Math.random() * 5
        ))
        animRef.current = requestAnimationFrame(tick)
      }
      animRef.current = requestAnimationFrame(tick)
    } else {
      cancelAnimationFrame(animRef.current)
      setBars(Array(BAR_COUNT).fill(4))
    }
    return () => cancelAnimationFrame(animRef.current)
  }, [isListening, waveRms])

  const handleMicClick = () => {
    if (!connected) return
    if (isListening) stop()
    else activate()
  }

  const statusText = {
    idle:         'Click to activate',
    listening:    'Listening...',
    processing:   'Processing...',
    speaking:     'Speaking...',
    disconnected: 'Backend offline',
  }[status] ?? 'Click to activate'

  return (
    <div className="voice-panel">
      {/* Ambient background rings */}
      <div className="voice-bg" aria-hidden>
        {[0, 1, 2, 3].map(i => (
          <div key={i} className={`ambient-ring ring-${i} ${isActive ? 'ring-active' : ''}`} />
        ))}
      </div>

      {/* Mic orb */}
      <div className="voice-core">
        <motion.button
          className={`mic-orb ${isListening ? 'orb-listening' : ''} ${isProcessing ? 'orb-processing' : ''} ${!connected ? 'orb-disabled' : ''}`}
          onClick={handleMicClick}
          whileHover={{ scale: connected ? 1.04 : 1 }}
          whileTap={{ scale: connected ? 0.96 : 1 }}
          aria-label={isListening ? 'Stop listening' : 'Activate voice'}
        >
          <div className="orb-inner">
            {isProcessing
              ? <div className="spin-ring" />
              : <span className="mic-glyph">{isListening ? '◉' : '◎'}</span>
            }
          </div>
        </motion.button>

        <div className={`voice-status-label ${isActive ? 'label-active' : ''}`}>
          {statusText}
        </div>

        {/* Waveform */}
        <div className="waveform" aria-hidden>
          {bars.map((h, i) => (
            <div
              key={i}
              className={`wbar ${isListening ? 'wbar-active' : ''}`}
              style={{ height: `${Math.max(3, Math.min(h, 40))}px` }}
            />
          ))}
        </div>
      </div>

      {/* Transcript + Response cards */}
      <div className="voice-cards">
        <AnimatePresence>
          {transcript && (
            <motion.div
              className="voice-card card-transcript"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              key={transcript}
            >
              <div className="card-label">YOU SAID</div>
              <div className="card-text">{transcript}</div>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          className="voice-card card-response"
          layout
        >
          <div className="card-label card-label-accent">AI RESPONSE</div>
          <AnimatePresence mode="wait">
            <motion.div
              className="card-text"
              key={response}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {response}
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Keyboard shortcut hint */}
      <div className="voice-hint">
        Press <kbd>Space</kbd> to activate · <kbd>Esc</kbd> to stop
      </div>
    </div>
  )
}
