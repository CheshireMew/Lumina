export interface CompanionTransport {
    send: (
        type: string,
        payload: Record<string, unknown>,
        turnId?: string,
    ) => Promise<unknown>;
}

export interface SendCompanionMessageInput {
    text: string;
    characterId?: string;
    userName?: string;
    model?: string;
    turnId: string;
}

export interface ResetCompanionSessionInput {
    characterId?: string;
    userName?: string;
}

export type CompanionHistoryDto = components["schemas"]["CompanionHistoryResponse"];

export const companionClient = {
    sendMessage(
        transport: CompanionTransport,
        input: SendCompanionMessageInput,
    ): Promise<unknown> {
        return transport.send("input_text", {
            text: input.text,
            character_id: input.characterId,
            user_name: input.userName,
            model: input.model,
        }, input.turnId);
    },

    interrupt(transport: CompanionTransport, turnId?: string): Promise<unknown> {
        return transport.send("control_interrupt", {
            action: "interrupt",
            turn_id: turnId,
        }, turnId);
    },

    resetSession(
        transport: CompanionTransport,
        input: ResetCompanionSessionInput,
    ): Promise<unknown> {
        return transport.send("control_session", {
            action: "reset",
            character_id: input.characterId,
            user_name: input.userName,
        });
    },

    fetchHistory(
        baseUrl: string,
        input: {
            characterId?: string;
            userName?: string;
            sessionId: number;
        },
    ): Promise<CompanionHistoryDto> {
        const url = new URL("/companion/history", baseUrl);
        if (input.characterId) {
            url.searchParams.set("character_id", input.characterId);
        }
        if (input.userName) {
            url.searchParams.set("user_name", input.userName);
        }
        url.searchParams.set("session_id", String(input.sessionId));
        return requestJson<CompanionHistoryDto>(url.toString());
    },
};
import type { components } from "../../types/api-schema";
import { requestJson } from "../../api/client";
