/**
 * src/stores/voxelStore.js — Global state (Zustand)
 */

import { create } from 'zustand'

const MAX_LOG_ENTRIES = 200

export const useVoxelStore = create((set, get) => ({
  // Connection
  connected: false,
  setConnected: (v) => set({ connected: v }),

  // Voice state: 'idle' | 'listening' | 'processing' | 'speaking' | 'disconnected'
  status: 'idle',
  setStatus: (status) => set({ status }),

  // Transcription + AI response
  transcript: '',
  setTranscript: (transcript) => set({ transcript }),
  response: 'Say "Hey Voxel" to start...',
  setResponse: (response) => set({ response }),

  // Waveform amplitude
  waveformRms: 0,
  setWaveformRms: (rms) => set({ waveformRms: rms }),

  // Stats
  commandCount: 0,
  incrementCommandCount: () => set((s) => ({ commandCount: s.commandCount + 1 })),
  sessionStart: Date.now(),

  // Activity log
  logs: [],
  addLogEntry: (entry) =>
    set((s) => ({
      logs: [entry, ...s.logs].slice(0, MAX_LOG_ENTRIES),
    })),
  clearLogs: () => set({ logs: [] }),

  // Settings (synced to backend via WebSocket)
  settings: {
    whisperModel: 'base.en',
    wakeWord: 'hey voxel',
    ttsEnabled: true,
    ttsRate: 175,
    alwaysOn: false,
    silenceThreshold: 0.02,
    silenceDuration: 1.2,
  },
  updateSettings: (patch) =>
    set((s) => ({ settings: { ...s.settings, ...patch } })),

  // Active nav tab
  activeTab: 'voice',
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
