import { useEffect, useRef, useCallback } from "react";
import { useChatStore } from "../store/useChatStore";
import { gatewayClient, GatewaySubscriber } from "../runtime/gatewayClient";

interface GatewayProps {
    onChatStart?: (mode: string) => void;
    onChatStream?: (content: string) => void;
    onChatEnd?: () => void;
    onEmotion?: (emotion: string) => void;
    onSessionReset?: (sessionId: number) => void;
    baseUrl: string;
    enabled?: boolean;
}

export const useGateway = ({
    onChatStart,
    onChatStream,
    onChatEnd,
    onEmotion,
    onSessionReset,
    baseUrl,
    enabled = true,
}: GatewayProps) => {
    const isConnected = useChatStore((state) => state.isConnected);

    const callbacksRef = useRef({
        onChatStart,
        onChatStream,
        onChatEnd,
        onEmotion,
        onSessionReset,
    });

    useEffect(() => {
        callbacksRef.current = {
            onChatStart,
            onChatStream,
            onChatEnd,
            onEmotion,
            onSessionReset,
        };
    }, [onChatStart, onChatStream, onChatEnd, onEmotion, onSessionReset]);

    useEffect(() => {
        if (!enabled) {
            gatewayClient.disconnect();
            return;
        }

        gatewayClient.connect(baseUrl);
        const unsubscribe = gatewayClient.subscribe({
            onChatStart: (mode) => callbacksRef.current.onChatStart?.(mode),
            onChatStream: (content) =>
                callbacksRef.current.onChatStream?.(content),
            onChatEnd: () => callbacksRef.current.onChatEnd?.(),
            onEmotion: (emotion) => callbacksRef.current.onEmotion?.(emotion),
            onSessionReset: (sessionId) =>
                callbacksRef.current.onSessionReset?.(sessionId),
        } satisfies GatewaySubscriber);

        return () => {
            unsubscribe();
        };
    }, [baseUrl, enabled]);

    const send = useCallback((type: string, payload: any) => {
        gatewayClient.send(type, payload);
    }, []);

    return { isConnected, send };
};
