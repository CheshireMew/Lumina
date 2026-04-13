import { useRef, useCallback, useState } from "react";
import {
    finalizeAssistantContent,
    formatAssistantDisplay,
} from "../utils/chatContent";

/**
 * useChatStream Hook
 *
 * Manages chat stream state and processing.
 * Handles token accumulation and response cleanup.
 *
 * Extracted from App.tsx to improve modularity.
 */
export function useChatStream() {
    const [displayMessage, setDisplayMessage] = useState<string>("");
    const [reasoningContent, setReasoningContent] = useState<string>("");

    const fullRawResponseRef = useRef<string>("");
    const reasoningBufferRef = useRef<string>("");

    /**
     * Reset all buffers at the start of a new stream.
     */
    const reset = useCallback(() => {
        console.log("[useChatStream] 🔄 RESET called - clearing all buffers");
        fullRawResponseRef.current = "";
        reasoningBufferRef.current = "";
        setDisplayMessage("");
        setReasoningContent("");
    }, []);

    /**
     * Process an incoming token.
     * @param token The token received from the stream
     * @param type 'content' for main response, 'reasoning' for thinking content
     */
    const processToken = useCallback(
        (token: string, type: "content" | "reasoning" = "content") => {
            if (type === "reasoning") {
                reasoningBufferRef.current += token;
                setReasoningContent(reasoningBufferRef.current);
                return;
            }

            // [DEBUG] Log every token received
            console.log(
                `[useChatStream] Token received: "${token.slice(0, 20)}..." | Buffer before: ${fullRawResponseRef.current.length} chars`,
            );

            fullRawResponseRef.current += token;
            setDisplayMessage(formatAssistantDisplay(fullRawResponseRef.current));
        },
        [],
    );

    /**
     * Get the final cleaned content for saving to history.
     */
    const getFinalContent = useCallback(() => {
        return finalizeAssistantContent(fullRawResponseRef.current);
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
