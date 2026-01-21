import { useEffect, useRef, useCallback } from "react";
import { API_CONFIG } from "../config";
import { useChatStore } from "../store/useChatStore";

interface GatewayProps {
    onChatStart?: (mode: string) => void;
    onChatStream?: (content: string) => void;
    onChatEnd?: () => void;
    onEmotion?: (emotion: string) => void;
    onSessionReset?: (sessionId: number) => void;
    baseUrl?: string;
}

// ... Protocol Interfaces (Keep same) ...
interface EventPacket {
    trace_id: string;
    session_id: number;
    sequence_number: number;
    type: string;
    source: string;
    payload: any;
    timestamp: number;
}

const EventType = {
    BRAIN_THINKING: "brain_thinking",
    BRAIN_RESPONSE: "brain_response",
    BRAIN_RESPONSE_END: "brain_response_end",
    SYSTEM_STATUS: "system_status",
    CONTROL_SESSION: "control_session",
    EMOTION_CHANGED: "emotion:changed",
    UI_REGISTER_WIDGET: "ui:register_widget",
    UI_REMOVE_WIDGET: "ui:remove_widget",
    PLUGIN_STATUS: "plugin_status",
};

// ========== [FIX] Singleton Connection Guard ==========
// Prevents React 18 dev mode from creating duplicate WebSocket connections
let globalWsInstance: WebSocket | null = null;
let globalWsUrl: string | null = null;
let connectionCount = 0;
// ======================================================

export const useGateway = ({
    onChatStart,
    onChatStream,
    onChatEnd,
    onEmotion,
    onSessionReset,
    baseUrl,
}: GatewayProps) => {
    const wsRef = useRef<WebSocket | null>(null);

    // Store Actions (Direct access to avoid re-renders)
    const { setConnection, setSessionId, setEmotion } = useChatStore.getState();
    const isConnected = useChatStore((state) => state.isConnected); // Reactive for return

    const currentSessionIdRef = useRef<number>(0);
    const lastSequenceRef = useRef<number>(-1); // [Architecture 4.2] Tier C: Sequence Tracker
    const pendingQueueRef = useRef<{ type: string; payload: any }[]>([]);

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
        const targetBaseUrl = baseUrl || API_CONFIG.BASE_URL;
        const wsUrl =
            targetBaseUrl.replace("http", "ws") + "/lumina/gateway/ws";

        let ws: WebSocket;
        let keepAliveTimer: any;
        let reconnectTimer: any;

        const flushQueue = () => {
            if (
                ws &&
                ws.readyState === WebSocket.OPEN &&
                currentSessionIdRef.current >= 0
            ) {
                while (pendingQueueRef.current.length > 0) {
                    const item = pendingQueueRef.current.shift();
                    if (item) {
                        const packet: EventPacket = {
                            trace_id: crypto.randomUUID(),
                            session_id: currentSessionIdRef.current,
                            sequence_number: 0, // Placeholder
                            type: item.type,
                            source: "frontend",
                            payload: item.payload,
                            timestamp: Date.now(),
                        };
                        ws.send(JSON.stringify(packet));
                    }
                }
            }
        };

        const connect = () => {
            connectionCount++;
            const connId = connectionCount;
            console.log(`[Gateway #${connId}] Attempting connection to`, wsUrl);

            // [FIX] Singleton Guard: Reuse existing connection if same URL
            if (
                globalWsInstance &&
                globalWsUrl === wsUrl &&
                globalWsInstance.readyState === WebSocket.OPEN
            ) {
                console.log(`[Gateway #${connId}] Reusing existing connection`);
                ws = globalWsInstance;
                wsRef.current = ws;
                useChatStore.getState().setConnection(true);
                return;
            }

            // Close any stale global connection
            if (
                globalWsInstance &&
                globalWsInstance.readyState !== WebSocket.CLOSED
            ) {
                console.log(`[Gateway #${connId}] Closing stale connection`);
                globalWsInstance.close();
            }

            console.log(`[Gateway #${connId}] Creating new connection`);
            ws = new WebSocket(wsUrl);
            globalWsInstance = ws;
            globalWsUrl = wsUrl;

            ws.onopen = () => {
                console.log(`[Gateway #${connId}] Connected`);
                useChatStore.getState().setConnection(true);
                wsRef.current = ws;
                flushQueue();
                keepAliveTimer = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) ws.send("ping");
                }, 30000);
            };

            ws.onclose = () => {
                console.log("[Gateway] Disconnected. Reconnecting...");
                useChatStore.getState().setConnection(false);
                wsRef.current = null;
                clearInterval(keepAliveTimer);
                reconnectTimer = setTimeout(connect, 3000);
            };

            ws.onerror = (err) => console.warn("[Gateway] Error:", err);

            ws.onmessage = (event) => {
                try {
                    if (event.data === "pong") return;
                    try {
                        if (JSON.parse(event.data).type === "pong") return;
                    } catch {}

                    const packet: EventPacket = JSON.parse(event.data);

                    // [Architecture 4.2] Tier C: Idempotency Guard
                    // 1. Session Jump? Reset Sequence tracker
                    if (packet.session_id > currentSessionIdRef.current) {
                        lastSequenceRef.current = -1;
                    }
                    // 2. Duplicate or Out-of-order? Drop it.
                    else if (
                        packet.session_id === currentSessionIdRef.current
                    ) {
                        if (packet.sequence_number <= lastSequenceRef.current) {
                            // console.warn(`[Gateway] Dropped redundant packet: Seq ${packet.sequence_number}`);
                            return;
                        }
                    }

                    lastSequenceRef.current = packet.sequence_number;

                    // Session Awareness (System packets usually have 0 session_id, we need to handle carefully)
                    if (
                        packet.type === EventType.SYSTEM_STATUS ||
                        packet.type === EventType.CONTROL_SESSION
                    ) {
                        if (packet.payload?.session_id) {
                            const newId = packet.payload.session_id;
                            if (newId > currentSessionIdRef.current) {
                                console.log(`[Gateway] New Session: ${newId}`);
                                currentSessionIdRef.current = newId;
                                useChatStore.getState().setSessionId(newId); // Sync Store

                                if (packet.type === EventType.CONTROL_SESSION) {
                                    callbacksRef.current.onSessionReset?.(
                                        newId,
                                    );
                                }
                                flushQueue();
                            }
                        }
                        return;
                    }

                    if (packet.session_id < currentSessionIdRef.current) return;

                    // Logic Mapping
                    switch (packet.type) {
                        case EventType.BRAIN_THINKING:
                            console.log(
                                "[useGateway] 🧠 BRAIN_THINKING received - will call onChatStart",
                            );
                            callbacksRef.current.onChatStart?.(
                                packet.payload?.mode || "proactive",
                            );
                            break;
                        case EventType.BRAIN_RESPONSE:
                            if (packet.payload?.content)
                                callbacksRef.current.onChatStream?.(
                                    packet.payload.content,
                                );
                            break;
                        case EventType.BRAIN_RESPONSE_END:
                            callbacksRef.current.onChatEnd?.();
                            break;
                        case EventType.EMOTION_CHANGED:
                            if (packet.payload?.emotion) {
                                const emo = packet.payload.emotion;
                                useChatStore.getState().setEmotion(emo); // Sync Store
                                callbacksRef.current.onEmotion?.(emo);
                                window.dispatchEvent(
                                    new CustomEvent("lumina:emotion", {
                                        detail: { emotion: emo },
                                    }),
                                );
                            }
                            break;
                        case EventType.UI_REGISTER_WIDGET:
                        case EventType.UI_REMOVE_WIDGET:
                        case "ui:unregister_widget":
                            window.dispatchEvent(
                                new CustomEvent("lumina:widget", {
                                    detail: {
                                        type: packet.type,
                                        payload: packet.payload,
                                    },
                                }),
                            );
                            break;
                        case EventType.PLUGIN_STATUS:
                            window.dispatchEvent(
                                new CustomEvent("lumina:plugin_status", {
                                    detail: packet.payload,
                                }),
                            );
                            break;
                    }
                } catch (e) {
                    console.warn("[Gateway] Parse Error:", e);
                }
            };
        };

        connect();

        return () => {
            ws?.close();
            clearInterval(keepAliveTimer);
            if (reconnectTimer) clearTimeout(reconnectTimer);
        };
    }, [baseUrl]);

    const send = useCallback((type: string, payload: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            if (currentSessionIdRef.current >= 0) {
                const packet: EventPacket = {
                    trace_id: crypto.randomUUID(),
                    session_id: currentSessionIdRef.current,
                    sequence_number: 0, // Placeholder
                    type,
                    source: "frontend",
                    payload,
                    timestamp: Date.now(),
                };
                wsRef.current.send(JSON.stringify(packet));
            } else {
                console.log("[Gateway] Session not ready, queuing:", type);
                pendingQueueRef.current.push({ type, payload });
            }
        } else {
            console.log("[Gateway] Offline, queuing:", type);
            pendingQueueRef.current.push({ type, payload });
        }
    }, []);
    // }; [Fixed] Removed extra closing brace

    return { isConnected, send };
};
