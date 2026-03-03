'use strict';

/**
 * Drive service - extends existing Drive functionality.
 * Port of drive_manager.py, reusing oauth2Client from main.js.
 */

const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

class DriveService {
  /**
   * @param {object} oauth2Client - Authenticated Google OAuth2 client from main.js
   */
  constructor(oauth2Client) {
    this.auth = oauth2Client;
  }

  get drive() {
    return google.drive({ version: 'v3', auth: this.auth });
  }

  get docs() {
    return google.docs({ version: 'v1', auth: this.auth });
  }

  /**
   * Ensure token is fresh; refresh if needed.
   */
  async ensureAuth() {
    const creds = this.auth.credentials;
    if (!creds || !creds.access_token) {
      throw new Error('Not authenticated with Google');
    }
    // Refresh if expiry_date is within 5 minutes
    if (creds.expiry_date && creds.expiry_date < Date.now() + 5 * 60 * 1000) {
      await this.auth.refreshAccessToken();
    }
  }

  /**
   * List .wav audio files in a Drive folder.
   * @param {string} folderId
   * @returns {Promise<Array>} Array of file objects {id, name, size}
   */
  async listAudioFiles(folderId) {
    await this.ensureAuth();
    const res = await this.drive.files.list({
      q: `'${folderId}' in parents and trashed=false`,
      fields: 'files(id,name,size,mimeType)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
      pageSize: 1000
    });
    const all = res.data.files || [];
    return all.filter(f => f.name.toLowerCase().endsWith('.wav'));
  }

  /**
   * Check if a transcription already exists for this audio file.
   * @param {string} baseFilename - Filename without extension
   * @param {string} folderId
   * @returns {Promise<boolean>}
   */
  async transcriptionExists(baseFilename, folderId) {
    await this.ensureAuth();
    const escaped = baseFilename.replace(/'/g, "\\'");
    const res = await this.drive.files.list({
      q: `name contains '${escaped}' and '${folderId}' in parents and trashed=false`,
      fields: 'files(id,name)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
      pageSize: 20
    });
    const files = res.data.files || [];
    const suffixes = ['_complete_data.json', '_paragraphs_timestamps'];
    for (const f of files) {
      const nameNorm = f.name.toLowerCase().trim();
      const baseNorm = baseFilename.toLowerCase().trim();
      if (nameNorm.startsWith(baseNorm) && suffixes.some(s => nameNorm.includes(s))) {
        return true;
      }
    }
    return false;
  }

  /**
   * Download a file from Drive to a local path, with progress callback.
   * @param {string} fileId
   * @param {string} localPath
   * @param {function} [onProgress] - Called with (bytesDownloaded, totalBytes)
   */
  async downloadFile(fileId, localPath, onProgress = null) {
    await this.ensureAuth();

    // Get mime type first
    const meta = await this.drive.files.get({
      fileId,
      fields: 'mimeType,size',
      supportsAllDrives: true
    });
    const mimeType = meta.data.mimeType || '';
    const totalBytes = parseInt(meta.data.size || '0', 10);

    // Ensure directory exists
    fs.mkdirSync(path.dirname(localPath), { recursive: true });

    let request;
    if (mimeType.includes('application/vnd.google-apps')) {
      request = this.drive.files.export(
        { fileId, mimeType: 'text/plain' },
        { responseType: 'stream' }
      );
    } else {
      request = this.drive.files.get(
        { fileId, alt: 'media', supportsAllDrives: true },
        { responseType: 'stream' }
      );
    }

    const res = await request;
    return new Promise((resolve, reject) => {
      const dest = fs.createWriteStream(localPath);
      let downloaded = 0;

      res.data.on('data', (chunk) => {
        downloaded += chunk.length;
        if (onProgress && totalBytes > 0) {
          onProgress(downloaded, totalBytes);
        }
      });

      res.data.on('error', reject);
      res.data.pipe(dest);
      dest.on('finish', () => resolve(localPath));
      dest.on('error', reject);
    });
  }

  /**
   * Upload a local file to Drive (resumable, 50MB chunks).
   * @param {string} localPath
   * @param {string} driveName - Name in Drive
   * @param {string} folderId
   * @param {function} [onProgress] - Called with percent (0-100)
   * @returns {Promise<string>} File ID
   */
  async uploadFile(localPath, driveName, folderId, onProgress = null) {
    await this.ensureAuth();

    const fileSize = fs.statSync(localPath).size;
    const mimeType = this._mimeType(driveName);

    const res = await this.drive.files.create(
      {
        requestBody: { name: driveName, parents: [folderId] },
        media: { mimeType, body: fs.createReadStream(localPath) },
        fields: 'id',
        supportsAllDrives: true
      },
      {
        onUploadProgress: (evt) => {
          if (onProgress && fileSize > 0) {
            onProgress(Math.round((evt.bytesRead / fileSize) * 100));
          }
        }
      }
    );
    return res.data.id;
  }

  /**
   * Create a Google Doc with text content.
   * @param {string} name - Document name
   * @param {string} content - Plain text content
   * @param {string} folderId
   * @returns {Promise<string>} Document ID
   */
  async createGoogleDoc(name, content, folderId) {
    await this.ensureAuth();

    // Create empty doc in Drive
    const file = await this.drive.files.create({
      requestBody: {
        name,
        mimeType: 'application/vnd.google-apps.document',
        parents: [folderId]
      },
      fields: 'id',
      supportsAllDrives: true
    });
    const docId = file.data.id;

    // Insert content via Docs API
    await this.docs.documents.batchUpdate({
      documentId: docId,
      requestBody: {
        requests: [{
          insertText: {
            location: { index: 1 },
            text: content
          }
        }]
      }
    });

    return docId;
  }

  /**
   * Export a Google Doc as plain text.
   * @param {string} fileId
   * @returns {Promise<string>}
   */
  async exportDocAsText(fileId) {
    await this.ensureAuth();
    const res = await this.drive.files.export({
      fileId,
      mimeType: 'text/plain'
    }, { responseType: 'arraybuffer' });
    return Buffer.from(res.data).toString('utf-8');
  }

  /**
   * List files matching a pattern in a folder.
   * @param {string} folderId
   * @param {string} pattern - Substring to match in name
   * @returns {Promise<Array>}
   */
  async listFilesWithPattern(folderId, pattern) {
    await this.ensureAuth();
    const escaped = pattern.replace(/'/g, "\\'");
    const res = await this.drive.files.list({
      q: `'${folderId}' in parents and name contains '${escaped}' and trashed=false`,
      fields: 'files(id,name,mimeType,modifiedTime)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
      pageSize: 1000
    });
    return res.data.files || [];
  }

  /**
   * Find or create a subfolder.
   * @param {string} parentId
   * @param {string} folderName
   * @returns {Promise<string>} Folder ID
   */
  async findOrCreateFolder(parentId, folderName) {
    await this.ensureAuth();
    const escaped = folderName.replace(/'/g, "\\'");
    const res = await this.drive.files.list({
      q: `'${parentId}' in parents and name='${escaped}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
      fields: 'files(id)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true
    });
    const folders = res.data.files || [];
    if (folders.length > 0) return folders[0].id;

    const folder = await this.drive.files.create({
      requestBody: {
        name: folderName,
        mimeType: 'application/vnd.google-apps.folder',
        parents: [parentId]
      },
      fields: 'id',
      supportsAllDrives: true
    });
    return folder.data.id;
  }

  /**
   * Create a lock file in _processing/ folder.
   * @param {string} processingFolderId
   * @param {string} lockName - e.g. "filename.wav.lock"
   * @param {string} machineId
   * @returns {Promise<string>} Lock file ID
   */
  async createLockFile(processingFolderId, lockName, machineId) {
    await this.ensureAuth();
    const content = JSON.stringify({
      machine_id: machineId,
      started_at: new Date().toISOString()
    });
    const buf = Buffer.from(content, 'utf-8');
    const { Readable } = require('stream');

    const res = await this.drive.files.create({
      requestBody: { name: lockName, parents: [processingFolderId] },
      media: { mimeType: 'application/json', body: Readable.from(buf) },
      fields: 'id',
      supportsAllDrives: true
    });
    return res.data.id;
  }

  /**
   * Delete a file by ID.
   */
  async deleteFile(fileId) {
    await this.ensureAuth();
    try {
      await this.drive.files.delete({ fileId, supportsAllDrives: true });
    } catch {
      // Ignore deletion errors
    }
  }

  /**
   * Check if a lock file exists and is fresh (< 2h old).
   * @returns {Promise<boolean>} true = someone else is processing
   */
  async checkLockFile(processingFolderId, lockName) {
    await this.ensureAuth();
    const escaped = lockName.replace(/'/g, "\\'");
    const res = await this.drive.files.list({
      q: `'${processingFolderId}' in parents and name='${escaped}' and trashed=false`,
      fields: 'files(id,modifiedTime)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true
    });
    const files = res.data.files || [];
    if (files.length === 0) return { locked: false, fileId: null };

    const f = files[0];
    const modTime = new Date(f.modifiedTime);
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);

    if (modTime > twoHoursAgo) {
      return { locked: true, fileId: f.id };
    }
    // Stale lock — return it so caller can replace
    return { locked: false, fileId: f.id, stale: true };
  }

  /**
   * List Google Docs in transcriptions folder that are ready for highlights
   * (contain 🎬 READY 🎬 in their text).
   * @param {string} folderId
   * @returns {Promise<Array>} Array of {id, name, text}
   */
  async listDocsReadyForHighlights(folderId) {
    await this.ensureAuth();
    // Only check docs modified in the last 7 days to avoid scanning the entire folder
    const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
    const res = await this.drive.files.list({
      q: `'${folderId}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false and modifiedTime > '${since}'`,
      fields: 'files(id,name,modifiedTime)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
      pageSize: 100
    });
    const docs = res.data.files || [];

    const ready = [];
    for (const doc of docs) {
      if (!doc.name.includes('_paragraphs_timestamps')) continue;
      const text = await this.exportDocAsText(doc.id);
      if (text.includes('🎬 READY 🎬') || text.includes('🎬READY🎬')) {
        ready.push({ ...doc, text });
      }
    }
    return ready;
  }

  /**
   * Mark a doc as processed by replacing 🎬 READY 🎬 with 🎬 PROCESSED 🎬.
   * @param {string} docId
   */
  async markDocAsProcessed(docId) {
    await this.ensureAuth();
    await this.docs.documents.batchUpdate({
      documentId: docId,
      requestBody: {
        requests: [
          {
            replaceAllText: {
              containsText: { text: '🎬 READY 🎬', matchCase: true },
              replaceText: '🎬 PROCESSED 🎬'
            }
          },
          {
            replaceAllText: {
              containsText: { text: '🎬READY🎬', matchCase: true },
              replaceText: '🎬 PROCESSED 🎬'
            }
          }
        ]
      }
    });
  }

  _mimeType(filename) {
    const ext = path.extname(filename).toLowerCase();
    const map = {
      '.json': 'application/json',
      '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.mp4': 'video/mp4',
      '.mp3': 'audio/mpeg',
      '.wav': 'audio/wav',
      '.txt': 'text/plain'
    };
    return map[ext] || 'application/octet-stream';
  }
}

module.exports = DriveService;
