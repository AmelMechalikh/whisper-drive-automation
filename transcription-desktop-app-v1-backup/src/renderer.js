// Éléments DOM
const authScreen = document.getElementById('auth-screen');
const mainScreen = document.getElementById('main-screen');
const authButton = document.getElementById('auth-button');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const progressContainer = document.getElementById('progress-container');
const statusText = document.getElementById('status-text');
const progressPercent = document.getElementById('progress-percent');
const progressFill = document.getElementById('progress-fill');
const details = document.getElementById('details');
const successMessage = document.getElementById('success-message');
const newUploadButton = document.getElementById('new-upload-button');

// Vérifier l'authentification au démarrage
window.electronAPI.checkAuth().then((isAuthenticated) => {
  if (isAuthenticated) {
    showMainScreen();
  } else {
    showAuthScreen();
  }
});

// Authentification Google
authButton.addEventListener('click', async () => {
  authButton.disabled = true;
  authButton.textContent = 'Connexion en cours...';

  try {
    const result = await window.electronAPI.authenticateGoogle();
    if (result.success) {
      showMainScreen();
    }
  } catch (error) {
    alert('Erreur d\'authentification: ' + error.message);
    authButton.disabled = false;
    authButton.innerHTML = '<img src="https://www.google.com/favicon.ico" class="google-icon"> Se connecter avec Google';
  }
});

function showAuthScreen() {
  authScreen.classList.remove('hidden');
  mainScreen.classList.add('hidden');
}

function showMainScreen() {
  authScreen.classList.add('hidden');
  mainScreen.classList.remove('hidden');
}

// Drag & Drop
dropZone.addEventListener('click', () => {
  fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');

  const files = e.dataTransfer.files;
  if (files.length > 0) {
    handleFile(files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFile(e.target.files[0]);
  }
});

// Traitement du fichier
async function handleFile(file) {
  // Vérifier que c'est une vidéo
  if (!file.type.startsWith('video/')) {
    alert('Veuillez sélectionner un fichier vidéo');
    return;
  }

  // Cacher la drop zone et montrer la progression
  dropZone.classList.add('hidden');
  progressContainer.classList.remove('hidden');
  successMessage.classList.add('hidden');

  // Afficher les détails du fichier
  const fileSize = (file.size / 1024 / 1024).toFixed(2);
  details.innerHTML = `
    <strong>Fichier:</strong> ${file.name}<br>
    <strong>Taille:</strong> ${fileSize} MB
  `;

  try {
    // Traiter la vidéo
    const result = await window.electronAPI.processVideo(file.path);

    if (result.success) {
      // Afficher le message de succès
      progressContainer.classList.add('hidden');
      successMessage.classList.remove('hidden');
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    alert('Erreur: ' + error.message);
    resetUI();
  }
}

// Listeners pour les progrès
window.electronAPI.onExtractionProgress((data) => {
  updateProgress(data.percent, 'Extraction de l\'audio...');
});

window.electronAPI.onUploadProgress((data) => {
  updateProgress(data.percent, `Upload: ${data.fileName}...`);
});

window.electronAPI.onStatusUpdate((data) => {
  statusText.textContent = data.message;
});

function updateProgress(percent, message) {
  const roundedPercent = Math.round(percent);
  progressFill.style.width = `${roundedPercent}%`;
  progressPercent.textContent = `${roundedPercent}%`;
  if (message) {
    statusText.textContent = message;
  }
}

// Bouton "Nouveau fichier"
newUploadButton.addEventListener('click', () => {
  resetUI();
});

function resetUI() {
  dropZone.classList.remove('hidden');
  progressContainer.classList.add('hidden');
  successMessage.classList.add('hidden');
  progressFill.style.width = '0%';
  progressPercent.textContent = '0%';
  statusText.textContent = 'Préparation...';
  details.innerHTML = '';
  fileInput.value = '';
}

// ============================================================================
// WATCH FOLDER
// ============================================================================

const toggleWatchButton = document.getElementById('toggle-watch');
const watchFolderInfo = document.getElementById('watch-folder-info');
const watchedFolderPath = document.getElementById('watched-folder-path');
const selectFolderButton = document.getElementById('select-folder-button');
const watchActivity = document.getElementById('watch-activity');
const watchStatusDot = document.getElementById('watch-status');
const watchText = document.getElementById('watch-text');

let isWatching = false;
let currentWatchedFolder = null;

// Vérifier si un dossier est déjà surveillé au démarrage
window.electronAPI.getWatchedFolder().then((result) => {
  if (result.isWatching && result.folderPath) {
    isWatching = true;
    currentWatchedFolder = result.folderPath;
    updateWatchUI();
  }
});

// Toggle watch
toggleWatchButton.addEventListener('click', async () => {
  if (!isWatching) {
    // Activer la surveillance
    watchFolderInfo.classList.remove('hidden');
    if (!currentWatchedFolder) {
      // Sélectionner un dossier
      const result = await window.electronAPI.selectWatchFolder();
      if (result.success) {
        currentWatchedFolder = result.folderPath;
        watchedFolderPath.textContent = currentWatchedFolder;
        startWatching();
      }
    } else {
      startWatching();
    }
  } else {
    // Désactiver la surveillance
    await window.electronAPI.stopWatching();
    isWatching = false;
    watchActivity.classList.add('hidden');
    updateWatchUI();
  }
});

// Sélectionner un dossier
selectFolderButton.addEventListener('click', async () => {
  const result = await window.electronAPI.selectWatchFolder();
  if (result.success) {
    currentWatchedFolder = result.folderPath;
    watchedFolderPath.textContent = currentWatchedFolder;
    if (isWatching) {
      // Redémarrer la surveillance avec le nouveau dossier
      await window.electronAPI.stopWatching();
      startWatching();
    }
  }
});

async function startWatching() {
  const result = await window.electronAPI.startWatching(currentWatchedFolder);
  if (result.success) {
    isWatching = true;
    watchActivity.classList.remove('hidden');
    updateWatchUI();
    addWatchActivity('Surveillance activée', 'success');
  }
}

function updateWatchUI() {
  if (isWatching) {
    toggleWatchButton.classList.add('active');
    watchText.textContent = 'Actif';
    watchFolderInfo.classList.remove('hidden');
    if (currentWatchedFolder) {
      watchedFolderPath.textContent = currentWatchedFolder;
    }
  } else {
    toggleWatchButton.classList.remove('active');
    watchText.textContent = 'Activer';
    watchFolderInfo.classList.add('hidden');
  }
}

function addWatchActivity(message, type = 'processing', fileName = null) {
  // Afficher la section watch-activity si cachée
  if (watchActivity.classList.contains('hidden')) {
    watchActivity.classList.remove('hidden');
  }

  // Si fileName fourni, chercher si item existe déjà et le mettre à jour
  if (fileName) {
    const existingItem = watchActivity.querySelector(`[data-filename="${fileName}"]`);
    if (existingItem) {
      const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '🔄';
      existingItem.className = `watch-activity-item ${type}`;
      existingItem.innerHTML = `<span>${icon}</span><span>${message}</span>`;
      return;
    }
  }

  // Créer nouvel item
  const item = document.createElement('div');
  item.className = `watch-activity-item ${type}`;
  if (fileName) {
    item.setAttribute('data-filename', fileName);
  }

  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '🔄';
  item.innerHTML = `<span>${icon}</span><span>${message}</span>`;

  watchActivity.insertBefore(item, watchActivity.firstChild);

  // Limiter à 10 items
  while (watchActivity.children.length > 10) {
    watchActivity.removeChild(watchActivity.lastChild);
  }
}

// Listeners pour les événements du watch folder
window.electronAPI.onWatchFolderNewFile((data) => {
  addWatchActivity(`${data.fileName} - Détecté`, 'processing', data.fileName);
});

window.electronAPI.onWatchFolderProgress((data) => {
  const stageText = data.stage === 'extraction' ? 'Extraction audio' :
                    data.stage === 'upload-audio' ? 'Upload audio' :
                    data.stage === 'upload-video' ? 'Upload vidéo' : data.message;
  addWatchActivity(`${data.fileName} - ${stageText}`, 'processing', data.fileName);
});

window.electronAPI.onWatchFolderSuccess((data) => {
  addWatchActivity(`${data.fileName} - Terminé ✓`, 'success', data.fileName);
});

window.electronAPI.onWatchFolderError((data) => {
  addWatchActivity(`${data.fileName} - Erreur: ${data.error}`, 'error', data.fileName);
});

window.electronAPI.onWatchFolderAutoStarted((data) => {
  // Le watch folder a démarré automatiquement au lancement de l'app
  isWatching = true;
  currentWatchedFolder = data.folderPath;
  updateWatchUI();
  addWatchActivity('Surveillance activée automatiquement', 'success');
});
