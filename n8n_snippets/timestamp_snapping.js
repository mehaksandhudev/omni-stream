/**
 * Timestamp Snapping Logic for n8n Code Node
 * 
 * INPUTS expected from previous nodes:
 * 1. 'viral_clips': Array of objects [{ start: 10.5, end: 15.2 }, ...] (from AI analysis)
 * 2. 'aligned_words': Array of objects [{ word: "hello", start: 10.52, end: 10.9 }, ...] (from Alignment Service)
 */

const clips = items[0].json.viral_clips;
// Assuming alignment service output is in items[0].json.whisper_result.segments... but let's assume flattened words list
// You might need to flatten segments -> words in a previous step or here.
let allWords = [];
if (items[0].json.whisper_result && items[0].json.whisper_result.segments) {
    for (const seg of items[0].json.whisper_result.segments) {
        if (seg.words) {
            allWords.push(...seg.words);
        }
    }
}

const correctedClips = clips.map(clip => {
    const targetStart = clip.start;
    const targetEnd = clip.end;

    // Find the word that starts closest to the targetStart
    let bestStartWord = null;
    let minStartDiff = Infinity;

    // Find the word that ends closest to the targetEnd
    let bestEndWord = null;
    let minEndDiff = Infinity;

    for (const word of allWords) {
        // Check Start
        const startDiff = Math.abs(word.start - targetStart);
        if (startDiff < minStartDiff) {
            minStartDiff = startDiff;
            bestStartWord = word;
        }

        // Check End
        const endDiff = Math.abs(word.end - targetEnd);
        if (endDiff < minEndDiff) {
            minEndDiff = endDiff;
            bestEndWord = word;
        }
    }

    // Safety fallback
    const finalStart = bestStartWord ? bestStartWord.start : targetStart;
    const finalEnd = bestEndWord ? bestEndWord.end : targetEnd;

    return {
        original_start: targetStart,
        original_end: targetEnd,
        snapped_start: finalStart,
        snapped_end: finalEnd,
        duration: finalEnd - finalStart,
        text_content: getWordsBetween(allWords, finalStart, finalEnd)
    };
});

function getWordsBetween(words, start, end) {
    return words
        .filter(w => w.start >= start && w.end <= end)
        .map(w => w.word)
        .join("");
}

return [{ json: { corrected_clips: correctedClips } }];
