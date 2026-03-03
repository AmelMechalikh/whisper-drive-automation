'use strict';

/**
 * Output generator - port of output_generator.py
 * Generates paragraphs_timestamps Google Doc + complete_data.json
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SILENCE_THRESHOLD = 2.0; // seconds between segments = new paragraph

/**
 * Convert seconds to M:SS format (e.g. 65.5 → "1:05")
 */
function secondsToSimpleTimestamp(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Group Whisper segments into paragraphs based on silence gaps.
 * @param {Array} segments
 * @returns {Array} paragraphs, each with .start and .segments[]
 */
function groupSegmentsIntoParagraphs(segments) {
  if (!segments || segments.length === 0) return [];

  const paragraphs = [];
  let currentParagraph = {
    start: segments[0].start,
    segments: [segments[0]]
  };

  for (let i = 1; i < segments.length; i++) {
    const prev = segments[i - 1];
    const curr = segments[i];
    const gap = curr.start - prev.end;

    if (gap >= SILENCE_THRESHOLD) {
      paragraphs.push(currentParagraph);
      currentParagraph = { start: curr.start, segments: [curr] };
    } else {
      currentParagraph.segments.push(curr);
    }
  }
  paragraphs.push(currentParagraph);
  return paragraphs;
}

/**
 * Build the paragraphs_timestamps text content.
 * Format: (M:SS) text (M:SS) continuation...
 *         (empty line between paragraphs)
 */
function buildParagraphsText(paragraphs) {
  const lines = [];
  for (const para of paragraphs) {
    const parts = (para.segments || []).map(seg => {
      const ts = secondsToSimpleTimestamp(seg.start);
      return `(${ts}) ${seg.text.trim()}`;
    });
    lines.push(parts.join(' '));
  }
  return lines.join('\n\n');
}

/**
 * Inject word timestamps into segments.
 * RunPod returns word_timestamps as a flat list at the top level,
 * separate from segments. Port of _inject_words_into_segments() in transcription_backends.py.
 */
function injectWordsIntoSegments(segments, wordTimestamps) {
  if (!segments.length || !wordTimestamps || !wordTimestamps.length) return segments;

  const result = [];
  let wordIdx = 0;

  for (const segment of segments) {
    const segEnd = segment.end || 0;
    const segWords = [];

    while (wordIdx < wordTimestamps.length) {
      const word = wordTimestamps[wordIdx];
      if ((word.start || 0) < segEnd) {
        segWords.push({
          start: word.start,
          end: word.end,
          word: word.word || '',
          score: 1.0
        });
        wordIdx++;
      } else {
        break;
      }
    }

    const segCopy = { ...segment };
    if (segWords.length) segCopy.words = segWords;
    result.push(segCopy);
  }

  return result;
}

/**
 * Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
 */
function secondsToSrtTime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.round((seconds % 1) * 1000);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

/**
 * Build SRT file content from segments.
 */
function buildSrtContent(segments) {
  const lines = [];
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    lines.push(String(i + 1));
    lines.push(`${secondsToSrtTime(seg.start)} --> ${secondsToSrtTime(seg.end)}`);
    lines.push(seg.text.trim());
    lines.push('');
  }
  return lines.join('\n');
}

/**
 * Build the complete_data JSON structure.
 */
function buildCompleteData(baseFilename, whisperResult, paragraphs) {
  let segments = whisperResult.segments || [];

  // RunPod returns word timestamps as a separate flat list — inject into segments
  if (whisperResult.word_timestamps && whisperResult.word_timestamps.length) {
    segments = injectWordsIntoSegments(segments, whisperResult.word_timestamps);
  }
  const fullText = whisperResult.text ||
    segments.map(s => s.text.trim()).join(' ');
  const duration = segments.length > 0
    ? Math.max(...segments.map(s => s.end))
    : 0;

  const data = {
    metadata: {
      filename: baseFilename,
      language: whisperResult.language || 'unknown',
      duration,
      total_segments: segments.length
    },
    full_text: fullText,
    segments
  };

  if (paragraphs) {
    data.paragraphs = paragraphs;
    data.metadata.total_paragraphs = paragraphs.length;
  }
  return data;
}

/**
 * Generate all outputs for a transcription.
 *
 * @param {string} baseFilename - Filename without extension
 * @param {object} whisperResult - RunPod output
 * @param {object} driveService - DriveService instance (optional)
 * @param {string} outputFolderId - Drive folder ID for outputs
 * @param {function} [onLog] - Log callback
 * @returns {Promise<{paragraphsDocId: string|null, jsonFileId: string|null, jsonLocalPath: string, completeData: object}>}
 */
async function generateAllOutputs(baseFilename, whisperResult, driveService = null, outputFolderId = null, onLog = null) {
  const log = onLog || console.log;
  const tmpDir = path.join(os.tmpdir(), 'transcription-app', 'outputs');
  fs.mkdirSync(tmpDir, { recursive: true });

  // 1. Group into paragraphs
  const paragraphs = groupSegmentsIntoParagraphs(whisperResult.segments || []);
  log(`📝 ${paragraphs.length} paragraphe(s) générés`);

  // 2. Build complete data
  const completeData = buildCompleteData(baseFilename, whisperResult, paragraphs);

  // 3. Save JSON locally
  const jsonFilename = `${baseFilename}_complete_data.json`;
  const jsonLocalPath = path.join(tmpDir, jsonFilename);
  fs.writeFileSync(jsonLocalPath, JSON.stringify(completeData, null, 2), 'utf-8');
  log(`💾 JSON local: ${jsonLocalPath}`);

  // 4. Save SRT locally
  const srtFilename = `${baseFilename}_with_timestamps.srt`;
  const srtLocalPath = path.join(tmpDir, srtFilename);
  fs.writeFileSync(srtLocalPath, buildSrtContent(completeData.segments || []), 'utf-8');
  log(`⏰ SRT local: ${srtLocalPath}`);

  let paragraphsDocId = null;
  let jsonFileId = null;
  let srtFileId = null;

  if (driveService && outputFolderId) {
    // 5. Create Google Doc with paragraphs_timestamps
    const paragraphsText = buildParagraphsText(paragraphs);
    const docName = `${baseFilename}_paragraphs_timestamps`;
    try {
      paragraphsDocId = await driveService.createGoogleDoc(docName, paragraphsText, outputFolderId);
      log(`📝 Google Doc créé: ${docName} (${paragraphsDocId})`);
    } catch (err) {
      log(`⚠️ Erreur création Google Doc: ${err.message}`);
    }

    // 6. Upload JSON to Drive
    try {
      jsonFileId = await driveService.uploadFile(jsonLocalPath, jsonFilename, outputFolderId);
      log(`☁️  JSON uploadé sur Drive: ${jsonFilename} (${jsonFileId})`);
    } catch (err) {
      log(`⚠️ Erreur upload JSON: ${err.message}`);
    }

    // 7. Upload SRT to Drive
    try {
      srtFileId = await driveService.uploadFile(srtLocalPath, srtFilename, outputFolderId);
      log(`☁️  SRT uploadé sur Drive: ${srtFilename} (${srtFileId})`);
    } catch (err) {
      log(`⚠️ Erreur upload SRT: ${err.message}`);
    }
  }

  return { paragraphsDocId, jsonFileId, srtFileId, jsonLocalPath, srtLocalPath, completeData };
}

module.exports = {
  generateAllOutputs,
  groupSegmentsIntoParagraphs,
  buildParagraphsText,
  buildCompleteData,
  buildSrtContent,
  secondsToSimpleTimestamp,
  secondsToSrtTime
};
