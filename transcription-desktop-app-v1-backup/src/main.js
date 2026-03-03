const { app, BrowserWindow, ipcMain, shell, dialog, Tray, Menu } = require('electron');
const path = require('path');
const { google } = require('googleapis');
const Store = require('electron-store');
const fs = require('fs');
const ffmpeg = require('fluent-ffmpeg');
const chokidar = require('chokidar');
const AutoLaunch = require('auto-launch');

// Store pour sauvegarder les credentials Google
const store = new Store();

// Auto-launch au démarrage
const autoLauncher = new AutoLaunch({
  name: 'TranscriptionApp',
  path: app.getPath('exe')
});

// Tray icon
let tray = null;

// Configuration OAuth Google Drive
// IMPORTANT: drive (et non drive.file) pour accéder aux Shared Drives
const SCOPES = ['https://www.googleapis.com/auth/drive'];
const CLIENT_ID = '';
const CLIENT_SECRET = '';
const REDIRECT_URI = 'http://localhost:3000/oauth2callback';

// ID du dossier source_files dans Google Drive
const SOURCE_FILES_FOLDER_ID = '1A29pkQvrBodU_HxNS8deYt6T27AlmbSe';

let mainWindow;
let oauth2Client;
let folderWatcher = null;
let watchedFolder = null;
let processingFiles = new Set(); // Éviter de traiter 2 fois le même fichier

function createTray() {
  // Créer icône tray
  const iconPath = path.join(__dirname, '../build/tray-icon.png');

  // Utiliser icône par défaut Electron si pas d'icône custom
  try {
    if (fs.existsSync(iconPath)) {
      tray = new Tray(iconPath);
    } else {
      // Pas d'icône, créer un tray sans icône (fonctionne sur certaines plateformes)
      tray = new Tray(app.getAppPath());
    }
  } catch (error) {
    // Fallback: pas de tray si erreur
    return;
  }

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Ouvrir',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
        } else {
          createWindow();
        }
      }
    },
    {
      label: 'Watch Folder',
      type: 'checkbox',
      checked: !!folderWatcher,
      click: () => {
        // Toggle watch folder (géré par l'UI)
        if (mainWindow) mainWindow.show();
      }
    },
    { type: 'separator' },
    {
      label: 'Quitter',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('Transcription App');
  tray.setContextMenu(contextMenu);

  // Double-clic pour ouvrir la fenêtre
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
    } else {
      createWindow();
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'Transcription App',
    resizable: false
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Minimiser dans le tray au lieu de fermer
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

// Initialisation OAuth2
function initOAuth() {
  oauth2Client = new google.auth.OAuth2(
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI
  );

  // Vérifier si on a déjà des credentials sauvegardés
  const tokens = store.get('google_tokens');
  if (tokens) {
    oauth2Client.setCredentials(tokens);
    return true;
  }
  return false;
}

// Authentification Google
ipcMain.handle('authenticate-google', async () => {
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
  });

  // Ouvrir le navigateur pour auth
  await shell.openExternal(authUrl);

  // Créer serveur temporaire pour recevoir le callback
  const http = require('http');
  return new Promise((resolve) => {
    const server = http.createServer(async (req, res) => {
      if (req.url.startsWith('/oauth2callback')) {
        const url = new URL(req.url, 'http://localhost:3000');
        const code = url.searchParams.get('code');

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end('<h1>Authentification réussie! Vous pouvez fermer cette fenêtre.</h1>');

        server.close();

        // Échanger le code contre des tokens
        const { tokens } = await oauth2Client.getToken(code);
        oauth2Client.setCredentials(tokens);
        store.set('google_tokens', tokens);

        resolve({ success: true });
      }
    });

    server.listen(3000);
  });
});

// Vérifier si authentifié
ipcMain.handle('check-auth', async () => {
  return initOAuth();
});

// Helper: Extraction audio avec FFmpeg
async function extractAudio(videoPath) {
  const audioPath = path.join(
    path.dirname(videoPath),
    path.basename(videoPath, path.extname(videoPath)) + '.wav'
  );

  return new Promise((resolve, reject) => {
    // Vérifier que le fichier vidéo existe
    if (!fs.existsSync(videoPath)) {
      reject(new Error(`Fichier vidéo introuvable: ${videoPath}`));
      return;
    }

    ffmpeg(videoPath)
      .noVideo()
      .audioCodec('pcm_s16le')
      .audioFrequency(16000)
      .audioChannels(1)
      .on('start', (commandLine) => {
        // FFmpeg démarre - envoyer notification
        if (mainWindow) {
          mainWindow.webContents.send('watch-folder-progress', {
            fileName: path.basename(videoPath),
            stage: 'extraction',
            message: `Extraction audio - FFmpeg démarré`
          });
        }
      })
      .on('progress', (progress) => {
        if (mainWindow) {
          const percent = progress.percent || 0;
          mainWindow.webContents.send('watch-folder-progress', {
            fileName: path.basename(videoPath),
            stage: 'extraction',
            message: `Extraction audio - ${Math.round(percent)}%`
          });
          // Aussi envoyer extraction-progress pour compatibilité
          mainWindow.webContents.send('extraction-progress', {
            percent: percent
          });
        }
      })
      .on('end', () => {
        resolve(audioPath);
      })
      .on('error', (err) => {
        reject(new Error(`FFmpeg error: ${err.message}`));
      })
      .save(audioPath);
  });
}

// Helper: Vérifier si un fichier existe déjà sur Drive
async function fileExistsOnDrive(fileName, folderId) {
  const drive = google.drive({ version: 'v3', auth: oauth2Client });

  try {
    const res = await drive.files.list({
      q: `name='${fileName}' and '${folderId}' in parents and trashed=false`,
      fields: 'files(id, name)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true
    });

    return res.data.files && res.data.files.length > 0;
  } catch (error) {
    console.error('Check file exists error:', error);
    return false;
  }
}

// Helper: Upload vers Google Drive
async function uploadToDrive(filePath, fileName, folderId, watchFileName = null, stage = null) {
  const drive = google.drive({ version: 'v3', auth: oauth2Client });

  const fileSize = fs.statSync(filePath).size;
  const fileStream = fs.createReadStream(filePath);

  try {
    const res = await drive.files.create({
      requestBody: {
        name: fileName,
        parents: folderId ? [folderId] : undefined
      },
      media: {
        body: fileStream
      },
      supportsAllDrives: true  // Support pour Shared Drives
    }, {
      onUploadProgress: (evt) => {
        const progress = (evt.bytesRead / fileSize) * 100;
        if (mainWindow) {
          // Envoyer upload-progress (pour upload manuel)
          mainWindow.webContents.send('upload-progress', {
            percent: progress,
            fileName: fileName
          });

          // Envoyer watch-folder-progress avec pourcentage (pour watch folder)
          if (watchFileName && stage) {
            const stageLabel = stage === 'upload-audio' ? 'Upload audio' : 'Upload vidéo';
            mainWindow.webContents.send('watch-folder-progress', {
              fileName: watchFileName,
              stage: stage,
              message: `${stageLabel} - ${Math.round(progress)}%`
            });
          }
        }
      }
    });

    return {
      success: true,
      fileId: res.data.id,
      fileName: res.data.name
    };
  } catch (error) {
    console.error('Upload error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Watch Folder Functions
function startWatchingFolder(folderPath) {
  // Arrêter le watcher existant
  if (folderWatcher) {
    folderWatcher.close();
  }

  watchedFolder = folderPath;
  store.set('watched_folder', folderPath);

  // Extensions vidéo supportées
  const videoExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v'];

  folderWatcher = chokidar.watch(folderPath, {
    ignored: /(^|[\/\\])\../, // Ignorer fichiers cachés
    persistent: true,
    ignoreInitial: true, // IMPORTANT: Ignorer fichiers existants, ne traiter que les nouveaux
    awaitWriteFinish: {
      stabilityThreshold: 2000,
      pollInterval: 100
    }
  });

  folderWatcher.on('add', async (filePath) => {
    const ext = path.extname(filePath).toLowerCase();

    // Vérifier si c'est une vidéo et pas déjà en cours de traitement
    if (videoExtensions.includes(ext) && !processingFiles.has(filePath)) {
      processingFiles.add(filePath);

      // Notifier l'UI
      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-new-file', {
          fileName: path.basename(filePath),
          filePath: filePath
        });
      }

      // ATTENDRE que le fichier soit complètement copié (surtout pour gros fichiers)
      await new Promise(resolve => setTimeout(resolve, 3000));

      try {
        // Debug: Notifier début traitement
        if (mainWindow) {
          mainWindow.webContents.send('watch-folder-progress', {
            fileName: path.basename(filePath),
            stage: 'starting',
            message: 'Démarrage traitement...'
          });
        }

        // Traiter la vidéo automatiquement
        const result = await processVideoAuto(filePath);

        if (result.success) {
          if (mainWindow) {
            mainWindow.webContents.send('watch-folder-success', {
              fileName: path.basename(filePath),
              video: result.video,
              audio: result.audio
            });
          }
        } else {
          // ERREUR DÉTAILLÉE dans l'UI
          if (mainWindow) {
            mainWindow.webContents.send('watch-folder-error', {
              fileName: path.basename(filePath),
              error: result.error || 'Erreur inconnue'
            });
          }
        }
      } catch (error) {
        // ERREUR EXCEPTION dans l'UI
        if (mainWindow) {
          mainWindow.webContents.send('watch-folder-error', {
            fileName: path.basename(filePath),
            error: `Exception: ${error.message}\nStack: ${error.stack}`
          });
        }
      } finally {
        processingFiles.delete(filePath);
      }
    }
  });

  folderWatcher.on('error', (error) => {
    console.error('Watch error:', error);
  });

  return true;
}

function stopWatchingFolder() {
  if (folderWatcher) {
    folderWatcher.close();
    folderWatcher = null;
  }
  watchedFolder = null;
  store.delete('watched_folder');
  return true;
}

// Version automatique du traitement (pour watch folder)
async function processVideoAuto(videoPath) {
  const fileName = path.basename(videoPath);

  try {
    // Vérifier que le fichier existe
    if (!fs.existsSync(videoPath)) {
      return {
        success: false,
        error: `Fichier introuvable: ${fileName}`
      };
    }

    // Vérifier OAuth
    if (!oauth2Client.credentials || !oauth2Client.credentials.access_token) {
      return {
        success: false,
        error: 'Non authentifié - Veuillez vous connecter avec Google'
      };
    }

    // Préparer les noms de fichiers
    const videoFileName = path.basename(videoPath);
    const audioFileName = path.basename(videoPath, path.extname(videoPath)) + '.wav';

    // Vérifier si les fichiers existent déjà sur Drive
    const audioExists = await fileExistsOnDrive(audioFileName, SOURCE_FILES_FOLDER_ID);
    const videoExists = await fileExistsOnDrive(videoFileName, SOURCE_FILES_FOLDER_ID);

    if (audioExists && videoExists) {
      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-progress', {
          fileName: fileName,
          stage: 'skipped',
          message: 'Fichiers déjà uploadés - Skip'
        });
      }
      return {
        success: true,
        skipped: true,
        message: 'Fichiers déjà présents sur Drive'
      };
    }

    let audioResult = null;
    let audioPath = null;

    // Étape 1: Extraction et upload audio (si pas déjà sur Drive)
    if (!audioExists) {
      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-progress', {
          fileName: fileName,
          stage: 'extraction',
          message: 'Extraction audio...'
        });
      }

      audioPath = await extractAudio(videoPath);

      if (!fs.existsSync(audioPath)) {
        return {
          success: false,
          error: `Extraction audio échouée - Fichier audio non créé`
        };
      }

      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-progress', {
          fileName: fileName,
          stage: 'upload-audio',
          message: 'Upload audio...'
        });
      }

      audioResult = await uploadToDrive(
        audioPath,
        audioFileName,
        SOURCE_FILES_FOLDER_ID,
        fileName,
        'upload-audio'
      );

      if (!audioResult.success) {
        try { fs.unlinkSync(audioPath); } catch (e) {}
        return {
          success: false,
          error: `Échec upload audio: ${audioResult.error}`
        };
      }
    } else {
      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-progress', {
          fileName: fileName,
          stage: 'skipped-audio',
          message: 'Audio déjà uploadé - Skip'
        });
      }
    }

    let videoResult = null;

    if (!videoExists) {
      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-progress', {
          fileName: fileName,
          stage: 'upload-video',
          message: 'Upload vidéo...'
        });
      }

      videoResult = await uploadToDrive(
        videoPath,
        videoFileName,
        SOURCE_FILES_FOLDER_ID,
        fileName,
        'upload-video'
      );

      if (!videoResult.success) {
        if (audioPath) {
          try { fs.unlinkSync(audioPath); } catch (e) {}
        }
        return {
          success: false,
          error: `Échec upload vidéo: ${videoResult.error}`
        };
      }
    } else {
      if (mainWindow) {
        mainWindow.webContents.send('watch-folder-progress', {
          fileName: fileName,
          stage: 'skipped-video',
          message: 'Vidéo déjà uploadée - Skip'
        });
      }
    }

    if (audioPath) {
      try { fs.unlinkSync(audioPath); } catch (e) {}
    }

    return {
      success: true,
      video: videoResult,
      audio: audioResult
    };
  } catch (error) {
    return {
      success: false,
      error: `Exception: ${error.message}`
    };
  }
}

// IPC Handlers
ipcMain.handle('extract-audio', async (event, videoPath) => {
  return extractAudio(videoPath);
});

ipcMain.handle('upload-to-drive', async (event, filePath, fileName, folderId) => {
  return uploadToDrive(filePath, fileName, folderId);
});

// Traitement complet d'un fichier
ipcMain.handle('process-video', async (event, videoPath) => {
  try {
    mainWindow.webContents.send('status-update', {
      stage: 'extraction',
      message: 'Extraction de l\'audio...'
    });

    const audioPath = await extractAudio(videoPath);

    mainWindow.webContents.send('status-update', {
      stage: 'upload-audio',
      message: 'Upload de l\'audio...'
    });

    const audioFileName = path.basename(audioPath);
    const audioResult = await uploadToDrive(
      audioPath,
      audioFileName,
      SOURCE_FILES_FOLDER_ID
    );

    if (!audioResult.success) {
      fs.unlinkSync(audioPath);
      return {
        success: false,
        error: `Échec upload audio: ${audioResult.error}`
      };
    }

    mainWindow.webContents.send('status-update', {
      stage: 'upload-video',
      message: 'Upload de la vidéo...'
    });

    const videoFileName = path.basename(videoPath);
    const videoResult = await uploadToDrive(
      videoPath,
      videoFileName,
      SOURCE_FILES_FOLDER_ID
    );

    if (!videoResult.success) {
      fs.unlinkSync(audioPath);
      return {
        success: false,
        error: `Échec upload vidéo: ${videoResult.error}`
      };
    }

    fs.unlinkSync(audioPath);

    return {
      success: true,
      video: videoResult,
      audio: audioResult
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
});

// Watch Folder Handlers
ipcMain.handle('select-watch-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Sélectionner un dossier à surveiller'
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return {
      success: true,
      folderPath: result.filePaths[0]
    };
  }

  return {
    success: false
  };
});

ipcMain.handle('start-watching', async (event, folderPath) => {
  try {
    startWatchingFolder(folderPath);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('stop-watching', async () => {
  try {
    stopWatchingFolder();
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-watched-folder', async () => {
  const folder = store.get('watched_folder');
  return {
    isWatching: !!folderWatcher,
    folderPath: folder || watchedFolder
  };
});

app.whenReady().then(async () => {
  // Activer auto-launch au démarrage
  try {
    const isEnabled = await autoLauncher.isEnabled();
    if (!isEnabled) {
      await autoLauncher.enable();
    }
  } catch (error) {
    // Erreur silencieuse si auto-launch ne fonctionne pas
  }

  // Créer tray icon
  createTray();

  initOAuth();
  createWindow();

  // Auto-restart watch folder si configuré
  const savedFolder = store.get('watched_folder');
  if (savedFolder && fs.existsSync(savedFolder)) {
    // Attendre que l'OAuth soit initialisé et que la fenêtre soit prête
    setTimeout(() => {
      try {
        // Vérifier que l'OAuth est bien configuré avant de démarrer
        const isAuth = initOAuth();
        if (isAuth && oauth2Client.credentials && oauth2Client.credentials.access_token) {
          startWatchingFolder(savedFolder);
          watchedFolder = savedFolder;

          // Notifier le renderer que le watch folder a démarré
          if (mainWindow && mainWindow.webContents) {
            mainWindow.webContents.send('watch-folder-auto-started', {
              folderPath: savedFolder
            });
          }
        }
      } catch (error) {
        // Erreur silencieuse
      }
    }, 3000);
  }
});

app.on('window-all-closed', () => {
  // Ne pas quitter l'app, rester en arrière-plan dans le tray
  // L'utilisateur doit quitter via le menu tray
  if (process.platform !== 'darwin' && !app.isQuitting) {
    // Ne rien faire, l'app reste dans le tray
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
