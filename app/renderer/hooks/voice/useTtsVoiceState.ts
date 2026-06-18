import { useCallback, useEffect, useRef, useState } from "react";

import { VoiceOption } from "./types";
import { normalizeVoices } from "./utils";

export const useTtsVoiceState = (isActive: boolean, ttsBaseUrl: string) => {
    const [edgeVoices, setEdgeVoices] = useState<VoiceOption[]>([]);
    const [gptVoices, setGptVoices] = useState<VoiceOption[]>([]);
    const [activeTtsEngines, setActiveTtsEngines] = useState<string[]>([]);

    const hasWarnedTts = useRef(false);

    const refreshStatus = useCallback(async () => {
        try {
            const response = await fetch(`${ttsBaseUrl}/models/list`);
            if (response.ok) {
                const data = await response.json();
                setActiveTtsEngines(data.active ? [data.active] : []);
                hasWarnedTts.current = false;
            }

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
            const response = await fetch(`${ttsBaseUrl}/voices`);
            if (!response.ok) {
                return;
            }

            const data = await response.json();
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
