import { useRef, useCallback, useState } from "react";

/**
 * useChatStream Hook
 *
 * Manages chat stream state and processing.
 * Handles token accumulation, emotion tag detection, and display cleanup.
 *
 * Extracted from App.tsx to improve modularity.
 */
export function useChatStream() {
  const [displayMessage, setDisplayMessage] = useState<string>("");
  const [reasoningContent, setReasoningContent] = useState<string>("");

  const fullRawResponseRef = useRef<string>("");
  const emotionBufferRef = useRef<string>("");
  const reasoningBufferRef = useRef<string>("");

  /**
   * Reset all buffers at the start of a new stream.
   */
  const reset = useCallback(() => {
    fullRawResponseRef.current = "";
    emotionBufferRef.current = "";
    reasoningBufferRef.current = "";
    setDisplayMessage("");
    setReasoningContent("");
  }, []);

  /**
   * Process an incoming token.
   * @param token The token received from the stream
   * @param type 'content' for main response, 'reasoning' for thinking content
   * @param onEmotionDetected Callback when an emotion tag is detected
   */
  const processToken = useCallback(
    (
      token: string,
      type: "content" | "reasoning" = "content",
      onEmotionDetected?: (emotion: string) => void
    ) => {
      if (type === "reasoning") {
        reasoningBufferRef.current += token;
        setReasoningContent(reasoningBufferRef.current);
        return;
      }

      fullRawResponseRef.current += token;
      emotionBufferRef.current += token;

      // Emotion Detection
      if (token.includes(")") || token.includes("]")) {
        // Check for emotion tags like [joy] or (happy)
        const emotionMatch = emotionBufferRef.current.match(
          /[\[\(](joy|happy|sad|angry|surprised|neutral|thinking)[\]\)]/i
        );
        if (emotionMatch && onEmotionDetected) {
          onEmotionDetected(emotionMatch[1].toLowerCase());
          emotionBufferRef.current = "";
        }

        // Keep buffer from growing too large
        if (emotionBufferRef.current.length > 50) {
          emotionBufferRef.current = emotionBufferRef.current.slice(-20);
        }
      }

      // Display Processing (cleanup tags)
      let displayUpdate = fullRawResponseRef.current;
      displayUpdate = displayUpdate
        .replace(/\[[^\]]*\]/g, "") // Remove [tags]
        .replace(/\([^)]*\)/g, "") // Remove (tags)
        .replace(/（[^）]*）/g, "") // Remove （中文tags）
        .replace(/&/g, ""); // Remove &

      setDisplayMessage(displayUpdate);
    },
    []
  );

  /**
   * Get the final cleaned content for saving to history.
   */
  const getFinalContent = useCallback(() => {
    return fullRawResponseRef.current
      .replace(/\[[^\]]*\]/g, "")
      .replace(/\([^)]*\)/g, "")
      .replace(/（[^）]*）/g, "")
      .replace(/&/g, "")
      .trim();
  }, []);

  /**
   * Get the raw response (with tags intact).
   */
  const getRawResponse = useCallback(() => {
    return fullRawResponseRef.current;
  }, []);

  return {
    displayMessage,
    reasoningContent,
    reset,
    processToken,
    getFinalContent,
    getRawResponse,
  };
}
