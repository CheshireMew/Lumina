import { emitRuntimeEvent } from "./events";

export type GatewayPayload = Record<string, unknown>;

export interface GatewayEventPacket {
    trace_id: string;
    client_id: string;
    turn_id?: string | null;
    session_id: number;
    generation: number;
    sequence_number: number;
    type: string;
    source: string;
    payload: GatewayPayload;
    timestamp: number;
}

export interface GatewayAck {
    requestId: string;
    turnId?: string;
    action: string;
    status: "accepted";
}

export interface GatewaySystemStatus {
    status: string;
    code: string;
    message: string;
    scope: string;
    turnId?: string;
}

export interface GatewaySubscriber {
    onConnection?: (connected: boolean) => void;
    onReady?: (clientId: string, sessionId: number, generation: number) => void;
    onChatStart?: (turnId: string, mode: string) => void;
    onChatStream?: (turnId: string, content: string) => void;
    onChatReasoning?: (turnId: string, content: string) => void;
    onChatEnd?: (turnId: string, status: string) => void;
    onEmotion?: (emotion: string) => void;
    onSessionReset?: (sessionId: number, generation: number) => void;
    onSystemStatus?: (status: GatewaySystemStatus) => void;
}

export const GATEWAY_EVENT_TYPE = {
    BRAIN_THINKING: "brain_thinking",
    BRAIN_RESPONSE: "brain_response",
    BRAIN_REASONING: "brain_reasoning",
    BRAIN_RESPONSE_END: "brain_response_end",
    CONTROL_ACK: "control_ack",
    SYSTEM_STATUS: "system_status",
    CONTROL_SESSION: "control_session",
    EMOTION_CHANGED: "emotion:changed",
} as const;

type NotifyGatewaySubscriber = (
    dispatch: (subscriber: GatewaySubscriber) => void,
) => void;

export function dispatchGatewayEvent(
    packet: GatewayEventPacket,
    notify: NotifyGatewaySubscriber,
): void {
    if (packet.type === GATEWAY_EVENT_TYPE.SYSTEM_STATUS) {
        notify((subscriber) =>
            subscriber.onSystemStatus?.({
                status: String(packet.payload?.status || ""),
                code: String(packet.payload?.code || "response_failed"),
                message: String(packet.payload?.message || "回复生成失败，请重试。"),
                scope: String(packet.payload?.scope || "application"),
                turnId: packet.turn_id || undefined,
            }),
        );
        return;
    }

    const turnId = packet.turn_id || "";
    switch (packet.type) {
        case GATEWAY_EVENT_TYPE.BRAIN_THINKING:
            if (turnId) {
                notify((subscriber) =>
                    subscriber.onChatStart?.(
                        turnId,
                        String(packet.payload?.mode || "chat"),
                    ),
                );
            }
            break;
        case GATEWAY_EVENT_TYPE.BRAIN_RESPONSE:
            if (turnId && packet.payload?.content) {
                notify((subscriber) =>
                    subscriber.onChatStream?.(
                        turnId,
                        String(packet.payload.content),
                    ),
                );
            }
            break;
        case GATEWAY_EVENT_TYPE.BRAIN_REASONING:
            if (turnId && packet.payload?.content) {
                notify((subscriber) =>
                    subscriber.onChatReasoning?.(
                        turnId,
                        String(packet.payload.content),
                    ),
                );
            }
            break;
        case GATEWAY_EVENT_TYPE.BRAIN_RESPONSE_END:
            if (turnId) {
                notify((subscriber) =>
                    subscriber.onChatEnd?.(
                        turnId,
                        String(packet.payload?.status || "completed"),
                    ),
                );
            }
            break;
        case GATEWAY_EVENT_TYPE.EMOTION_CHANGED:
            if (packet.payload?.emotion) {
                const emotion = String(packet.payload.emotion);
                notify((subscriber) => subscriber.onEmotion?.(emotion));
                emitRuntimeEvent("emotion", { emotion });
            }
            break;
    }
}
