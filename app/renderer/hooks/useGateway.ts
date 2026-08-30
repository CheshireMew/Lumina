import { useEffect, useRef, useCallback } from "react";
import { useChatStore } from "../store/useChatStore";
import { gatewayClient, GatewaySubscriber } from "../runtime/gatewayClient";
import type { GatewaySystemStatus } from "../runtime/gatewayProtocol";

interface GatewayProps {
    onReady?: (clientId: string, sessionId: number, generation: number) => void;
    onChatStart?: (turnId: string, mode: string) => void;
    onChatStream?: (turnId: string, content: string) => void;
    onChatReasoning?: (turnId: string, content: string) => void;
    onChatEnd?: (turnId: string, status: string) => void;
    onEmotion?: (emotion: string) => void;
    onSessionReset?: (sessionId: number, generation: number) => void;
    onSystemStatus?: (status: GatewaySystemStatus) => void;
    baseUrl: string;
    enabled?: boolean;
}

export const useGateway = ({
    onChatStart,
    onChatStream,
    onChatEnd,
    onChatReasoning,
    onReady,
    onEmotion,
    onSessionReset,
    onSystemStatus,
    baseUrl,
    enabled = true,
}: GatewayProps) => {
    const isConnected = useChatStore((state) => state.isConnected);
    const setConnection = useChatStore((state) => state.setConnection);
    const setSession = useChatStore((state) => state.setSession);
    const setEmotion = useChatStore((state) => state.setEmotion);

    const callbacksRef = useRef({
        onChatStart,
        onChatStream,
        onChatEnd,
        onChatReasoning,
        onReady,
        onEmotion,
        onSessionReset,
        onSystemStatus,
    });

    useEffect(() => {
        callbacksRef.current = {
            onChatStart,
            onChatStream,
            onChatEnd,
            onChatReasoning,
            onReady,
            onEmotion,
            onSessionReset,
            onSystemStatus,
        };
    }, [onChatStart, onChatStream, onChatEnd, onChatReasoning, onReady, onEmotion, onSessionReset, onSystemStatus]);

    useEffect(() => {
        if (!enabled) {
            gatewayClient.disconnect();
            setConnection(false);
            return;
        }

        gatewayClient.connect(baseUrl);
        const unsubscribe = gatewayClient.subscribe({
            onConnection: setConnection,
            onReady: (clientId, sessionId, generation) => {
                setSession(sessionId, generation);
                callbacksRef.current.onReady?.(clientId, sessionId, generation);
            },
            onChatStart: (turnId, mode) =>
                callbacksRef.current.onChatStart?.(turnId, mode),
            onChatStream: (turnId, content) =>
                callbacksRef.current.onChatStream?.(turnId, content),
            onChatReasoning: (turnId, content) =>
                callbacksRef.current.onChatReasoning?.(turnId, content),
            onChatEnd: (turnId, status) =>
                callbacksRef.current.onChatEnd?.(turnId, status),
            onEmotion: (emotion) => {
                setEmotion(emotion);
                callbacksRef.current.onEmotion?.(emotion);
            },
            onSessionReset: (sessionId, generation) =>
                callbacksRef.current.onSessionReset?.(sessionId, generation),
            onSystemStatus: (status) =>
                callbacksRef.current.onSystemStatus?.(status),
        } satisfies GatewaySubscriber);

        return () => {
            unsubscribe();
        };
    }, [baseUrl, enabled, setConnection, setEmotion, setSession]);

    const send = useCallback((
        type: string,
        payload: Record<string, unknown>,
        turnId?: string,
    ) => {
        return gatewayClient.send(type, payload, turnId);
    }, []);

    return { isConnected, send };
};
