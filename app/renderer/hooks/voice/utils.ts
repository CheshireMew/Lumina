import { VoiceOption } from "./types";

export const normalizeVoices = (payload: any): VoiceOption[] => {
    if (Array.isArray(payload)) {
        return payload;
    }

    if (Array.isArray(payload?.voices)) {
        return payload.voices;
    }

    return [...(payload?.chinese || []), ...(payload?.english || [])];
};
