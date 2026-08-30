import { useRef, useCallback } from "react";
import { finalizeAssistantContent } from "../utils/chatContent";

interface TurnBuffer {
    raw: string;
    reasoning: string;
}

/**
 * useChatStream Hook
 *
 * Manages chat stream state and processing.
 * Handles token accumulation and response cleanup.
 *
 * Extracted from App.tsx to improve modularity.
 */
export function useChatStream() {
    const buffersRef = useRef<Map<string, TurnBuffer>>(new Map());
    const activeTurnIdRef = useRef<string | null>(null);

    /**
     * Reset all buffers at the start of a new stream.
     */
    const reset = useCallback((turnId?: string) => {
        if (turnId) {
            buffersRef.current.delete(turnId);
            if (activeTurnIdRef.current !== turnId) return;
        } else {
            buffersRef.current.clear();
        }
        activeTurnIdRef.current = null;
    }, []);

    const start = useCallback((turnId: string) => {
        buffersRef.current.set(turnId, { raw: "", reasoning: "" });
        activeTurnIdRef.current = turnId;
    }, []);

    /**
     * Process an incoming token.
     * @param token The token received from the stream
     * @param type 'content' for main response, 'reasoning' for thinking content
     */
    const processToken = useCallback(
        (
            turnId: string,
            token: string,
            type: "content" | "reasoning" = "content",
        ): TurnBuffer => {
            const buffer = buffersRef.current.get(turnId) ?? {
                raw: "",
                reasoning: "",
            };
            if (type === "reasoning") {
                buffer.reasoning += token;
            } else {
                buffer.raw += token;
            }
            buffersRef.current.set(turnId, buffer);
            return buffer;
        },
        [],
    );

    /**
     * Get the final cleaned content for saving to history.
     */
    const getFinalContent = useCallback((turnId: string) => {
        return finalizeAssistantContent(buffersRef.current.get(turnId)?.raw || "");
    }, []);

    /**
     * Get the raw response (with tags intact).
     */
    const getRawResponse = useCallback((turnId: string) => {
        return buffersRef.current.get(turnId)?.raw || "";
    }, []);

    const finish = useCallback((turnId: string) => {
        const buffer = buffersRef.current.get(turnId) ?? {
            raw: "",
            reasoning: "",
        };
        const result = {
            content: finalizeAssistantContent(buffer.raw),
            reasoning: buffer.reasoning,
        };
        buffersRef.current.delete(turnId);
        if (activeTurnIdRef.current === turnId) {
            activeTurnIdRef.current = null;
        }
        return result;
    }, []);

    return {
        start,
        reset,
        processToken,
        finish,
        getFinalContent,
        getRawResponse,
    };
}
