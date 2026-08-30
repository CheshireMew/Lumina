import { describe, expect, it, vi } from "vitest";

import { dispatchGatewayEvent, GATEWAY_EVENT_TYPE } from "./gatewayProtocol";

describe("gatewayProtocol", () => {
    it("passes a structured, turn-scoped status to the UI", () => {
        const onSystemStatus = vi.fn();
        dispatchGatewayEvent(
            {
                trace_id: "trace",
                client_id: "client",
                turn_id: "turn-1",
                session_id: 1,
                generation: 1,
                sequence_number: 1,
                type: GATEWAY_EVENT_TYPE.SYSTEM_STATUS,
                source: "core.chat_turn",
                payload: {
                    status: "error",
                    code: "provider_unavailable",
                    message: "暂时无法连接模型服务，请稍后重试。",
                    scope: "turn",
                },
                timestamp: 0,
            },
            (dispatch) => dispatch({ onSystemStatus }),
        );

        expect(onSystemStatus).toHaveBeenCalledWith({
            status: "error",
            code: "provider_unavailable",
            message: "暂时无法连接模型服务，请稍后重试。",
            scope: "turn",
            turnId: "turn-1",
        });
    });
});
