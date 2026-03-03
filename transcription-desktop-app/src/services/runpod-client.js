'use strict';

/**
 * RunPod Serverless API client for Whisper transcription.
 * Port of runpod_client.py
 */

const https = require('https');
const http = require('http');

class RunPodClient {
  constructor(apiKey, endpoint) {
    this.apiKey = apiKey;
    this.endpoint = endpoint.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  /**
   * Submit audio URL to RunPod and poll until result.
   * @param {string} audioUrl - Public URL to audio file
   * @param {string} model - Whisper model (default: turbo)
   * @param {string} language - Language code (default: fr)
   * @returns {Promise<object>} Transcription result
   */
  async transcribeAudio(audioUrl, model = 'turbo', language = 'fr') {
    const payload = {
      input: {
        audio: audioUrl,
        model,
        language,
        word_timestamps: true,
        condition_on_previous_text: false,
        no_speech_threshold: 0.8,
        compression_ratio_threshold: 3.0
      }
    };

    const result = await this._request('POST', `${this.endpoint}/run`, payload);
    const jobId = result.id;

    if (!jobId) {
      throw new Error(`RunPod did not return job ID. Response: ${JSON.stringify(result)}`);
    }

    return this._pollJobStatus(jobId);
  }

  /**
   * Poll job status until COMPLETED or FAILED.
   * @param {string} jobId
   * @param {number} timeout - Max wait in seconds (default 1800)
   * @param {number} pollInterval - Poll interval in seconds (default 5)
   */
  async _pollJobStatus(jobId, timeout = 1800, pollInterval = 5) {
    const start = Date.now();
    let consecutiveErrors = 0;
    const maxRetries = 3;

    while ((Date.now() - start) / 1000 < timeout) {
      let data;
      try {
        data = await this._request('GET', `${this.endpoint}/status/${jobId}`);
        consecutiveErrors = 0;
      } catch (err) {
        consecutiveErrors++;
        if (consecutiveErrors >= maxRetries) {
          throw new Error(`Failed to check job status after ${maxRetries} retries: ${err.message}`);
        }
        await this._sleep(pollInterval * 1000);
        continue;
      }

      const status = data.status;

      if (status === 'COMPLETED') {
        if (!data.output) {
          throw new Error(`Job completed but no output returned. Response: ${JSON.stringify(data)}`);
        }
        return data.output;
      } else if (status === 'FAILED') {
        throw new Error(`RunPod job failed: ${data.error || 'Unknown error'}`);
      }
      // IN_QUEUE or IN_PROGRESS → keep polling

      await this._sleep(pollInterval * 1000);
    }

    throw new Error(`RunPod job ${jobId} timed out after ${timeout}s`);
  }

  /**
   * Cancel a running job.
   */
  async cancelJob(jobId) {
    try {
      await this._request('POST', `${this.endpoint}/cancel/${jobId}`);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Generic HTTP request helper (no external dependencies).
   */
  _request(method, url, body = null) {
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(url);
      const transport = parsedUrl.protocol === 'https:' ? https : http;

      const bodyStr = body ? JSON.stringify(body) : null;
      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method,
        headers: {
          ...this.headers,
          ...(bodyStr ? { 'Content-Length': Buffer.byteLength(bodyStr) } : {})
        },
        timeout: 30000
      };

      const req = transport.request(options, (res) => {
        let raw = '';
        res.on('data', (chunk) => { raw += chunk; });
        res.on('end', () => {
          if (res.statusCode >= 400) {
            return reject(new Error(`HTTP ${res.statusCode}: ${raw}`));
          }
          try {
            resolve(JSON.parse(raw));
          } catch {
            resolve(raw);
          }
        });
      });

      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });

      if (bodyStr) req.write(bodyStr);
      req.end();
    });
  }

  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = RunPodClient;
