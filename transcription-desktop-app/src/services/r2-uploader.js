'use strict';

/**
 * Cloudflare R2 uploader (S3-compatible).
 * Replaces GCS bucket for temporary audio storage.
 *
 * Requires @aws-sdk/client-s3
 */

const { S3Client, PutObjectCommand, DeleteObjectCommand } = require('@aws-sdk/client-s3');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class R2Uploader {
  /**
   * @param {object} config
   * @param {string} config.accountId      - Cloudflare account ID
   * @param {string} config.accessKeyId    - R2 access key
   * @param {string} config.secretAccessKey - R2 secret key
   * @param {string} config.bucket         - R2 bucket name
   * @param {string} config.publicDomain   - Public domain, e.g. "pub-xxx.r2.dev"
   */
  constructor(config) {
    this.bucket = config.bucket;
    this.publicDomain = config.publicDomain;

    this.client = new S3Client({
      region: 'auto',
      endpoint: `https://${config.accountId}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: config.accessKeyId,
        secretAccessKey: config.secretAccessKey
      }
    });
  }

  /**
   * Upload a file to R2 and return its public URL.
   * @param {string} localPath - Local file path
   * @param {string} [customKey] - Optional custom key; defaults to temp-audio/{uuid}/{filename}
   * @returns {Promise<{url: string, key: string}>}
   */
  async uploadFile(localPath, customKey = null) {
    const filename = path.basename(localPath);
    const uuid = crypto.randomUUID();
    const key = customKey || `temp-audio/${uuid}/${filename}`;

    const fileStream = fs.createReadStream(localPath);
    const fileSize = fs.statSync(localPath).size;

    const mimeType = filename.endsWith('.wav')
      ? 'audio/wav'
      : filename.endsWith('.mp3')
        ? 'audio/mpeg'
        : 'application/octet-stream';

    await this.client.send(new PutObjectCommand({
      Bucket: this.bucket,
      Key: key,
      Body: fileStream,
      ContentLength: fileSize,
      ContentType: mimeType
    }));

    const url = `https://${this.publicDomain}/${key}`;
    return { url, key };
  }

  /**
   * Delete an object from R2.
   */
  async deleteFile(key) {
    try {
      await this.client.send(new DeleteObjectCommand({
        Bucket: this.bucket,
        Key: key
      }));
    } catch {
      // Non-critical cleanup failure — ignore
    }
  }

  /**
   * Upload a small test file to verify credentials.
   * @returns {Promise<string>} Public URL of test file
   */
  async testConnection() {
    const testKey = `test/${Date.now()}.txt`;
    const testContent = Buffer.from('R2 connection test');

    await this.client.send(new PutObjectCommand({
      Bucket: this.bucket,
      Key: testKey,
      Body: testContent,
      ContentLength: testContent.length,
      ContentType: 'text/plain'
    }));

    const url = `https://${this.publicDomain}/${testKey}`;

    // Clean up test file
    await this.deleteFile(testKey);

    return url;
  }
}

module.exports = R2Uploader;
