/**
 * src/hooks/useVoxelSocket.js
 *
 * Maintains a persistent WebSocket connection to the Python backend
 * (ws://localhost:8765). The backend pushes JSON events; the frontend
 * can also send JSON commands.
 *
 * Message protocol:
 *   Backend → Frontend:
 *     { type: "transcript",  text: "open chrome" }
 *     { type: "response",    text: "Opening Chrome now." }
 *     { type: "status",      state: "listening" | "idle" | "processing" }
 *     { type: "command",     name: "open_app", args: {...}, success: true }
 *     { type: "log",         level: "info"|"warn"|"error", message: "..." }
 *     { type: "waveform",    rms: 0.12 }
 *
 *   Frontend → Backend:
 *     { action: "activate" }        — trigger one listen cycle
 *     { action: "stop" }            — stop current listen
 *     { action: "settings", data }  — push new settings
 */

import { useEffect, useRef, useCallback } from 'react'
import { useVoxelStore } from '@/stores/voxelStore'

const WS_URL = 'ws://localhost:8765'
const RECONNECT_DELAY = 2000

export function useVoxelSocket() {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const {
    setConnected,
    setStatus,
    setTranscript,
    setResponse,
    addLogEntry,
    setWaveformRms,
    incrementCommandCount,
  } = useVoxelStore()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      addLogEntry({ level: 'info', message: 'Connected to VOXEL backend.', ts: Date.now() })
    }

    ws.onclose = () => {
      setConnected(false)
      setStatus('disconnected')
      addLogEntry({ level: 'warn', message: 'Backend disconnected. Retrying...', ts: Date.now() })
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = (err) => {
      addLogEntry({ level: 'error', message: `WebSocket error: ${err.message || 'unknown'}`, ts: Date.now() })
    }

    ws.onmessage = (event) => {
      let msg
      try { msg = JSON.parse(event.data) } catch { return }

      switch (msg.type) {
        case 'transcript':
          setTranscript(msg.text)
          setStatus('processing')
          break
        case 'response':
          setResponse(msg.text)
          setStatus('idle')
          break
        case 'status':
          setStatus(msg.state)
          break
        case 'command':
          incrementCommandCount()
          addLogEntry({
            level: msg.success ? 'info' : 'error',
            message: msg.success
              ? `Executed: ${msg.name}`
              : `Failed: ${msg.name} — ${msg.error}`,
            command: msg.name,
            ts: Date.now(),
          })
          break
        case 'log':
          addLogEntry({ level: msg.level, message: msg.message, ts: Date.now() })
          break
        case 'waveform':
          setWaveformRms(msg.rms)
          break
        default:
          break
      }
    }
  }, [setConnected, setStatus, setTranscript, setResponse, addLogEntry, setWaveformRms, incrementCommandCount])

  const send = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  const activate = useCallback(() => send({ action: 'activate' }), [send])
  const stop = useCallback(() => send({ action: 'stop' }), [send])
  const pushSettings = useCallback((data) => send({ action: 'settings', data }), [send])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { activate, stop, pushSettings }
}
