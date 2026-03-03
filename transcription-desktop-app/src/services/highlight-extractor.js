'use strict';

/**
 * Highlight extractor - port of highlight_extractor.py
 * Extracts highlights from Google Docs comments, matches timestamps,
 * generates Excel output.
 */

const { normalizeFrenchWord } = require('../utils/french-normalizer');

// ─── Helpers ─────────────────────────────────────────────────────────────────

function secondsToTimecode(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/**
 * Remove formatting markers from highlight text.
 */
function cleanHighlightText(text) {
  let t = text;
  t = t.replace(/===\s*Paragraphe\s+\d+\s*===/g, '');
  t = t.replace(/Temps:\s*\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}/g, '');
  t = t.replace(/Mots:\s*\d+/g, '');
  t = t.replace(/Texte:\s*/g, '');
  t = t.replace(/\(\d+:\d+\)/g, '');
  t = t.replace(/\s+/g, ' ').trim();
  return t;
}

/**
 * Flatten all segments into a list of normalized words with timestamps.
 * Merges words starting with apostrophe or hyphen into the previous word
 * (Whisper tokenizes "c'est" → ["c", "'est"]).
 */
function flattenWordsFromSegments(segments) {
  const allWords = [];
  let globalIndex = 0;

  for (const segment of segments) {
    if (!segment.words) continue;
    for (const wordInfo of segment.words) {
      const wordText = (wordInfo.word || '').trim();

      const shouldMerge =
        allWords.length > 0 &&
        (wordText.startsWith("'") || wordText.startsWith('\u2019') || wordText.startsWith('-'));

      if (shouldMerge) {
        const prev = allWords[allWords.length - 1];
        const cleanText = normalizeFrenchWord(wordText);
        prev.word = prev.word + cleanText;
        prev.end = wordInfo.end !== undefined ? wordInfo.end : prev.end;
      } else {
        const cleanText = normalizeFrenchWord(wordText);
        if (cleanText) {
          allWords.push({
            word: cleanText,
            start: wordInfo.start || 0,
            end: wordInfo.end || 0,
            index: globalIndex++
          });
        }
      }
    }
  }
  return allWords;
}

/**
 * Find all positions in allWords where searchWords sequence matches with score >= minScore.
 */
function findWordSequenceCandidates(allWords, searchWords, minScore = 0.7) {
  if (!searchWords.length) return [];
  const searchNorm = searchWords
    .map(w => normalizeFrenchWord(w))
    .filter(w => w.length > 0);
  if (!searchNorm.length) return [];

  const firstWord = searchNorm[0];
  const candidates = [];

  for (let i = 0; i < allWords.length; i++) {
    const wordNorm = allWords[i].word;
    if (firstWord === wordNorm || firstWord.includes(wordNorm) || wordNorm.includes(firstWord)) {
      let matchedCount = 1;
      for (let j = 1; j < Math.min(searchNorm.length, allWords.length - i); j++) {
        const nextNorm = allWords[i + j].word;
        const searchWordNorm = searchNorm[j];
        if (searchWordNorm === nextNorm || searchWordNorm.includes(nextNorm) || nextNorm.includes(searchWordNorm)) {
          matchedCount++;
        } else {
          break;
        }
      }
      const score = matchedCount / searchNorm.length;
      if (score >= minScore) {
        candidates.push({
          index: i,
          start: allWords[i].start,
          end: allWords[Math.min(i + matchedCount - 1, allWords.length - 1)].end,
          score,
          matched: matchedCount
        });
      }
    }
  }
  return candidates;
}

/**
 * Use context to pick the best candidate when multiple have the same score.
 */
function disambiguateWithContext(startCandidates, segments, contextBefore, contextAfter) {
  if (!contextBefore && !contextAfter) return null;

  let bestCandidate = null;
  let bestScore = -1;

  for (const candidate of startCandidates) {
    const segIdx = candidate._segIdx || 0;
    const before = segments.slice(Math.max(0, segIdx - 5), segIdx).map(s => s.text || '').join(' ');
    const after = segments.slice(segIdx + 1, segIdx + 6).map(s => s.text || '').join(' ');

    const normSimple = t => t.replace(/[,.!?;:]/g, ' ').replace(/\s+/g, ' ').toLowerCase().trim();

    const beforeNorm = normSimple(before);
    const afterNorm = normSimple(after);
    const docBeforeNorm = normSimple(contextBefore || '');
    const docAfterNorm = normSimple(contextAfter || '');

    let score = 0;
    if (docBeforeNorm) {
      const words = docBeforeNorm.split(' ').slice(-20);
      score += words.filter(w => beforeNorm.includes(w)).length;
    }
    if (docAfterNorm) {
      const words = docAfterNorm.split(' ').slice(0, 20);
      score += words.filter(w => afterNorm.includes(w)).length;
    }

    if (score > bestScore) {
      bestScore = score;
      bestCandidate = candidate;
    }
  }

  if (bestCandidate && bestScore > 5) return bestCandidate;
  return null;
}

/**
 * Find exact timestamps for a highlight text within complete transcription data.
 * @param {string} highlightText
 * @param {object} completeData - {segments: [...]}
 * @param {string} [contextBefore]
 * @param {string} [contextAfter]
 * @returns {{start: number|null, end: number|null}}
 */
function findExactTimestamps(highlightText, completeData, contextBefore = '', contextAfter = '') {
  const cleanText = cleanHighlightText(highlightText);
  const words = cleanText.split(/\s+/).filter(w => w.length > 0);

  if (words.length < 2) return { start: null, end: null };

  const segments = completeData.segments || [];
  const allWords = flattenWordsFromSegments(segments);

  if (!allWords.length) return { start: null, end: null };

  // STEP 1: Find start candidates using first 6-8 words
  const numWordsStart = Math.min(8, words.length);
  const startSearchWords = words.slice(0, numWordsStart);
  const startSearchNorm = startSearchWords.map(w => normalizeFrenchWord(w));
  console.log(`[match-debug] Recherche: "${startSearchNorm.join(' ')}" dans ${allWords.length} mots`);
  console.log(`[match-debug] Premiers mots transcrits: "${allWords.slice(0, 5).map(w => w.word).join(' ')}"`);
  let startCandidates = findWordSequenceCandidates(allWords, startSearchWords, 0.7);
  console.log(`[match-debug] Candidats trouvés: ${startCandidates.length}`);

  if (!startCandidates.length) return { start: null, end: null };

  // Annotate candidates with segment index
  for (const c of startCandidates) {
    for (let i = 0; i < segments.length; i++) {
      if (segments[i].start <= c.start && c.start <= (segments[i].end || segments[i].start + 10)) {
        c._segIdx = i;
        break;
      }
    }
  }

  // Pick best start
  let bestStart = startCandidates.reduce((a, b) => a.score >= b.score ? a : b);

  // Disambiguate if multiple candidates share top score
  if (startCandidates.length > 1 && (contextBefore || contextAfter)) {
    const topScore = bestStart.score;
    const topCandidates = startCandidates.filter(c => c.score === topScore);
    if (topCandidates.length > 1) {
      const disambiguated = disambiguateWithContext(topCandidates, segments, contextBefore, contextAfter);
      if (disambiguated) bestStart = disambiguated;
    }
  }

  const startTime = bestStart.start;
  const startIndex = bestStart.index;

  // STEP 2: Find end candidates using last 6 words, only after start
  const numWordsEnd = Math.min(6, words.length);
  const endSearchWords = words.slice(-numWordsEnd);
  const wordsAfterStart = allWords.slice(startIndex);
  const endCandidates = findWordSequenceCandidates(wordsAfterStart, endSearchWords, 0.7);

  if (!endCandidates.length) return { start: null, end: null };

  let endTime;
  if (endCandidates.length === 1) {
    endTime = endCandidates[0].end;
  } else {
    // Pick candidate whose coverage ratio is closest to 1.0
    let bestCand = null;
    let bestDist = Infinity;

    const cleanTextLen = cleanText.length;

    for (const cand of endCandidates) {
      const endIdxAbs = startIndex + cand.index + cand.matched;
      const wordsInRange = allWords.slice(startIndex, endIdxAbs);
      const transcriptLen = wordsInRange.map(w => w.word).join(' ').length;
      const ratio = cleanTextLen > 0 ? transcriptLen / cleanTextLen : 0;

      if (ratio >= 0.7 && ratio <= 1.5) {
        const dist = Math.abs(ratio - 1.0);
        if (dist < bestDist) {
          bestDist = dist;
          bestCand = cand;
        }
      }
    }

    endTime = (bestCand || endCandidates[0]).end;
  }

  // Add safety margin
  return { start: startTime, end: endTime + 0.4 };
}

/**
 * Extract context (text before/after a highlight) from a full document text.
 */
function extractContext(fullText, highlightText, contextWords = 50) {
  const clean = cleanHighlightText(highlightText);
  const searchWords = clean.split(/\s+/).slice(0, 20).join(' ');

  let pos = fullText.indexOf(searchWords);
  if (pos === -1) return { before: '', after: '' };

  const textBefore = fullText.slice(0, pos);
  const textAfter = fullText.slice(pos + searchWords.length);

  const wordsBefore = textBefore.split(/\s+/);
  const wordsAfter = textAfter.split(/\s+/);

  const before = wordsBefore.slice(-contextWords).join(' ');
  const after = wordsAfter.slice(0, contextWords).join(' ');

  return { before: before.trim(), after: after.trim() };
}

/**
 * Main extraction function: given Drive comments + complete data, produce highlight rows.
 * @param {Array} comments - Array from driveService.getFileComments()
 * @param {object} completeData - Parsed _complete_data.json
 * @param {string} [fullDocText] - Full document text for context (optional)
 * @returns {Array} highlight rows for Excel
 */
/**
 * Extract inline marker segments from doc text.
 * Format: 🎬 S1 🎬 text to extract 🎬 /S1 🎬
 * @param {string} docText
 * @returns {Array} Array of {id, text}
 */
function extractInlineMarkerSegments(docText) {
  // Debug: show context around 🎬
  const idx = docText.indexOf('🎬');
  if (idx >= 0) {
    console.log(`[marker-debug] Premier 🎬 trouvé à pos ${idx}: "${docText.substring(idx, idx + 50)}"`);
  } else {
    console.log('[marker-debug] Aucun 🎬 dans le texte exporté!');
  }

  const MARKER_START = /🎬\s*([A-Za-z]\d+)\s*🎬/g;
  const MARKER_END = /🎬\s*\/([A-Za-z]\d+)\s*🎬/g;

  const startMarkers = [];
  const endMarkers = [];
  let m;

  while ((m = MARKER_START.exec(docText)) !== null) {
    startMarkers.push({ id: m[1], endPos: m.index + m[0].length });
  }
  while ((m = MARKER_END.exec(docText)) !== null) {
    endMarkers.push({ id: m[1], startPos: m.index });
  }

  const segments = [];
  for (const start of startMarkers) {
    const end = endMarkers.find(e => e.id === start.id && e.startPos > start.endPos);
    if (end) {
      const raw = docText.substring(start.endPos, end.startPos);
      const clean = cleanHighlightText(raw);
      if (clean) segments.push({ id: start.id, text: clean });
    }
  }
  return segments;
}

/**
 * Extract highlights from inline markers (🎬 S1 🎬 ... 🎬 /S1 🎬) in doc text.
 * @param {string} docText - Full document text
 * @param {object} completeData - Complete transcription data with word timestamps
 * @returns {Array} Array of highlight row objects
 */
function extractHighlights(docText, completeData) {
  const segments = extractInlineMarkerSegments(docText);
  if (!segments.length) return [];

  const highlightData = [];
  let segmentNum = 1;

  for (const seg of segments) {
    const ctx = extractContext(docText, seg.text);
    const result = findExactTimestamps(seg.text, completeData, ctx.before, ctx.after);

    if (result.start === null || result.end === null) {
      console.warn(`⚠️ Timestamps introuvables pour segment ${seg.id}: "${seg.text.substring(0, 50)}..."`);
      continue;
    }

    highlightData.push({
      'Numéro': segmentNum,
      'Groupe': seg.id,
      'Sous-segment': null,
      'Total': null,
      'Début (secondes)': parseFloat(result.start.toFixed(2)),
      'Fin (secondes)': parseFloat(result.end.toFixed(2)),
      'Début (HH:MM:SS)': secondsToTimecode(result.start),
      'Fin (HH:MM:SS)': secondsToTimecode(result.end),
      'Durée (secondes)': parseFloat((result.end - result.start).toFixed(2)),
      'À fusionner': 'Non',
      'Texte': seg.text
    });

    segmentNum++;
  }

  return highlightData;
}

/**
 * Write highlight data to an Excel file using exceljs.
 * @param {Array} rows - Array of highlight row objects
 * @param {string} outputPath - Local path for .xlsx file
 */
async function writeExcel(rows, outputPath) {
  const ExcelJS = require('exceljs');
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet('Highlights');

  if (!rows.length) {
    sheet.addRow(['Aucun highlight trouvé']);
    await workbook.xlsx.writeFile(outputPath);
    return;
  }

  // Set header
  sheet.columns = Object.keys(rows[0]).map(key => ({
    header: key,
    key,
    width: key === 'Texte' ? 60 : key.includes('HH') ? 14 : 16
  }));

  // Style header
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'FF4472C4' }
  };
  headerRow.font = { bold: true, color: { argb: 'FFFFFFFF' } };

  for (const row of rows) {
    sheet.addRow(row);
  }

  await workbook.xlsx.writeFile(outputPath);
}

module.exports = {
  extractHighlights,
  findExactTimestamps,
  writeExcel,
  cleanHighlightText,
  flattenWordsFromSegments,
  secondsToTimecode
};
