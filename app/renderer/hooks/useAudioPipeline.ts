import { useRef, useCallback, useEffect } from "react";
import { ttsService } from "@core/voice/tts_service";
import { SentenceSplitter } from "@core/voice/sentence_splitter";
import { AudioQueue } from "@core/voice/audio_queue";
import type { AudioResponse } from "@core/voice/types";

const MAX_CONCURRENT_SYNTHESIS = 2;
const MAX_PENDING_SENTENCES = 8;

interface SynthesisJob {
    sequence: number;
    text: string;
}

interface SynthesisRun {
    id: number;
    active: number;
    nextSequence: number;
    nextPlayback: number;
    pending: SynthesisJob[];
    completed: Map<number, AudioResponse | null>;
}

/**
 * useAudioPipeline Hook
 *
 * Manages TTS synthesis and audio playback queue.
 * Extracted from App.tsx to improve modularity.
 *
 * Features:
 * - Concurrent synthesis (multiple sentences synthesize in parallel)
 * - Sequential playback (audio plays in order)
 * - Automatic queue management
 */
export function useAudioPipeline() {
    const audioQueueRef = useRef<AudioQueue | null>(null);
    if (audioQueueRef.current === null) {
        audioQueueRef.current = new AudioQueue();
    }
    const sentenceSplitterRef = useRef<SentenceSplitter | null>(null);
    const sentenceIndexRef = useRef<number>(0);
    const runIdRef = useRef<number>(0);
    const synthesisRunRef = useRef<SynthesisRun | null>(null);

    const drainCompleted = useCallback((run: SynthesisRun) => {
        while (run.completed.has(run.nextPlayback)) {
            const audioResponse = run.completed.get(run.nextPlayback) ?? null;
            run.completed.delete(run.nextPlayback);
            run.nextPlayback++;
            if (audioResponse && synthesisRunRef.current === run) {
                audioQueueRef.current?.enqueue(audioResponse);
            }
        }
    }, []);

    const pumpSynthesis = useCallback((run: SynthesisRun) => {
        while (
            synthesisRunRef.current === run &&
            run.active < MAX_CONCURRENT_SYNTHESIS &&
            run.pending.length > 0
        ) {
            const job = run.pending.shift()!;
            run.active++;
            void ttsService.synthesize(job.text).then((audioResponse) => {
                if (synthesisRunRef.current === run) {
                    run.completed.set(job.sequence, audioResponse);
                }
            }).catch((error) => {
                console.error(
                    `[AudioPipeline] Synthesis failed for ${job.sequence}:`,
                    error,
                );
                if (synthesisRunRef.current === run) {
                    run.completed.set(job.sequence, null);
                }
            }).finally(() => {
                run.active--;
                if (synthesisRunRef.current !== run) return;
                drainCompleted(run);
                pumpSynthesis(run);
            });
        }
    }, [drainCompleted]);

    /**
     * Initialize the pipeline for a new response stream.
     * Call this at the start of each AI response.
     */
    const initPipeline = useCallback(
        (onSentenceReady: (sentence: string, index: number) => void) => {
            sentenceIndexRef.current = 0;
            runIdRef.current++; // New run
            ttsService.stop();
            synthesisRunRef.current = {
                id: runIdRef.current,
                active: 0,
                nextSequence: 0,
                nextPlayback: 0,
                pending: [],
                completed: new Map(),
            };
            audioQueueRef.current?.clear();

            sentenceSplitterRef.current = new SentenceSplitter((sentence) => {
                const cleanSentence = sentence.trim();
                if (cleanSentence.length > 0) {
                    onSentenceReady(cleanSentence, sentenceIndexRef.current++);
                }
            });
        },
        [],
    );

    /**
     * Enqueue a sentence for synthesis.
     * Synthesis happens concurrently, but playback is sequential.
     */
    const enqueueSynthesis = useCallback((sentence: string, _index: number) => {
        const run = synthesisRunRef.current;
        if (!run) return;
        const cleanSentence = sentence
            .replace(/\[.*?\]/g, "")
            .replace(/\(.*?\)/g, "")
            .replace(/（.*?）/g, "")
            .replace(/<\|.*?\|>/g, "")
            .trim();
        if (!cleanSentence.replace(/[。！？!?,，、；&\n\s]/g, "")) return;

        if (run.pending.length >= MAX_PENDING_SENTENCES) {
            const tail = run.pending[run.pending.length - 1];
            tail.text = `${tail.text}${cleanSentence}`;
        } else {
            run.pending.push({
                sequence: run.nextSequence++,
                text: cleanSentence,
            });
        }
        pumpSynthesis(run);
    }, [pumpSynthesis]);

    /**
     * Feed a token to the sentence splitter.
     * Call this for each token received during streaming.
     */
    const feedToken = useCallback((token: string) => {
        sentenceSplitterRef.current?.feedToken(token);
    }, []);

    /**
     * Flush any remaining content in the splitter.
     * Call this when the stream ends.
     */
    const flush = useCallback(() => {
        sentenceSplitterRef.current?.flush();
    }, []);

    /**
     * Clear the audio queue immediately.
     * Use for interruption scenarios.
     */
    const clear = useCallback(() => {
        ttsService.stop(); // Abort network requests
        runIdRef.current++; // Invalidate pending promises
        synthesisRunRef.current = null;
        audioQueueRef.current?.clear();
    }, []);

    useEffect(() => {
        return () => {
            ttsService.stop();
            audioQueueRef.current?.clear();
        };
    }, []);

    return {
        initPipeline,
        enqueueSynthesis,
        feedToken,
        flush,
        clear,
        audioQueue: audioQueueRef.current,
    };
}
