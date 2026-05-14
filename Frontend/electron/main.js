/**
 * electron/main.js — Electron main process
 *
 * Responsibilities:
 *   1. Create the BrowserWindow (frameless, draggable)
 *   2. Spawn the Python VOXEL backend as a child process
 *   3. Forward backend stdout/stderr to renderer via IPC
 *   4. Handle graceful shutdown of both processes
 */

const { app, BrowserWindow, ipcMain, shell, Tray, Menu, nativeImage } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const VITE_DEV_URL = 'http://localhost:5173'

let win = null
let tray = null
let pythonProcess = null

// ── Window ───────────────────────────────────────────────────────────────────

function createWindow() {
  win = new BrowserWindow({
    width: 1080,
    height: 680,
    minWidth: 820,
    minHeight: 540,
    frame: false,           // custom titlebar
    transparent: false,
    backgroundColor: '#0a0c0f',
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '../public/icon.png'),
  })

  if (isDev) {
    win.loadURL(VITE_DEV_URL)
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  win.on('closed', () => { win = null })
}

// ── System Tray ──────────────────────────────────────────────────────────────

function createTray() {
  const iconPath = path.join(__dirname, '../public/tray-icon.png')
  tray = new Tray(nativeImage.createFromPath(iconPath).resize({ width: 16 }))
  const menu = Menu.buildFromTemplate([
    { label: 'Show VOXEL', click: () => win?.show() },
    { label: 'Hide', click: () => win?.hide() },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ])
  tray.setToolTip('VOXEL — Voice Assistant')
  tray.setContextMenu(menu)
  tray.on('double-click', () => win?.show())
}

// ── Python Backend ───────────────────────────────────────────────────────────

function spawnPython() {
  const pythonExe = process.platform === 'win32' ? 'python' : 'python3'
  const backendPath = isDev
    ? path.join(__dirname, '../../Backend/main.py')
    : path.join(process.resourcesPath, 'Backend/main.py')

  console.log(`[electron] Spawning Python backend: ${pythonExe} ${backendPath}`)

  pythonProcess = spawn(pythonExe, [backendPath], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env },
  })

  pythonProcess.stdout.on('data', (data) => {
    const text = data.toString()
    console.log('[python]', text.trim())
    win?.webContents.send('python:log', { level: 'info', text })
  })

  pythonProcess.stderr.on('data', (data) => {
    const text = data.toString()
    console.error('[python:err]', text.trim())
    win?.webContents.send('python:log', { level: 'error', text })
  })

  pythonProcess.on('close', (code) => {
    console.log(`[electron] Python process exited with code ${code}`)
    win?.webContents.send('python:status', { status: 'stopped', code })
  })

  pythonProcess.on('error', (err) => {
    console.error('[electron] Failed to start Python:', err)
    win?.webContents.send('python:status', { status: 'error', message: err.message })
  })
}

// ── IPC Handlers ─────────────────────────────────────────────────────────────

ipcMain.handle('window:minimize', () => win?.minimize())
ipcMain.handle('window:maximize', () => {
  if (win?.isMaximized()) win.restore()
  else win?.maximize()
})
ipcMain.handle('window:close', () => win?.close())
ipcMain.handle('window:hide', () => win?.hide())

ipcMain.handle('python:restart', () => {
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
  setTimeout(spawnPython, 800)
})

ipcMain.handle('python:stop', () => {
  pythonProcess?.kill()
  pythonProcess = null
})

ipcMain.handle('open:external', (_, url) => shell.openExternal(url))

// ── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  createWindow()
  createTray()
  spawnPython()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('before-quit', () => {
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
})
