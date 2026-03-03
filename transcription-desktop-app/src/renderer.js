'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
// SCREENS & INIT
// ═══════════════════════════════════════════════════════════════════════════════

const authScreen      = document.getElementById('auth-screen');
const onboardingScreen = document.getElementById('onboarding-screen');
const mainScreen      = document.getElementById('main-screen');
const authButton      = document.getElementById('auth-button');

window.electronAPI.checkAuth().then(async (isAuthenticated) => {
  if (!isAuthenticated) {
    showScreen('auth');
    return;
  }
  const settings = await window.electronAPI.getSettings();
  const isFirstRun = !settings.onboardingDone;
  if (isFirstRun) {
    showScreen('onboarding');
    wizardStep1();
  } else {
    showScreen('main');
    initMainScreen();
  }
});

authButton.addEventListener('click', async () => {
  authButton.disabled = true;
  authButton.textContent = 'Connexion en cours...';
  try {
    const result = await window.electronAPI.authenticateGoogle();
    if (result.success) {
      const settings = await window.electronAPI.getSettings();
      if (!settings.onboardingDone) {
        showScreen('onboarding');
        wizardStep1();
      } else {
        showScreen('main');
        initMainScreen();
      }
    }
  } catch (error) {
    alert('Erreur authentification: ' + error.message);
    authButton.disabled = false;
    authButton.innerHTML = '<img src="https://www.google.com/favicon.ico" class="google-icon"> Se connecter avec Google';
  }
});

function showScreen(name) {
  authScreen.classList.add('hidden');
  onboardingScreen.classList.add('hidden');
  mainScreen.classList.add('hidden');
  if (name === 'auth') authScreen.classList.remove('hidden');
  else if (name === 'onboarding') onboardingScreen.classList.remove('hidden');
  else mainScreen.classList.remove('hidden');
}

// ═══════════════════════════════════════════════════════════════════════════════
// ONBOARDING WIZARD
// ═══════════════════════════════════════════════════════════════════════════════

function wizardStep1() {
  showWizardStep(1);
}

function showWizardStep(n) {
  [1, 2, 3].forEach(i => {
    document.getElementById(`wizard-step-${i}`).classList.toggle('hidden', i !== n);
    const dot = document.querySelector(`.step[data-step="${i}"]`);
    if (dot) dot.classList.toggle('active', i === n);
    if (dot) dot.classList.toggle('done', i < n);
  });
}

document.getElementById('wizard-next-1').addEventListener('click', () => showWizardStep(2));

document.getElementById('wz-test-runpod').addEventListener('click', async () => {
  const key = document.getElementById('wz-runpod-key').value.trim();
  const endpoint = document.getElementById('wz-runpod-endpoint').value.trim();
  const statusEl = document.getElementById('wz-runpod-status');
  statusEl.classList.remove('hidden', 'test-ok', 'test-fail');
  statusEl.textContent = 'Test en cours...';
  statusEl.classList.remove('hidden');
  const res = await window.electronAPI.testRunpodConnection({ apiKey: key, endpointId: endpoint });
  if (res.success) {
    statusEl.classList.add('test-ok');
    statusEl.textContent = '✅ Connexion RunPod OK';
  } else {
    statusEl.classList.add('test-fail');
    statusEl.textContent = '❌ ' + res.error;
  }
});

document.getElementById('wizard-next-2').addEventListener('click', () => showWizardStep(3));

document.getElementById('wz-test-r2').addEventListener('click', async () => {
  const r2Config = wizardGetR2Config();
  const statusEl = document.getElementById('wz-r2-status');
  statusEl.classList.remove('hidden', 'test-ok', 'test-fail');
  statusEl.textContent = 'Test en cours...';
  statusEl.classList.remove('hidden');
  const res = await window.electronAPI.testR2Connection(r2Config);
  if (res.success) {
    statusEl.classList.add('test-ok');
    statusEl.textContent = '✅ Connexion R2 OK';
  } else {
    statusEl.classList.add('test-fail');
    statusEl.textContent = '❌ ' + res.error;
  }
});

document.getElementById('wizard-finish').addEventListener('click', async () => {
  const runpodKey = document.getElementById('wz-runpod-key').value.trim();
  const runpodEndpoint = document.getElementById('wz-runpod-endpoint').value.trim();
  const sourceFolder = document.getElementById('wz-source-folder').value.trim();
  const transcriptionsFolder = document.getElementById('wz-transcriptions-folder').value.trim();

  const settings = {
    onboardingDone: true,
    autoStart: true,
    runpod: { apiKey: runpodKey, endpointId: runpodEndpoint },
    r2: wizardGetR2Config(),
    drive: {
      sourceFolderId: sourceFolder,
      transcriptionsFolderId: transcriptionsFolder
    }
  };

  await window.electronAPI.saveSettings(settings);
  showScreen('main');
  initMainScreen();
  // Auto-start automation
  await window.electronAPI.startAutomation();
});

function wizardGetR2Config() {
  return {
    accountId: document.getElementById('wz-r2-account').value.trim(),
    accessKeyId: document.getElementById('wz-r2-access-key').value.trim(),
    secretAccessKey: document.getElementById('wz-r2-secret').value.trim(),
    bucket: document.getElementById('wz-r2-bucket').value.trim(),
    publicDomain: document.getElementById('wz-r2-domain').value.trim()
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN SCREEN INIT
// ═══════════════════════════════════════════════════════════════════════════════

function initMainScreen() {
  initTabs();
  initUploadTab();
  initAutomationTab();
  initSettingsTab();
  loadSettings();
  initAutomationListeners();
  checkAutomationStatus();
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════════════════════════════════════════

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// UPLOAD TAB
// ═══════════════════════════════════════════════════════════════════════════════

function initUploadTab() {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const progressContainer = document.getElementById('progress-container');
  const statusText = document.getElementById('status-text');
  const progressPercent = document.getElementById('progress-percent');
  const progressFill = document.getElementById('progress-fill');
  const details = document.getElementById('details');
  const successMessage = document.getElementById('success-message');

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
  });

  async function handleFile(file) {
    if (!file.type.startsWith('video/')) { alert('Veuillez sélectionner un fichier vidéo'); return; }
    dropZone.classList.add('hidden');
    progressContainer.classList.remove('hidden');
    successMessage.classList.add('hidden');
    const fileSize = (file.size / 1024 / 1024).toFixed(2);
    details.innerHTML = `<strong>Fichier:</strong> ${file.name}<br><strong>Taille:</strong> ${fileSize} MB`;
    try {
      const result = await window.electronAPI.processVideo(file.path);
      if (result.success) {
        progressContainer.classList.add('hidden');
        successMessage.classList.remove('hidden');
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      alert('Erreur: ' + error.message);
      resetUploadUI();
    }
  }

  function resetUploadUI() {
    dropZone.classList.remove('hidden');
    progressContainer.classList.add('hidden');
    successMessage.classList.add('hidden');
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    statusText.textContent = 'Préparation...';
    details.innerHTML = '';
    fileInput.value = '';
  }

  document.getElementById('new-upload-button').addEventListener('click', resetUploadUI);

  window.electronAPI.onExtractionProgress((data) => {
    const pct = Math.round(data.percent || 0);
    progressFill.style.width = `${pct}%`;
    progressPercent.textContent = `${pct}%`;
    statusText.textContent = "Extraction audio...";
  });
  window.electronAPI.onUploadProgress((data) => {
    const pct = Math.round(data.percent || 0);
    progressFill.style.width = `${pct}%`;
    progressPercent.textContent = `${pct}%`;
    statusText.textContent = `Upload: ${data.fileName}...`;
  });

  // Watch folder
  const toggleWatch = document.getElementById('toggle-watch');
  const watchFolderInfo = document.getElementById('watch-folder-info');
  const watchedFolderPath = document.getElementById('watched-folder-path');
  const selectFolderButton = document.getElementById('select-folder-button');
  const watchActivity = document.getElementById('watch-activity');
  const watchStatusDot = document.getElementById('watch-status');
  const watchText = document.getElementById('watch-text');
  let isWatching = false;
  let currentWatchedFolder = null;

  window.electronAPI.getWatchedFolder().then((result) => {
    if (result.isWatching && result.folderPath) {
      isWatching = true;
      currentWatchedFolder = result.folderPath;
      updateWatchUI();
    }
  });

  toggleWatch.addEventListener('click', async () => {
    if (!isWatching) {
      watchFolderInfo.classList.remove('hidden');
      if (!currentWatchedFolder) {
        const result = await window.electronAPI.selectWatchFolder();
        if (result.success) {
          currentWatchedFolder = result.folderPath;
          watchedFolderPath.textContent = currentWatchedFolder;
          await startWatch();
        }
      } else {
        await startWatch();
      }
    } else {
      await window.electronAPI.stopWatching();
      isWatching = false;
      watchActivity.classList.add('hidden');
      updateWatchUI();
    }
  });

  selectFolderButton.addEventListener('click', async () => {
    const result = await window.electronAPI.selectWatchFolder();
    if (result.success) {
      currentWatchedFolder = result.folderPath;
      watchedFolderPath.textContent = currentWatchedFolder;
      if (isWatching) { await window.electronAPI.stopWatching(); await startWatch(); }
    }
  });

  async function startWatch() {
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
      toggleWatch.classList.add('active');
      watchText.textContent = 'Actif';
      watchFolderInfo.classList.remove('hidden');
      if (currentWatchedFolder) watchedFolderPath.textContent = currentWatchedFolder;
    } else {
      toggleWatch.classList.remove('active');
      watchText.textContent = 'Activer';
      watchFolderInfo.classList.add('hidden');
    }
  }

  function addWatchActivity(message, type = 'processing', fileName = null) {
    if (watchActivity.classList.contains('hidden')) watchActivity.classList.remove('hidden');
    if (fileName) {
      const existing = watchActivity.querySelector(`[data-filename="${fileName}"]`);
      if (existing) {
        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '🔄';
        existing.className = `watch-activity-item ${type}`;
        existing.innerHTML = `<span>${icon}</span><span>${message}</span>`;
        return;
      }
    }
    const item = document.createElement('div');
    item.className = `watch-activity-item ${type}`;
    if (fileName) item.setAttribute('data-filename', fileName);
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '🔄';
    item.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    watchActivity.insertBefore(item, watchActivity.firstChild);
    while (watchActivity.children.length > 10) watchActivity.removeChild(watchActivity.lastChild);
  }

  window.electronAPI.onWatchFolderNewFile((data) => addWatchActivity(`${data.fileName} - Détecté`, 'processing', data.fileName));
  window.electronAPI.onWatchFolderProgress((data) => addWatchActivity(`${data.fileName} - ${data.message || data.stage}`, 'processing', data.fileName));
  window.electronAPI.onWatchFolderSuccess((data) => addWatchActivity(`${data.fileName} - Terminé ✓`, 'success', data.fileName));
  window.electronAPI.onWatchFolderError((data) => addWatchActivity(`${data.fileName} - Erreur: ${data.error}`, 'error', data.fileName));
  window.electronAPI.onWatchFolderAutoStarted((data) => {
    isWatching = true;
    currentWatchedFolder = data.folderPath;
    updateWatchUI();
    addWatchActivity('Surveillance activée automatiquement', 'success');
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTOMATION TAB
// ═══════════════════════════════════════════════════════════════════════════════

let nextScanTimer = null;
let nextScanCountdown = 300; // 5 min
let isAutomationRunning = false;
const MAX_LOG_LINES = 100;

function initAutomationTab() {
  const toggleBtn = document.getElementById('toggle-automation');
  const btnTranscription = document.getElementById('btn-run-transcription');
  const btnHighlights = document.getElementById('btn-run-highlights');
  const btnClearLogs = document.getElementById('btn-clear-logs');

  toggleBtn.addEventListener('click', async () => {
    if (isAutomationRunning) {
      await window.electronAPI.stopAutomation();
    } else {
      await window.electronAPI.startAutomation();
    }
  });

  btnTranscription.addEventListener('click', async () => {
    await window.electronAPI.runTranscriptionNow();
  });

  btnHighlights.addEventListener('click', async () => {
    await window.electronAPI.runHighlightsNow();
  });

  btnClearLogs.addEventListener('click', () => {
    document.getElementById('log-panel').innerHTML = '';
  });
}

function initAutomationListeners() {
  window.electronAPI.onAutomationStatus((data) => {
    updateAutomationUI(data);
  });

  window.electronAPI.onAutomationUpdate((data) => {
    if (data.type === 'transcription-complete') {
      addLog(`✅ Transcription terminée: ${data.fileName}`);
    } else if (data.type === 'highlights-complete') {
      addLog(`✅ Highlights terminés: ${data.docName} (${data.segmentCount} segments)`);
    } else if (data.type === 'auth-error') {
      addLog('🔐 Session Google expirée — reconnexion requise');
      // Afficher un bandeau d'alerte
      showAuthAlert();
    }
  });

  window.electronAPI.onLogLine((data) => {
    addLog(data.message);
  });
}

async function checkAutomationStatus() {
  const status = await window.electronAPI.getAutomationStatus();
  updateAutomationUI(status);
}

function updateAutomationUI(status) {
  isAutomationRunning = status.enabled || status.running;

  const toggleBtn = document.getElementById('toggle-automation');
  const statusDot = document.getElementById('auto-status-dot');
  const statusText = document.getElementById('auto-status-text');
  const globalDot = document.getElementById('automation-dot');
  const btnTranscription = document.getElementById('btn-run-transcription');
  const btnHighlights = document.getElementById('btn-run-highlights');

  if (isAutomationRunning) {
    toggleBtn.classList.add('active');
    statusText.textContent = 'Actif';
    globalDot.classList.add('pulsing');
    btnTranscription.disabled = false;
    btnHighlights.disabled = false;

    if (!nextScanTimer) startScanCountdown();
  } else {
    toggleBtn.classList.remove('active');
    statusText.textContent = 'Activer';
    globalDot.classList.remove('pulsing');
    btnTranscription.disabled = true;
    btnHighlights.disabled = true;
    stopScanCountdown();
    document.getElementById('auto-next-scan').textContent = 'Prochain scan dans --';
  }

  // Update queues
  renderQueue('transcription-queue', status.transcriptionQueue || []);
  renderQueue('highlights-queue', status.highlightsQueue || []);
}

function renderQueue(containerId, items) {
  const container = document.getElementById(containerId);
  if (!items.length) {
    container.innerHTML = '<p class="empty-queue">Aucun fichier en attente</p>';
    return;
  }
  container.innerHTML = items.map(item => {
    const icon = item.status === 'done' ? '✅'
      : item.status === 'error' ? '❌'
      : item.status === 'transcribing' ? '🎙️'
      : item.status === 'uploading-r2' ? '☁️'
      : item.status === 'generating' ? '📝'
      : '🔄';
    const labels = {
      'pending': 'En attente',
      'downloading': item.message || 'Téléchargement...',
      'uploading-r2': 'Upload R2...',
      'transcribing': 'Transcription en cours...',
      'generating': 'Génération outputs...',
      'done': 'Terminé',
      'error': item.error || 'Erreur'
    };
    const msg = labels[item.status] || item.message || item.status;
    return `<div class="queue-item ${item.status}">
      <span class="queue-icon">${icon}</span>
      <span class="queue-name">${item.fileName}</span>
      <span class="queue-status">${msg}</span>
    </div>`;
  }).join('');
}

function startScanCountdown() {
  nextScanCountdown = 300;
  updateCountdownDisplay();
  nextScanTimer = setInterval(() => {
    nextScanCountdown--;
    if (nextScanCountdown <= 0) nextScanCountdown = 300;
    updateCountdownDisplay();
  }, 1000);
}

function stopScanCountdown() {
  if (nextScanTimer) { clearInterval(nextScanTimer); nextScanTimer = null; }
}

function updateCountdownDisplay() {
  const m = Math.floor(nextScanCountdown / 60);
  const s = nextScanCountdown % 60;
  document.getElementById('auto-next-scan').textContent =
    `Prochain scan dans ${m}:${String(s).padStart(2, '0')}`;
}

function showAuthAlert() {
  // Passer sur le tab Automation et afficher un bandeau
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  document.querySelector('.tab-btn[data-tab="automation"]').classList.add('active');
  document.getElementById('tab-automation').classList.remove('hidden');

  let alert = document.getElementById('auth-alert');
  if (!alert) {
    alert = document.createElement('div');
    alert.id = 'auth-alert';
    alert.className = 'auth-alert';
    alert.innerHTML = `
      <span>🔐 Session Google expirée — l'automation est en pause.</span>
      <button id="reauth-btn" class="primary-button" style="padding:6px 14px;font-size:0.85rem;">
        Reconnecter Google
      </button>
    `;
    document.getElementById('tab-automation').prepend(alert);
    document.getElementById('reauth-btn').addEventListener('click', async () => {
      const result = await window.electronAPI.authenticateGoogle();
      if (result.success) {
        alert.remove();
        addLog('✅ Reconnexion Google réussie');
        await window.electronAPI.startAutomation();
      }
    });
  }
}

function addLog(message) {
  const panel = document.getElementById('log-panel');
  const line = document.createElement('div');
  line.className = 'log-line';
  const time = new Date().toLocaleTimeString('fr-FR');
  line.textContent = `[${time}] ${message}`;
  panel.insertBefore(line, panel.firstChild);

  // Keep only last 100 lines
  while (panel.children.length > MAX_LOG_LINES) {
    panel.removeChild(panel.lastChild);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETTINGS TAB
// ═══════════════════════════════════════════════════════════════════════════════

function initSettingsTab() {
  document.getElementById('s-test-runpod').addEventListener('click', async () => {
    const key = document.getElementById('s-runpod-key').value.trim();
    const endpoint = document.getElementById('s-runpod-endpoint').value.trim();
    const statusEl = document.getElementById('s-runpod-status');
    statusEl.classList.remove('hidden', 'test-ok', 'test-fail');
    statusEl.textContent = 'Test...';
    statusEl.classList.remove('hidden');
    const res = await window.electronAPI.testRunpodConnection({ apiKey: key, endpointId: endpoint });
    statusEl.classList.add(res.success ? 'test-ok' : 'test-fail');
    statusEl.textContent = res.success ? '✅ OK' : ('❌ ' + res.error);
  });

  document.getElementById('s-test-r2').addEventListener('click', async () => {
    const r2Config = getSettingsR2Config();
    const statusEl = document.getElementById('s-r2-status');
    statusEl.classList.remove('hidden', 'test-ok', 'test-fail');
    statusEl.textContent = 'Test...';
    statusEl.classList.remove('hidden');
    const res = await window.electronAPI.testR2Connection(r2Config);
    statusEl.classList.add(res.success ? 'test-ok' : 'test-fail');
    statusEl.textContent = res.success ? '✅ OK' : ('❌ ' + res.error);
  });

  document.getElementById('s-save').addEventListener('click', async () => {
    const settings = {
      runpod: {
        apiKey: document.getElementById('s-runpod-key').value.trim(),
        endpointId: document.getElementById('s-runpod-endpoint').value.trim()
      },
      r2: getSettingsR2Config(),
      drive: {
        sourceFolderId: document.getElementById('s-source-folder').value.trim(),
        transcriptionsFolderId: document.getElementById('s-transcriptions-folder').value.trim(),
        segmentsFolderId: document.getElementById('s-segments-folder').value.trim(),
        excelFolderId: document.getElementById('s-excel-folder').value.trim()
      },
      autoStart: document.getElementById('s-auto-start').checked
    };

    await window.electronAPI.saveSettings(settings);
    const statusEl = document.getElementById('s-save-status');
    statusEl.textContent = '✅ Sauvegardé';
    setTimeout(() => { statusEl.textContent = ''; }, 2000);
  });
}

function getSettingsR2Config() {
  return {
    accountId: document.getElementById('s-r2-account').value.trim(),
    accessKeyId: document.getElementById('s-r2-access-key').value.trim(),
    secretAccessKey: document.getElementById('s-r2-secret').value.trim(),
    bucket: document.getElementById('s-r2-bucket').value.trim(),
    publicDomain: document.getElementById('s-r2-domain').value.trim()
  };
}

async function loadSettings() {
  const settings = await window.electronAPI.getSettings();

  if (settings.runpod) {
    document.getElementById('s-runpod-key').value = settings.runpod.apiKey || '';
    document.getElementById('s-runpod-endpoint').value = settings.runpod.endpointId || '';
  }
  if (settings.r2) {
    document.getElementById('s-r2-account').value = settings.r2.accountId || '';
    document.getElementById('s-r2-access-key').value = settings.r2.accessKeyId || '';
    document.getElementById('s-r2-secret').value = settings.r2.secretAccessKey || '';
    document.getElementById('s-r2-bucket').value = settings.r2.bucket || '';
    document.getElementById('s-r2-domain').value = settings.r2.publicDomain || '';
  }
  if (settings.drive) {
    document.getElementById('s-source-folder').value = settings.drive.sourceFolderId || '';
    document.getElementById('s-transcriptions-folder').value = settings.drive.transcriptionsFolderId || '';
    document.getElementById('s-segments-folder').value = settings.drive.segmentsFolderId || '';
    document.getElementById('s-excel-folder').value = settings.drive.excelFolderId || '';
  }
  document.getElementById('s-auto-start').checked = !!settings.autoStart;
}
