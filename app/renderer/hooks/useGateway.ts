import { useEffect, useRef, useState } from "react";
import { API_CONFIG } from "../config";

interface GatewayProps {
    onChatStart?: (mode: string) => void;
    onChatStream?: (content: string) => void;
    onChatEnd?: () => void;
    onEmotion?: (emotion: string) => void; // [Phase 32] Emotion event from backend Broker
    baseUrl?: string;
}

// --- Protocol Definition ---
interface EventPacket {
    trace_id: string;
    session_id: number;
    type: string;
    source: string;
    payload: any;
    timestamp: number;
}

const EventType = {
    BRAIN_THINKING: "brain_thinking",
    BRAIN_RESPONSE: "brain_response",
    SYSTEM_STATUS: "system_status",
    CONTROL_SESSION: "control_session",
    EMOTION_CHANGED: "emotion:changed", // [Phase 32]
};

export const useGateway = ({
    onChatStart,
    onChatStream,
    onChatEnd,
    onEmotion,
    baseUrl,
}: GatewayProps) => {
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const currentSessionIdRef = useRef<number>(0);
    const pendingQueueRef = useRef<{ type: string; payload: any }[]>([]);

    // Use refs to keep callbacks fresh without reconnecting WS
    const callbacksRef = useRef({
        onChatStart,
        onChatStream,
        onChatEnd,
        onEmotion,
    });

    useEffect(() => {
        callbacksRef.current = {
            onChatStart,
            onChatStream,
            onChatEnd,
            onEmotion,
        };
    }, [onChatStart, onChatStream, onChatEnd, onEmotion]);

    useEffect(() => {
        // Determine WS URL (assume backend port 8010 based on standard setup)
        // [Fix] Use provided baseUrl or fallback to config
        const targetBaseUrl = baseUrl || API_CONFIG.BASE_URL;
        const wsUrl =
            targetBaseUrl.replace("http", "ws") + "/lumina/gateway/ws";

        let ws: WebSocket;
        let keepAliveTimer: any;

        const flushQueue = () => {
            if (
                ws &&
                ws.readyState === WebSocket.OPEN &&
                currentSessionIdRef.current >= 0
            ) {
                while (pendingQueueRef.current.length > 0) {
                    const item = pendingQueueRef.current.shift();
                    if (item) {
                        console.log(
                            `[Gateway] Flushing queued message: ${item.type}`
                        );
                        const packet: EventPacket = {
                            trace_id: crypto.randomUUID(),
                            session_id: currentSessionIdRef.current,
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
            console.log("[Gateway] Connecting to", wsUrl);
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("[Gateway] Connected");
                setIsConnected(true);
                wsRef.current = ws;

                // Flush early messages if session assumed valid (0)
                flushQueue();

                // Keep Alive (Ping every 30s)
                keepAliveTimer = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) ws.send("ping");
                }, 30000);
            };

            ws.onclose = () => {
                console.log("[Gateway] Disconnected. Reconnecting in 3s...");
                setIsConnected(false);
                wsRef.current = null;
                clearInterval(keepAliveTimer);
                setTimeout(connect, 3000);
            };

            ws.onerror = (err) => {
                console.warn("[Gateway] Error:", err);
            };

            ws.onmessage = (event) => {
                try {
                    // 1. Handle Ping-Pong
                    if (event.data === "pong") return;
                    try {
                        // Check if it's simple pong JSON
                        const raw = JSON.parse(event.data);
                        if (raw.type === "pong") return;
                    } catch {}

                    // 2. Parse Packet
                    const packet: EventPacket = JSON.parse(event.data);

                    // 3. Log Source
                    // console.log(`[EventBus] <${packet.source}> ${packet.type}`, packet.payload);

                    // 4. Update Session Awareness
                    if (
                        packet.type === EventType.SYSTEM_STATUS ||
                        packet.type === EventType.CONTROL_SESSION
                    ) {
                        if (packet.payload?.session_id) {
                            const newId = packet.payload.session_id;
                            if (newId > currentSessionIdRef.current) {
                                console.log(`[Gateway] New Session: ${newId}`);
                                currentSessionIdRef.current = newId;
                                // [Fix] Flush pending messages now that we have a session
                                flushQueue();
                            }
                        }
                        return;
                    }

                    // 5. Check Session Validity (Simple Client-Side Guard)
                    if (packet.session_id < currentSessionIdRef.current) {
                        // Ignore old packet
                        return;
                    }

                    // 6. Map to Logic
                    switch (packet.type) {
                        case EventType.BRAIN_THINKING:
                            // Mapped from "chat_start"
                            console.log(
                                "[Gateway] Brain Thinking...",
                                packet.payload
                            );
                            callbacksRef.current.onChatStart?.(
                                packet.payload?.mode || "proactive"
                            );
                            break;

                        case EventType.BRAIN_RESPONSE:
                            // Check for End Signal
                            if (packet.payload?.content) {
                                callbacksRef.current.onChatStream?.(
                                    packet.payload.content
                                );
                            } else {
                                // If empty payload, treating as end?
                            }
                            break;

                        case "brain_response_end":
                            console.log("[Gateway] Brain Response End");
                            callbacksRef.current.onChatEnd?.();
                            break;

                        case EventType.EMOTION_CHANGED:
                            // [Phase 32] Emotion event from backend Broker
                            if (packet.payload?.emotion) {
                                console.log(
                                    "[Gateway] Emotion:",
                                    packet.payload.emotion
                                );
                                callbacksRef.current.onEmotion?.(
                                    packet.payload.emotion
                                );
                                // Also dispatch to window for components that listen directly
                                window.dispatchEvent(
                                    new CustomEvent("lumina:emotion", {
                                        detail: {
                                            emotion: packet.payload.emotion,
                                        },
                                    })
                                );
                            }
                            break;

                        case "ui:register_widget":
                        case "ui:remove_widget":
                            // Bridge Backend UI Events -> Frontend Window Events
                            console.log(
                                `[Gateway] Bridging ${packet.type}`,
                                packet.payload
                            );
                            window.dispatchEvent(
                                new CustomEvent(packet.type, {
                                    detail: packet.payload,
                                })
                            );
                            break;

                        default:
                            break;
                    }
                } catch (e) {
                    // Ignore non-json
                    console.warn("[Gateway] Parse Error:", e, event.data);
                }
            };
        };

        connect();

        return () => {
            ws?.close();
            clearInterval(keepAliveTimer);
        };
    }, [baseUrl]); // Only reconnect if baseUrl changes

    const send = (type: string, payload: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            // [Fix] Check if session is ready
            if (currentSessionIdRef.current >= 0) {
                const packet: EventPacket = {
                    trace_id: crypto.randomUUID(),
                    session_id: currentSessionIdRef.current,
                    type,
                    source: "frontend",
                    payload,
                    timestamp: Date.now(),
                };
                wsRef.current.send(JSON.stringify(packet));
            } else {
                // Queue it
                console.warn(
                    `[Gateway] Session not ready (id=${currentSessionIdRef.current}), queueing message: ${type}`
                );
                pendingQueueRef.current.push({ type, payload });
            }
        } else {
            console.warn("[Gateway] Cannot send, WS not open");
        }
    };

    return { isConnected, send };
};
