'use strict';

/**
 * Automation worker - orchestrates transcription + highlights cycles.
 * Port of cloud_run_server.py + Cloud Scheduler.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const RunPodClient = require('./runpod-client');
const R2Uploader = require('./r2-uploader');
const DriveService = require('./drive-service');
const { generateAllOutputs } = require('./output-generator');
const { extractHighlights, writeExcel } = require('./highlight-extractor');

// ─── State ────────────────────────────────────────────────────────────────────

let transcriptionRunning = false;
let highlightsRunning = false;
let transcriptionQueue = [];   // { fileName, status, startTime, error }
let highlightsQueue = [];

const MAX_RETRIES = 3;
const transcriptionFailures = new Map();  // fileName → failureCount

let transcriptionTimer = null;
let highlightsTimer = null;

let emitter = null;           // EventEmitter to push updates to main.js
let driveService = null;
let r2Uploader = null;
let runpodClient = null;
let machineId = null;
let config = null;            // Full settings object

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Start automation cycles.
 * @param {object} opts
 * @param {object} opts.oauth2Client
 * @param {object} opts.settings - App settings from electron-store
 * @param {string} opts.machineId - Unique machine UUID
 * @param {EventEmitter} opts.events - To emit updates to renderer
 */
function start(opts) {
  config = opts.settings;
  machineId = opts.machineId;
  emitter = opts.events;

  driveService = new DriveService(opts.oauth2Client);

  if (config.r2?.accountId) {
    r2Uploader = new R2Uploader({
      accountId: config.r2.accountId,
      accessKeyId: config.r2.accessKeyId,
      secretAccessKey: config.r2.secretAccessKey,
      bucket: config.r2.bucket,
      publicDomain: config.r2.publicDomain
    });
  }

  if (config.runpod?.apiKey && config.runpod?.endpointId) {
    const endpoint = `https://api.runpod.ai/v2/${config.runpod.endpointId}`;
    runpodClient = new RunPodClient(config.runpod.apiKey, endpoint);
  }

  // Transcription cycle: every 5 minutes
  runTranscriptionCycle();
  transcriptionTimer = setInterval(runTranscriptionCycle, 5 * 60 * 1000);

  // Highlights cycle: every 2 minutes
  runHighlightsCycle();
  highlightsTimer = setInterval(runHighlightsCycle, 2 * 60 * 1000);

  log('✅ Automation démarrée');
}

/**
 * Stop all automation cycles.
 */
function stop() {
  if (transcriptionTimer) { clearInterval(transcriptionTimer); transcriptionTimer = null; }
  if (highlightsTimer) { clearInterval(highlightsTimer); highlightsTimer = null; }
  log('⏹ Automation arrêtée');
}

/**
 * Get current status snapshot.
 */
function getStatus() {
  return {
    running: !!(transcriptionTimer || highlightsTimer),
    transcriptionRunning,
    highlightsRunning,
    transcriptionQueue: [...transcriptionQueue],
    highlightsQueue: [...highlightsQueue]
  };
}

/**
 * Trigger a transcription cycle immediately.
 */
function runTranscriptionNow() {
  runTranscriptionCycle();
}

/**
 * Trigger a highlights cycle immediately.
 */
function runHighlightsNow() {
  runHighlightsCycle();
}

// ─── Transcription Cycle ──────────────────────────────────────────────────────

async function runTranscriptionCycle() {
  if (transcriptionRunning) return;
  if (!runpodClient || !r2Uploader) {
    log('⚠️ RunPod ou R2 non configuré — cycle transcription ignoré');
    return;
  }

  transcriptionRunning = true;
  emit('cycle-start', { type: 'transcription' });

  try {
    const sourceFolderId = config.drive?.sourceFolderId;
    if (!sourceFolderId) {
      log('⚠️ Dossier source non configuré — cycle ignoré');
      return;
    }
    const transcriptionsFolderId = config.drive?.transcriptionsFolderId;
    const processingFolderId = await ensureProcessingFolder(sourceFolderId);

    const files = await driveService.listAudioFiles(sourceFolderId);
    log(`📋 ${files.length} fichier(s) WAV trouvé(s) dans source_files`);

    for (const file of files) {
      const baseName = file.name.replace(/\.wav$/i, '');

      // Check if already transcribed
      if (await driveService.transcriptionExists(baseName, transcriptionsFolderId)) {
        log(`⏭️  Déjà transcrit: ${file.name}`);
        continue;
      }

      // Skip files that failed too many times
      const failures = transcriptionFailures.get(file.name) || 0;
      if (failures >= MAX_RETRIES) {
        log(`🚫 ${file.name} ignoré après ${MAX_RETRIES} échecs`);
        continue;
      }

      // Check/acquire lock
      const lockName = `${file.name}.lock`;
      const lockStatus = await driveService.checkLockFile(processingFolderId, lockName);
      if (lockStatus.locked) {
        log(`🔒 En cours sur une autre machine: ${file.name}`);
        continue;
      }
      // Remove stale lock if needed
      if (lockStatus.fileId && lockStatus.stale) {
        await driveService.deleteFile(lockStatus.fileId);
      }

      let lockFileId = null;
      try {
        lockFileId = await driveService.createLockFile(processingFolderId, lockName, machineId);
        await transcribeFile(file, baseName, transcriptionsFolderId);
      } catch (err) {
        const failures = (transcriptionFailures.get(file.name) || 0) + 1;
        transcriptionFailures.set(file.name, failures);
        log(`❌ Erreur transcription ${file.name} (tentative ${failures}/${MAX_RETRIES}): ${err.message}`);
        if (failures >= MAX_RETRIES) {
          log(`🚫 ${file.name} mis en quarantaine après ${MAX_RETRIES} échecs`);
        }
        updateQueueItem('transcription', file.name, 'error', err.message);
      } finally {
        if (lockFileId) await driveService.deleteFile(lockFileId);
      }
    }
  } catch (err) {
    log(`❌ Erreur cycle transcription: ${err.message}`);
    if (isAuthError(err)) {
      log('🔐 Erreur d\'authentification Google — reconnectez-vous dans l\'app');
      emit('auth-error', { message: 'Reconnexion Google requise' });
    }
  } finally {
    transcriptionRunning = false;
    emit('cycle-end', { type: 'transcription' });
  }
}

async function transcribeFile(file, baseName, transcriptionsFolderId) {
  const tmpDir = path.join(os.tmpdir(), 'transcription-app');
  fs.mkdirSync(tmpDir, { recursive: true });

  addQueueItem('transcription', file.name);

  // 1. Download WAV
  log(`📥 Téléchargement: ${file.name}`);
  const localWav = path.join(tmpDir, file.name);
  await driveService.downloadFile(file.id, localWav, (dl, total) => {
    updateQueueItem('transcription', file.name, 'downloading', null,
      `Téléchargement ${Math.round((dl / total) * 100)}%`);
  });

  let r2Key = null;
  let audioUrl;

  try {
    // 2. Upload to R2
    log(`☁️  Upload R2: ${file.name}`);
    updateQueueItem('transcription', file.name, 'uploading-r2');
    const r2Result = await r2Uploader.uploadFile(localWav);
    audioUrl = r2Result.url;
    r2Key = r2Result.key;

    // 3. RunPod transcription
    log(`🚀 Transcription RunPod: ${file.name}`);
    updateQueueItem('transcription', file.name, 'transcribing');
    const whisperResult = await runpodClient.transcribeAudio(audioUrl);
    log(`✅ Transcription terminée: ${file.name}`);

    // 4. Generate outputs
    updateQueueItem('transcription', file.name, 'generating');
    const { paragraphsDocId, jsonFileId } = await generateAllOutputs(
      baseName,
      whisperResult,
      driveService,
      transcriptionsFolderId,
      log
    );
    log(`✅ Outputs générés pour: ${file.name}`);

    updateQueueItem('transcription', file.name, 'done');
    emit('transcription-complete', { fileName: file.name, paragraphsDocId, jsonFileId });

  } finally {
    // Cleanup
    try { fs.unlinkSync(localWav); } catch { /* ignore */ }
    if (r2Key) await r2Uploader.deleteFile(r2Key);
  }
}

// ─── Highlights Cycle ─────────────────────────────────────────────────────────

async function runHighlightsCycle() {
  if (highlightsRunning) return;

  highlightsRunning = true;
  emit('cycle-start', { type: 'highlights' });

  try {
    const transcriptionsFolderId = config.drive?.transcriptionsFolderId;
    const sourceFolderId = config.drive?.sourceFolderId;
    const segmentsFolderId = config.drive?.segmentsFolderId;
    const excelFolderId = config.drive?.excelFolderId;
    const processingFolderId = await ensureProcessingFolder(transcriptionsFolderId);

    if (!segmentsFolderId && !excelFolderId) {
      log('⚠️ Dossiers segments/excel non configurés — cycle highlights ignoré');
      return;
    }

    const docs = await driveService.listDocsReadyForHighlights(transcriptionsFolderId);
    log(`📋 ${docs.length} doc(s) avec marqueur 🎬 READY 🎬`);

    for (const doc of docs) {
      const lockName = `${doc.name}_highlights.lock`;
      const lockStatus = await driveService.checkLockFile(processingFolderId, lockName);
      if (lockStatus.locked) {
        log(`🔒 En cours: ${doc.name}`);
        continue;
      }
      if (lockStatus.fileId && lockStatus.stale) {
        await driveService.deleteFile(lockStatus.fileId);
      }

      let lockFileId = null;
      try {
        lockFileId = await driveService.createLockFile(processingFolderId, lockName, machineId);
        await processHighlights(doc, sourceFolderId, segmentsFolderId, excelFolderId, transcriptionsFolderId);
      } catch (err) {
        log(`❌ Erreur highlights ${doc.name}: ${err.message}`);
        updateQueueItem('highlights', doc.name, 'error', err.message);
      } finally {
        if (lockFileId) await driveService.deleteFile(lockFileId);
      }
    }
  } catch (err) {
    log(`❌ Erreur cycle highlights: ${err.message}`);
    if (isAuthError(err)) {
      emit('auth-error', { message: 'Reconnexion Google requise' });
    }
  } finally {
    highlightsRunning = false;
    emit('cycle-end', { type: 'highlights' });
  }
}

async function processHighlights(doc, sourceFolderId, segmentsFolderId, excelFolderId, transcriptionsFolderId) {
  const tmpDir = path.join(os.tmpdir(), 'transcription-app');
  fs.mkdirSync(tmpDir, { recursive: true });

  addQueueItem('highlights', doc.name);

  // Derive base name: strip "_paragraphs_timestamps" suffix
  const baseName = doc.name.replace(/_paragraphs_timestamps$/, '');

  // 1. Find and download _complete_data.json
  log(`🔍 Recherche JSON pour: ${baseName}`);
  const jsonFiles = await driveService.listFilesWithPattern(transcriptionsFolderId, `${baseName}_complete_data.json`);
  if (!jsonFiles.length) {
    throw new Error(`_complete_data.json introuvable pour ${baseName}`);
  }

  const jsonLocalPath = path.join(tmpDir, `${baseName}_complete_data.json`);
  await driveService.downloadFile(jsonFiles[0].id, jsonLocalPath);
  const completeData = JSON.parse(fs.readFileSync(jsonLocalPath, 'utf-8'));

  // 2. Use document text already fetched by listDocsReadyForHighlights
  const fullDocText = doc.text;

  // 3. Extract highlights from inline markers (🎬 S1 🎬 ... 🎬 /S1 🎬)
  const rows = extractHighlights(fullDocText, completeData);
  if (!rows.length) {
    log(`⚠️ Aucun segment 🎬 trouvé dans: ${doc.name}`);
    updateQueueItem('highlights', doc.name, 'done');
    return;
  }

  log(`🎬 ${rows.length} highlight(s) trouvé(s)`);

  // 4. Generate Excel
  const excelFilename = `${baseName}_highlights.xlsx`;
  const excelLocalPath = path.join(tmpDir, excelFilename);
  await writeExcel(rows, excelLocalPath);
  log(`📊 Excel généré: ${excelFilename}`);

  // 5. Upload Excel to Drive
  if (excelFolderId) {
    const excelFileId = await driveService.uploadFile(excelLocalPath, excelFilename, excelFolderId);
    log(`☁️  Excel uploadé: ${excelFilename} (${excelFileId})`);
  }

  // 6. Extract video segments if FFmpeg available
  const videoFiles = await driveService.listFilesWithPattern(sourceFolderId, baseName);
  const videoFile = videoFiles.find(f =>
    /\.(mp4|mov|avi|mkv|m4v)$/i.test(f.name)
  );

  if (videoFile && segmentsFolderId) {
    await extractVideoSegments(videoFile, rows, baseName, segmentsFolderId, tmpDir);
  }

  // 7. Mark doc as processed (🎬 READY 🎬 → 🎬 PROCESSED 🎬)
  await driveService.markDocAsProcessed(doc.id);
  log(`✅ Doc marqué PROCESSED: ${doc.name}`);

  updateQueueItem('highlights', doc.name, 'done');
  emit('highlights-complete', { docName: doc.name, segmentCount: rows.length });

  // Cleanup temp files
  try { fs.unlinkSync(jsonLocalPath); } catch { /* ignore */ }
  try { fs.unlinkSync(excelLocalPath); } catch { /* ignore */ }
}

async function extractVideoSegments(videoFile, rows, baseName, segmentsFolderId, tmpDir) {
  let ffmpegPath;
  try {
    ffmpegPath = require('ffmpeg-static');
    if (!ffmpegPath) throw new Error('ffmpeg-static returned null');
  } catch {
    log('⚠️ FFmpeg non disponible — segments vidéo ignorés');
    return;
  }

  const { execFile } = require('child_process');

  const videoLocalPath = path.join(tmpDir, videoFile.name);
  log(`📥 Téléchargement vidéo: ${videoFile.name}`);
  let lastPct = 0;
  await driveService.downloadFile(videoFile.id, videoLocalPath, (dl, total) => {
    if (!total) return;
    const pct = Math.round((dl / total) * 100);
    if (pct >= lastPct + 10) {
      lastPct = pct;
      log(`📥 Vidéo ${pct}% (${Math.round(dl / 1024 / 1024)}MB / ${Math.round(total / 1024 / 1024)}MB)`);
    }
  });

  // Same command as Python _extract_segment_ffmpeg:
  // ffmpeg -accurate_seek -ss {start} -i {input} -t {duration} -c:v copy -c:a aac -avoid_negative_ts make_zero -y {output}
  function runFfmpeg(args) {
    return new Promise((resolve, reject) => {
      execFile(ffmpegPath, args, { maxBuffer: 10 * 1024 * 1024 }, (err, stdout, stderr) => {
        if (err) reject(new Error(stderr || err.message));
        else resolve();
      });
    });
  }

  try {
    // Create subfolder {baseName}_segments inside segments_output — same as Python _get_or_create_subfolder
    const subfolderName = `${baseName}_segments`;
    const subFolderId = await driveService.findOrCreateFolder(segmentsFolderId, subfolderName);
    log(`📁 Dossier segments: ${subfolderName}`);

    for (const row of rows) {
      const segNum = row['Numéro'];
      const group = row['Groupe'] || `S${segNum}`;
      const start = row['Début (secondes)'];
      const end = row['Fin (secondes)'];
      const duration = row['Durée (secondes)'];

      // Naming: {group}_{start}-{end}.mp4 — same as Python
      const startCode = secondsToTimecodeShort(start);
      const endCode = secondsToTimecodeShort(end);
      const segName = `${group}_${startCode}-${endCode}.mp4`;
      const segLocalPath = path.join(tmpDir, segName);

      log(`✂️  Découpe ${group}: ${start}s → ${end}s`);
      await runFfmpeg([
        '-accurate_seek',
        '-ss', String(start),
        '-i', videoLocalPath,
        '-t', String(duration),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-avoid_negative_ts', 'make_zero',
        '-y',
        segLocalPath
      ]);

      const segFileId = await driveService.uploadFile(segLocalPath, segName, subFolderId);
      log(`✅ Segment uploadé: ${segName} (${segFileId})`);

      try { fs.unlinkSync(segLocalPath); } catch { /* ignore */ }
    }
  } finally {
    try { fs.unlinkSync(videoLocalPath); } catch { /* ignore */ }
  }
}

// Converts seconds to MMSS format for filenames (same as Python _seconds_to_timecode_short)
function secondsToTimecodeShort(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}${String(s).padStart(2, '0')}`;
}

// ─── Queue helpers ────────────────────────────────────────────────────────────

function addQueueItem(type, fileName) {
  const queue = type === 'transcription' ? transcriptionQueue : highlightsQueue;
  const existing = queue.find(q => q.fileName === fileName);
  if (!existing) {
    queue.push({ fileName, status: 'pending', startTime: Date.now() });
  }
  emitStatus();
}

function updateQueueItem(type, fileName, status, error = null, message = null) {
  const queue = type === 'transcription' ? transcriptionQueue : highlightsQueue;
  const item = queue.find(q => q.fileName === fileName);
  if (item) {
    item.status = status;
    item.message = message;  // Always update (clears old message when null)
    if (error) item.error = error;
  }
  emitStatus();
}

// ─── Utils ────────────────────────────────────────────────────────────────────

function isAuthError(err) {
  const msg = (err.message || '').toLowerCase();
  return msg.includes('deleted_client') ||
    msg.includes('invalid_grant') ||
    msg.includes('unauthorized') ||
    msg.includes('not authenticated') ||
    msg.includes('token');
}

async function ensureProcessingFolder(parentFolderId) {
  return driveService.findOrCreateFolder(parentFolderId, '_processing');
}

function log(message) {
  console.log(message);
  emit('log', { message, time: new Date().toISOString() });
}

function emit(event, data) {
  if (emitter) emitter.emit(event, data);
}

function emitStatus() {
  emit('status-update', getStatus());
}

// ─── Exports ──────────────────────────────────────────────────────────────────

module.exports = {
  start,
  stop,
  getStatus,
  runTranscriptionNow,
  runHighlightsNow
};
