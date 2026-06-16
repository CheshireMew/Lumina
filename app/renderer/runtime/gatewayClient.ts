import { API_CONFIG } from "../config";
import { useChatStore } from "../store/useChatStore";
import { emitRuntimeEvent } from "./events";

export interface GatewayEventPacket {
    trace_id: string;
    session_id: number;
    sequence_number: number;
    type: string;
    source: string;
    payload: any;
    timestamp: number;
}

export interface GatewaySubscriber {
    onChatStart?: (mode: string) => void;
    onChatStream?: (content: string) => void;
    onChatEnd?: () => void;
    onEmotion?: (emotion: string) => void;
    onSessionReset?: (sessionId: number) => void;
}

const EVENT_TYPE = {
    BRAIN_THINKING: "brain_thinking",
    BRAIN_RESPONSE: "brain_response",
    BRAIN_RESPONSE_END: "brain_response_end",
    SYSTEM_STATUS: "system_status",
    CONTROL_SESSION: "control_session",
    EMOTION_CHANGED: "emotion:changed",
} as const;

class GatewayClient {
    private socket: WebSocket | null = null;
    private wsUrl: string | null = null;
    private keepAliveTimer: number | null = null;
    private reconnectTimer: number | null = null;
    private currentSessionId = 0;
    private lastSequence = -1;
    private pendingQueue: Array<{ type: string; payload: any }> = [];
    private subscribers = new Set<GatewaySubscriber>();
    private shouldReconnect = false;

    subscribe(subscriber: GatewaySubscriber): () => void {
        this.subscribers.add(subscriber);
        return () => {
            this.subscribers.delete(subscriber);
        };
    }

    connect(baseUrl: string = API_CONFIG.BASE_URL): void {
        const nextWsUrl = baseUrl.replace("http", "ws") + "/lumina/gateway/ws";
        this.shouldReconnect = true;

        if (
            this.socket &&
            this.wsUrl === nextWsUrl &&
            (this.socket.readyState === WebSocket.OPEN ||
                this.socket.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }

        this.replaceSocket(nextWsUrl);
    }

    disconnect(): void {
        this.shouldReconnect = false;
        this.clearTimers();
        this.teardownSocket();
        useChatStore.getState().setConnection(false);
    }

    send(type: string, payload: any): void {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(
                JSON.stringify(this.createPacket(type, payload)),
            );
            return;
        }

        this.pendingQueue.push({ type, payload });
    }

    private replaceSocket(nextWsUrl: string): void {
        this.clearTimers();
        this.teardownSocket();

        this.wsUrl = nextWsUrl;
        const socket = new WebSocket(nextWsUrl);
        this.socket = socket;

        socket.onopen = () => {
            if (this.socket !== socket) {
                return;
            }

            useChatStore.getState().setConnection(true);
            this.flushQueue();
            this.keepAliveTimer = window.setInterval(() => {
                if (this.socket?.readyState === WebSocket.OPEN) {
                    this.socket.send("ping");
                }
            }, 30000);
        };

        socket.onclose = () => {
            if (this.socket !== socket) {
                return;
            }

            this.clearTimers();
            this.socket = null;
            useChatStore.getState().setConnection(false);

            if (this.shouldReconnect && this.wsUrl) {
                this.reconnectTimer = window.setTimeout(() => {
                    if (this.wsUrl) {
                        this.replaceSocket(this.wsUrl);
                    }
                }, 3000);
            }
        };

        socket.onerror = (error) => {
            console.warn("[Gateway] Error:", error);
        };

        socket.onmessage = (event) => {
            if (this.socket !== socket) {
                return;
            }
            this.handleMessage(event.data);
        };
    }

    private teardownSocket(): void {
        if (!this.socket) {
            return;
        }

        const socket = this.socket;
        socket.onopen = null;
        socket.onclose = null;
        socket.onerror = null;
        socket.onmessage = null;

        if (
            socket.readyState === WebSocket.OPEN ||
            socket.readyState === WebSocket.CONNECTING
        ) {
            socket.close();
        }

        this.socket = null;
    }

    private clearTimers(): void {
        if (this.keepAliveTimer !== null) {
            window.clearInterval(this.keepAliveTimer);
            this.keepAliveTimer = null;
        }

        if (this.reconnectTimer !== null) {
            window.clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    private flushQueue(): void {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return;
        }

        while (this.pendingQueue.length > 0) {
            const item = this.pendingQueue.shift();
            if (!item) {
                continue;
            }
            this.socket.send(JSON.stringify(this.createPacket(item.type, item.payload)));
        }
    }

    private createPacket(type: string, payload: any): GatewayEventPacket {
        return {
            trace_id: crypto.randomUUID(),
            session_id: this.currentSessionId,
            sequence_number: 0,
            type,
            source: "frontend",
            payload,
            timestamp: Date.now(),
        };
    }

    private handleMessage(rawData: string): void {
        try {
            if (rawData === "pong") {
                return;
            }

            const packet: GatewayEventPacket = JSON.parse(rawData);

            if (
                packet.session_id > this.currentSessionId
            ) {
                this.lastSequence = -1;
            } else if (
                packet.session_id === this.currentSessionId &&
                packet.sequence_number <= this.lastSequence
            ) {
                return;
            }

            this.lastSequence = packet.sequence_number;

            if (
                packet.type === EVENT_TYPE.SYSTEM_STATUS ||
                packet.type === EVENT_TYPE.CONTROL_SESSION
            ) {
                this.handleSessionPacket(packet);
                return;
            }

            if (packet.session_id < this.currentSessionId) {
                return;
            }

            switch (packet.type) {
                case EVENT_TYPE.BRAIN_THINKING:
                    this.notify((subscriber) =>
                        subscriber.onChatStart?.(packet.payload?.mode || "proactive"),
                    );
                    break;
                case EVENT_TYPE.BRAIN_RESPONSE:
                    if (packet.payload?.content) {
                        this.notify((subscriber) =>
                            subscriber.onChatStream?.(packet.payload.content),
                        );
                    }
                    break;
                case EVENT_TYPE.BRAIN_RESPONSE_END:
                    this.notify((subscriber) => subscriber.onChatEnd?.());
                    break;
                case EVENT_TYPE.EMOTION_CHANGED:
                    if (packet.payload?.emotion) {
                        const emotion = packet.payload.emotion;
                        useChatStore.getState().setEmotion(emotion);
                        this.notify((subscriber) =>
                            subscriber.onEmotion?.(emotion),
                        );
                        emitRuntimeEvent("emotion", { emotion });
                    }
                    break;
            }
        } catch (error) {
            console.warn("[Gateway] Parse Error:", error);
        }
    }

    private handleSessionPacket(packet: GatewayEventPacket): void {
        const nextSessionId = packet.payload?.session_id;
        if (!nextSessionId || nextSessionId <= this.currentSessionId) {
            return;
        }

        this.currentSessionId = nextSessionId;
        useChatStore.getState().setSessionId(nextSessionId);

        if (packet.type === EVENT_TYPE.CONTROL_SESSION) {
            this.notify((subscriber) =>
                subscriber.onSessionReset?.(nextSessionId),
            );
        }

        this.flushQueue();
    }

    private notify(dispatch: (subscriber: GatewaySubscriber) => void): void {
        this.subscribers.forEach((subscriber) => dispatch(subscriber));
    }
}

export const gatewayClient = new GatewayClient();
