import { useCallback, useEffect, useRef, useState } from "react";

import { listTtsModels, listTtsVoices } from "../../api/voiceApi";
import { VoiceOption } from "./types";
import { normalizeVoices } from "./utils";

export const useTtsVoiceState = (isActive: boolean, ttsBaseUrl: string) => {
    const [edgeVoices, setEdgeVoices] = useState<VoiceOption[]>([]);
    const [gptVoices, setGptVoices] = useState<VoiceOption[]>([]);
    const [activeTtsEngines, setActiveTtsEngines] = useState<string[]>([]);

    const hasWarnedTts = useRef(false);

    const refreshStatus = useCallback(async () => {
        try {
            const data = await listTtsModels(ttsBaseUrl);
            setActiveTtsEngines(data.active ? [data.active] : []);
            hasWarnedTts.current = false;

        } catch (error) {
            if (!hasWarnedTts.current) {
                console.warn("[VoiceManager] TTS service unavailable", error);
                hasWarnedTts.current = true;
            }
            setActiveTtsEngines([]);
        }
    }, [ttsBaseUrl]);

    const refreshVoices = useCallback(async () => {
        await refreshStatus();

        try {
            const data = await listTtsVoices(ttsBaseUrl);
            const voices = normalizeVoices(data);
            setEdgeVoices(voices);
            setGptVoices(voices);
        } catch (error) {
            setEdgeVoices([]);
            setGptVoices([]);
        }
    }, [refreshStatus]);

    useEffect(() => {
        if (!isActive) {
            return;
        }

        void refreshVoices();
    }, [isActive, refreshVoices]);

    return {
        edgeVoices,
        gptVoices,
        activeTtsEngines,
        refreshStatus,
        refreshVoices,
    };
};
