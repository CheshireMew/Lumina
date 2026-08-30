import type { GatewayAck, GatewayEventPacket } from "./gatewayProtocol";

export interface PendingGatewayRequest {
    packet: GatewayEventPacket;
    expiresAt: number;
    timeoutId: number;
    resolve: (ack: GatewayAck) => void;
    reject: (error: Error) => void;
}

export class GatewayRequestQueue {
    private pending: PendingGatewayRequest[] = [];
    private inFlight = new Map<string, PendingGatewayRequest>();

    constructor(
        private readonly limit: number,
        private readonly timeoutMs: number,
    ) {}

    enqueue(packet: GatewayEventPacket, onQueued: () => void): Promise<GatewayAck> {
        if (this.pending.length + this.inFlight.size >= this.limit) {
            return Promise.reject(new Error("Gateway request queue is full"));
        }

        return new Promise<GatewayAck>((resolve, reject) => {
            const request: PendingGatewayRequest = {
                packet,
                expiresAt: Date.now() + this.timeoutMs,
                timeoutId: window.setTimeout(() => {
                    this.remove(packet.trace_id);
                    reject(new Error(`Gateway request timed out: ${packet.type}`));
                }, this.timeoutMs),
                resolve,
                reject,
            };
            this.pending.push(request);
            onQueued();
        });
    }

    dequeue(): PendingGatewayRequest | undefined {
        while (this.pending.length > 0) {
            const request = this.pending.shift();
            if (!request) continue;
            if (request.expiresAt > Date.now()) return request;
            window.clearTimeout(request.timeoutId);
            request.reject(
                new Error(`Gateway request expired: ${request.packet.type}`),
            );
        }
        return undefined;
    }

    markInFlight(request: PendingGatewayRequest): void {
        this.inFlight.set(request.packet.trace_id, request);
    }

    requeueInFlight(): void {
        this.pending.push(...this.inFlight.values());
        this.inFlight.clear();
    }

    resolveAck(packet: GatewayEventPacket): void {
        const requestId = String(packet.payload?.request_id || "");
        const request = this.inFlight.get(requestId);
        if (!request) return;

        this.inFlight.delete(requestId);
        window.clearTimeout(request.timeoutId);
        const status = String(packet.payload?.status || "rejected");
        const action = String(packet.payload?.action || request.packet.type);
        if (status === "accepted") {
            request.resolve({
                requestId,
                turnId: packet.turn_id || undefined,
                action,
                status: "accepted",
            });
            return;
        }
        request.reject(
            new Error(
                String(packet.payload?.details || `Gateway rejected ${action}`),
            ),
        );
    }

    rejectAll(error: Error): void {
        const requests = [...this.pending, ...this.inFlight.values()];
        this.pending = [];
        this.inFlight.clear();
        for (const request of requests) {
            window.clearTimeout(request.timeoutId);
            request.reject(error);
        }
    }

    private remove(requestId: string): void {
        this.inFlight.delete(requestId);
        this.pending = this.pending.filter(
            (request) => request.packet.trace_id !== requestId,
        );
    }
}
