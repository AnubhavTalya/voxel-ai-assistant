/**
 * electron/preload.js — Secure context bridge between renderer and main process.
 * Only explicitly whitelisted APIs are exposed to the renderer (React app).
 */

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('voxel', {
  // Window controls
  minimize: () => ipcRenderer.invoke('window:minimize'),
  maximize: () => ipcRenderer.invoke('window:maximize'),
  close:    () => ipcRenderer.invoke('window:close'),
  hide:     () => ipcRenderer.invoke('window:hide'),

  // Python backend control
  restartBackend: () => ipcRenderer.invoke('python:restart'),
  stopBackend:    () => ipcRenderer.invoke('python:stop'),

  // Listen for backend events pushed from main process
  onPythonLog:    (cb) => ipcRenderer.on('python:log',    (_, d) => cb(d)),
  onPythonStatus: (cb) => ipcRenderer.on('python:status', (_, d) => cb(d)),
  removePythonListeners: () => {
    ipcRenderer.removeAllListeners('python:log')
    ipcRenderer.removeAllListeners('python:status')
  },

  // Shell
  openExternal: (url) => ipcRenderer.invoke('open:external', url),
})
