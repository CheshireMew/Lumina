import { GatewayRequestQueue } from "./gatewayRequestQueue";
import {
    dispatchGatewayEvent,
    GATEWAY_EVENT_TYPE,
    type GatewayAck,
    type GatewayEventPacket,
    type GatewayPayload,
    type GatewaySubscriber,
} from "./gatewayProtocol";

export type { GatewayAck, GatewayEventPacket, GatewaySubscriber } from "./gatewayProtocol";

const QUEUE_LIMIT = 100;
const REQUEST_TIMEOUT_MS = 15_000;

class GatewayClient {
    private socket: WebSocket | null = null;
    private baseUrl: string | null = null;
    private keepAliveTimer: number | null = null;
    private reconnectTimer: number | null = null;
    private currentSessionId = 1;
    private currentGeneration = 1;
    private lastSequence = 0;
    private readonly requests = new GatewayRequestQueue(
        QUEUE_LIMIT,
        REQUEST_TIMEOUT_MS,
    );
    private subscribers = new Set<GatewaySubscriber>();
    private shouldReconnect = false;
    private protocolReady = false;
    private readonly clientId = this.loadClientId();

    subscribe(subscriber: GatewaySubscriber): () => void {
        this.subscribers.add(subscriber);
        return () => {
            this.subscribers.delete(subscriber);
        };
    }

    connect(baseUrl: string): void {
        this.shouldReconnect = true;
        this.baseUrl = baseUrl;

        if (
            this.socket &&
            (this.socket.readyState === WebSocket.OPEN ||
                this.socket.readyState === WebSocket.CONNECTING)
        ) {
            return;
        }

        this.replaceSocket();
    }

    disconnect(): void {
        this.shouldReconnect = false;
        this.clearTimers();
        this.teardownSocket();
        this.requests.rejectAll(new Error("Gateway disconnected"));
        this.notify((subscriber) => subscriber.onConnection?.(false));
    }

    send(
        type: string,
        payload: GatewayPayload,
        turnId?: string,
    ): Promise<GatewayAck> {
        const packet = this.createPacket(type, payload, turnId);
        return this.requests.enqueue(packet, () => this.flushQueue());
    }

    private replaceSocket(): void {
        if (!this.baseUrl) {
            return;
        }
        this.clearTimers();
        this.teardownSocket();
        this.protocolReady = false;

        const url = new URL("/lumina/gateway/ws", this.baseUrl);
        url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
        url.searchParams.set("client_id", this.clientId);
        const socket = new WebSocket(url.toString());
        this.socket = socket;

        socket.onopen = () => {
            if (this.socket !== socket) {
                return;
            }

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
            this.protocolReady = false;
            this.requests.requeueInFlight();
            this.notify((subscriber) => subscriber.onConnection?.(false));

            if (this.shouldReconnect && this.baseUrl) {
                this.reconnectTimer = window.setTimeout(() => {
                    this.replaceSocket();
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
        if (
            !this.protocolReady ||
            !this.socket ||
            this.socket.readyState !== WebSocket.OPEN
        ) {
            return;
        }

        let request = this.requests.dequeue();
        while (request) {
            request.packet.session_id = this.currentSessionId;
            request.packet.generation = this.currentGeneration;
            request.packet.client_id = this.clientId;
            this.requests.markInFlight(request);
            this.socket.send(JSON.stringify(request.packet));
            request = this.requests.dequeue();
        }
    }

    private createPacket(
        type: string,
        payload: GatewayPayload,
        turnId?: string,
    ): GatewayEventPacket {
        return {
            trace_id: crypto.randomUUID(),
            client_id: this.clientId,
            turn_id: turnId,
            session_id: this.currentSessionId,
            generation: this.currentGeneration,
            sequence_number: 0,
            type,
            source: "frontend",
            payload,
            timestamp: Date.now() / 1000,
        };
    }

    private handleMessage(rawData: string): void {
        try {
            if (rawData === "pong") {
                return;
            }

            const packet = JSON.parse(rawData) as GatewayEventPacket;
            if (!packet || typeof packet !== "object" || !packet.type) {
                throw new Error("Invalid gateway packet");
            }

            if (packet.type === GATEWAY_EVENT_TYPE.CONTROL_SESSION) {
                this.handleSessionPacket(packet);
                return;
            }

            if (
                packet.client_id !== this.clientId ||
                packet.session_id !== this.currentSessionId ||
                packet.generation !== this.currentGeneration ||
                packet.sequence_number <= this.lastSequence
            ) {
                return;
            }
            this.lastSequence = packet.sequence_number;

            if (packet.type === GATEWAY_EVENT_TYPE.CONTROL_ACK) {
                this.requests.resolveAck(packet);
                return;
            }
            dispatchGatewayEvent(packet, (dispatch) => this.notify(dispatch));
        } catch (error) {
            console.warn("[Gateway] Parse Error:", error);
        }
    }

    private handleSessionPacket(packet: GatewayEventPacket): void {
        const nextSessionId = Number(packet.payload?.session_id || packet.session_id);
        const nextGeneration = Number(
            packet.payload?.generation || packet.generation,
        );
        const action = String(packet.payload?.action || "");
        if (!nextSessionId || !nextGeneration) {
            return;
        }

        if (
            this.protocolReady &&
            (nextSessionId < this.currentSessionId ||
                nextGeneration < this.currentGeneration)
        ) {
            return;
        }

        this.currentSessionId = nextSessionId;
        this.currentGeneration = nextGeneration;
        this.lastSequence = packet.sequence_number;
        this.protocolReady = true;
        this.notify((subscriber) => subscriber.onConnection?.(true));

        if (action === "reset") {
            this.notify((subscriber) =>
                subscriber.onSessionReset?.(nextSessionId, nextGeneration),
            );
        }

        this.notify((subscriber) =>
            subscriber.onReady?.(this.clientId, nextSessionId, nextGeneration),
        );

        this.flushQueue();
    }

    private loadClientId(): string {
        const key = "lumina.gateway.client-id";
        try {
            const existing = window.sessionStorage.getItem(key);
            if (existing) return existing;
            const created = crypto.randomUUID();
            window.sessionStorage.setItem(key, created);
            return created;
        } catch {
            return crypto.randomUUID();
        }
    }

    private notify(dispatch: (subscriber: GatewaySubscriber) => void): void {
        this.subscribers.forEach((subscriber) => dispatch(subscriber));
    }
}

export const gatewayClient = new GatewayClient();
