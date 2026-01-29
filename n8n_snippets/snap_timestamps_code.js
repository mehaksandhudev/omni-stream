// ============================================
// TIMESTAMP SNAPPING - Corrects AI's approximate timestamps
// to precise word boundaries from the transcript
// ============================================
// IMPORTANT: This handles Python-formatted data with np.float64() etc.

// Get the clips from the input
const inputData = $input.all();
let aiClips = [];

for (const item of inputData) {
    if (item.json.output) {
        try {
            const parsed = typeof item.json.output === 'string'
                ? JSON.parse(item.json.output)
                : item.json.output;
            if (Array.isArray(parsed)) {
                aiClips = aiClips.concat(parsed);
            } else {
                aiClips.push(parsed);
            }
        } catch (e) {
            console.log('Could not parse output:', e.message);
        }
    } else if (item.json.clips) {
        aiClips = aiClips.concat(item.json.clips);
    } else if (item.json.timeStart) {
        aiClips.push(item.json);
    }
}

console.log('Found clips:', aiClips.length);

// Get the word timestamps from the "Get Word Timestamps" node
let wordTimestampsRaw;
try {
    wordTimestampsRaw = $('Get Word Timestamps').first().json.data;
} catch (e) {
    console.log('Could not access Get Word Timestamps node:', e.message);
    return aiClips.map(clip => ({ json: { ...clip, error: 'Cannot find Get Word Timestamps node' } }));
}

if (!wordTimestampsRaw) {
    return aiClips.map(clip => ({ json: { ...clip, error: 'No word timestamps data found' } }));
}

// Parse the word timestamps - they come as a Python-like string
let allWords = [];

try {
    let dataStr = String(wordTimestampsRaw);

    // More aggressive cleaning for Python format
    // Step 1: Remove all np.float64(), np.int64(), etc. wrappers
    dataStr = dataStr.replace(/np\.\w+\(([^)]*)\)/g, '$1');

    // Step 2: Replace Python True/False/None
    dataStr = dataStr.replace(/\bTrue\b/g, 'true');
    dataStr = dataStr.replace(/\bFalse\b/g, 'false');
    dataStr = dataStr.replace(/\bNone\b/g, 'null');

    // Step 3: Replace single quotes with double quotes
    // But be careful with apostrophes inside words
    // First, temporarily replace escaped single quotes
    dataStr = dataStr.replace(/\\'/g, '___ESCAPED_QUOTE___');

    // Now handle the tricky part: single quotes as string delimiters
    // Python uses ' for strings, JSON needs "
    // We need to be careful: "I'd love" has an apostrophe

    // Simple approach: replace ' with " when it's a string delimiter
    // A string delimiter is typically after : or , or [ or at start
    let result = '';
    let i = 0;
    let inString = false;
    let stringChar = null;

    while (i < dataStr.length) {
        const char = dataStr[i];
        const prevChar = i > 0 ? dataStr[i - 1] : '';

        if (!inString && (char === "'" || char === '"')) {
            inString = true;
            stringChar = char;
            result += '"';
        } else if (inString && char === stringChar) {
            // Check if it's escaped
            if (prevChar !== '\\') {
                inString = false;
                stringChar = null;
                result += '"';
            } else {
                result += char;
            }
        } else if (inString && char === '"') {
            // Escape double quotes inside strings
            result += '\\"';
        } else {
            result += char;
        }
        i++;
    }

    // Restore escaped quotes
    result = result.replace(/___ESCAPED_QUOTE___/g, "'");

    // Try to parse
    const segments = JSON.parse(result);

    // Extract all words from segments
    for (const segment of segments) {
        if (segment.words && Array.isArray(segment.words)) {
            for (const word of segment.words) {
                const startVal = word.start;
                const endVal = word.end;

                allWords.push({
                    word: String(word.word || '').trim(),
                    start: typeof startVal === 'number' ? startVal : parseFloat(String(startVal)) || 0,
                    end: typeof endVal === 'number' ? endVal : parseFloat(String(endVal)) || 0
                });
            }
        }
    }

    console.log('Successfully parsed', allWords.length, 'words');

} catch (e) {
    console.log('Parse error:', e.message);
    console.log('Trying alternative parsing approach...');

    // Alternative: Use regex to extract word timestamps directly
    try {
        const wordRegex = /\{'word':\s*['"](.*?)['"],\s*'start':\s*(?:np\.float64\()?([\d.]+)\)?,\s*'end':\s*(?:np\.float64\()?([\d.]+)\)?/g;

        let match;
        const rawData = String(wordTimestampsRaw);

        while ((match = wordRegex.exec(rawData)) !== null) {
            allWords.push({
                word: match[1].trim(),
                start: parseFloat(match[2]),
                end: parseFloat(match[3])
            });
        }

        console.log('Regex extracted', allWords.length, 'words');

    } catch (e2) {
        console.log('Regex extraction also failed:', e2.message);
        return aiClips.map(clip => ({ json: { ...clip, error: 'Could not parse word timestamps: ' + e.message } }));
    }
}

if (allWords.length === 0) {
    return aiClips.map(clip => ({ json: { ...clip, error: 'No words extracted from timestamps' } }));
}

// Helper: Convert "HH:MM:SS" to seconds
function timeToSeconds(timeStr) {
    if (typeof timeStr === 'number') return timeStr;
    if (!timeStr) return 0;

    const parts = String(timeStr).split(':').map(Number);
    if (parts.length === 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
        return parts[0] * 60 + parts[1];
    }
    return parseFloat(timeStr) || 0;
}

// Helper: Convert seconds to "HH:MM:SS"
function secondsToTime(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// Find nearest word boundary
function findNearestWord(targetSeconds, type) {
    let best = null;
    let bestDiff = Infinity;

    for (const w of allWords) {
        const t = type === 'start' ? w.start : w.end;
        const diff = Math.abs(t - targetSeconds);
        if (diff < bestDiff) {
            bestDiff = diff;
            best = w;
        }
    }
    return best;
}

// Process each clip
const correctedClips = [];

for (const clip of aiClips) {
    const origStart = clip.timeStart || clip.startTime || clip.start_time;
    const origEnd = clip.timeEnd || clip.endTime || clip.end_time;

    if (!origStart || !origEnd) {
        correctedClips.push({ json: clip });
        continue;
    }

    const startSec = timeToSeconds(origStart);
    const endSec = timeToSeconds(origEnd);

    // Find nearest word boundaries
    const startWord = findNearestWord(startSec, 'start');
    const endWord = findNearestWord(endSec, 'end');

    const newStartSec = startWord ? startWord.start : startSec;
    const newEndSec = endWord ? endWord.end : endSec;

    correctedClips.push({
        json: {
            ...clip,
            originalTimeStart: origStart,
            originalTimeEnd: origEnd,
            timeStart: secondsToTime(newStartSec),
            timeEnd: secondsToTime(newEndSec),
            timeStartSeconds: newStartSec,
            timeEndSeconds: newEndSec,
            startsAt: startWord ? startWord.word : null,
            endsAt: endWord ? endWord.word : null,
            duration: Math.round((newEndSec - newStartSec) * 100) / 100
        }
    });

    console.log(`Corrected: ${origStart} → ${secondsToTime(newStartSec)}, ${origEnd} → ${secondsToTime(newEndSec)}`);
}

return correctedClips;
