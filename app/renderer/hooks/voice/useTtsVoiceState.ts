import { useCallback, useEffect, useRef, useState } from "react";

import { API_CONFIG } from "../../config";
import { VoiceOption } from "./types";
import { normalizeVoices } from "./utils";

export const useTtsVoiceState = (isActive: boolean) => {
    const [edgeVoices, setEdgeVoices] = useState<VoiceOption[]>([]);
    const [gptVoices, setGptVoices] = useState<VoiceOption[]>([]);
    const [activeTtsEngines, setActiveTtsEngines] = useState<string[]>([]);

    const hasWarnedTts = useRef(false);

    const refreshStatus = useCallback(async () => {
        try {
            const response = await fetch(`${API_CONFIG.TTS_BASE_URL}/models/list`);
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
    }, []);

    const refreshVoices = useCallback(async () => {
        await refreshStatus();

        try {
            const response = await fetch(`${API_CONFIG.TTS_BASE_URL}/voices`);
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
