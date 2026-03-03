const { contextBridge, ipcRenderer } = require('electron');

// Exposer API sécurisée au renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Authentification
  authenticateGoogle: () => ipcRenderer.invoke('authenticate-google'),
  checkAuth: () => ipcRenderer.invoke('check-auth'),

  // Traitement vidéo
  processVideo: (videoPath) => ipcRenderer.invoke('process-video', videoPath),

  // Watch Folder
  selectWatchFolder: () => ipcRenderer.invoke('select-watch-folder'),
  startWatching: (folderPath) => ipcRenderer.invoke('start-watching', folderPath),
  stopWatching: () => ipcRenderer.invoke('stop-watching'),
  getWatchedFolder: () => ipcRenderer.invoke('get-watched-folder'),

  // Listeners pour les progrès
  onExtractionProgress: (callback) => {
    ipcRenderer.on('extraction-progress', (event, data) => callback(data));
  },
  onUploadProgress: (callback) => {
    ipcRenderer.on('upload-progress', (event, data) => callback(data));
  },
  onStatusUpdate: (callback) => {
    ipcRenderer.on('status-update', (event, data) => callback(data));
  },

  // Listeners pour watch folder
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
  }
});
