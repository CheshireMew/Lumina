export interface CompanionTransport {
    send: (type: string, payload: Record<string, unknown>) => void;
}

export interface SendCompanionMessageInput {
    text: string;
    characterId?: string;
    userName?: string;
    model?: string;
}

export interface ResetCompanionSessionInput {
    characterId?: string;
    userName?: string;
}

export const companionClient = {
    sendMessage(
        transport: CompanionTransport,
        input: SendCompanionMessageInput,
    ): void {
        transport.send("input_text", {
            text: input.text,
            character_id: input.characterId,
            user_name: input.userName,
            model: input.model,
        });
    },

    interrupt(transport: CompanionTransport): void {
        transport.send("control_interrupt", {
            action: "interrupt",
        });
    },

    resetSession(
        transport: CompanionTransport,
        input: ResetCompanionSessionInput,
    ): void {
        transport.send("control_session", {
            action: "reset",
            character_id: input.characterId,
            user_name: input.userName,
        });
    },
};
