import { VoiceOption } from "./types";

const isVoiceOption = (value: unknown): value is VoiceOption => (
    typeof value === "object"
    && value !== null
    && "name" in value
    && typeof value.name === "string"
);

export const normalizeVoices = (payload: unknown): VoiceOption[] => {
    if (Array.isArray(payload)) {
        return payload.filter(isVoiceOption);
    }

    if (!payload || typeof payload !== "object") return [];
    const record = payload as Record<string, unknown>;
    if (Array.isArray(record.voices)) {
        return record.voices.filter(isVoiceOption);
    }

    return [
        ...(Array.isArray(record.chinese) ? record.chinese : []),
        ...(Array.isArray(record.english) ? record.english : []),
    ].filter(isVoiceOption);
};
