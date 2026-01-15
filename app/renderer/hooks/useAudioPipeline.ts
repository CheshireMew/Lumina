import { useRef, useCallback } from "react";
import { ttsService } from "@core/voice/tts_service";
import { SentenceSplitter } from "@core/voice/sentence_splitter";
import { AudioQueue } from "@core/voice/audio_queue";

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
  const audioQueueRef = useRef<AudioQueue>(new AudioQueue());
  const sentenceSplitterRef = useRef<SentenceSplitter | null>(null);
  const synthPromisesRef = useRef<Promise<void>[]>([]);
  const sentenceIndexRef = useRef<number>(0);

  /**
   * Initialize the pipeline for a new response stream.
   * Call this at the start of each AI response.
   */
  const initPipeline = useCallback(
    (onSentenceReady: (sentence: string, index: number) => void) => {
      sentenceIndexRef.current = 0;
      synthPromisesRef.current = [];
      audioQueueRef.current.clear();

      sentenceSplitterRef.current = new SentenceSplitter((sentence) => {
        const cleanSentence = sentence.trim();
        if (cleanSentence.length > 0) {
          onSentenceReady(cleanSentence, sentenceIndexRef.current++);
        }
      });
    },
    []
  );

  /**
   * Enqueue a sentence for synthesis.
   * Synthesis happens concurrently, but playback is sequential.
   */
  const enqueueSynthesis = useCallback((sentence: string, index: number) => {
    const synthPromise = (async () => {
      // Filter empty/symbol-only sentences
      const cleanSentence = sentence
        .replace(/[。！？!?,，、；&\n\s]/g, "")
        .trim();
      if (cleanSentence.length === 0) {
        console.log(`[AudioPipeline] Skipping empty sentence: "${sentence}"`);
        return;
      }

      console.log(
        `[AudioPipeline] Synthesizing ${index}:`,
        sentence.slice(0, 30)
      );
      try {
        // 1. Start synthesis immediately (concurrent)
        const audioResponse = await ttsService.synthesize(sentence);

        // 2. Wait for previous sentence to finish enqueuing (preserve order)
        if (index > 0) {
          await synthPromisesRef.current[index - 1];
        }

        // 3. Enqueue in order
        if (audioResponse) {
          audioQueueRef.current.enqueue(audioResponse);
          console.log(
            `[AudioPipeline] Enqueued ${index} (Queue: ${audioQueueRef.current.length})`
          );
        }
      } catch (error) {
        console.error(`[AudioPipeline] Synthesis failed for ${index}:`, error);
      }
    })();

    synthPromisesRef.current[index] = synthPromise;
  }, []);

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
    audioQueueRef.current.clear();
    synthPromisesRef.current = [];
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
