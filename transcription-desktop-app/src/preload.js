const { contextBridge, ipcRenderer } = require('electron');

// Exposer API sécurisée au renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // ─── Authentification ───────────────────────────────────────────────────────
  authenticateGoogle: () => ipcRenderer.invoke('authenticate-google'),
  checkAuth: () => ipcRenderer.invoke('check-auth'),

  // ─── Traitement vidéo (Upload tab) ─────────────────────────────────────────
  processVideo: (videoPath) => ipcRenderer.invoke('process-video', videoPath),

  // ─── Watch Folder ───────────────────────────────────────────────────────────
  selectWatchFolder: () => ipcRenderer.invoke('select-watch-folder'),
  startWatching: (folderPath) => ipcRenderer.invoke('start-watching', folderPath),
  stopWatching: () => ipcRenderer.invoke('stop-watching'),
  getWatchedFolder: () => ipcRenderer.invoke('get-watched-folder'),

  // ─── Automation ─────────────────────────────────────────────────────────────
  startAutomation: () => ipcRenderer.invoke('start-automation'),
  stopAutomation: () => ipcRenderer.invoke('stop-automation'),
  getAutomationStatus: () => ipcRenderer.invoke('get-automation-status'),
  runTranscriptionNow: () => ipcRenderer.invoke('run-transcription-now'),
  runHighlightsNow: () => ipcRenderer.invoke('run-highlights-now'),

  // ─── Settings ───────────────────────────────────────────────────────────────
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  getSettings: () => ipcRenderer.invoke('get-settings'),
  testR2Connection: (config) => ipcRenderer.invoke('test-r2-connection', config),
  testRunpodConnection: (config) => ipcRenderer.invoke('test-runpod-connection', config),

  // ─── Listeners (Upload) ─────────────────────────────────────────────────────
  onExtractionProgress: (callback) => {
    ipcRenderer.on('extraction-progress', (event, data) => callback(data));
  },
  onUploadProgress: (callback) => {
    ipcRenderer.on('upload-progress', (event, data) => callback(data));
  },
  onStatusUpdate: (callback) => {
    ipcRenderer.on('status-update', (event, data) => callback(data));
  },

  // ─── Listeners (Watch Folder) ────────────────────────────────────────────────
  onWatchFolderNewFile: (callback) => {
    ipcRenderer.on('watch-folder-new-file', (event, data) => callback(data));
  },
  onWatchFolderProgress: (callback) => {
    ipcRenderer.on('watch-folder-progress', (event, data) => callback(data));
  },
  onWatchFolderSuccess: (callback) => {
    ipcRenderer.on('watch-folder-success', (event, data) => callback(data));
  },
  onWatchFolderError: (callback) => {
    ipcRenderer.on('watch-folder-error', (event, data) => callback(data));
  },
  onWatchFolderAutoStarted: (callback) => {
    ipcRenderer.on('watch-folder-auto-started', (event, data) => callback(data));
  },

  // ─── Listeners (Automation) ──────────────────────────────────────────────────
  onAutomationStatus: (callback) => {
    ipcRenderer.on('automation-status', (event, data) => callback(data));
  },
  onAutomationUpdate: (callback) => {
    ipcRenderer.on('automation-update', (event, data) => callback(data));
  },
  onLogLine: (callback) => {
    ipcRenderer.on('log-line', (event, data) => callback(data));
  }
});
