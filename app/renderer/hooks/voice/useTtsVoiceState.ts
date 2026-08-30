import { useCallback, useEffect, useRef, useState } from "react";

import { listTtsModels, listTtsVoices } from "../../api/voiceApi";
import { VoiceOption } from "./types";
import { normalizeVoices } from "./utils";

export const useTtsVoiceState = (isActive: boolean, ttsBaseUrl: string) => {
    const [activeTtsEngines, setActiveTtsEngines] = useState<string[]>([]);
    const [ttsEngines, setTtsEngines] = useState<{ id: string; name: string }[]>([]);
    const [voicesByEngine, setVoicesByEngine] = useState<Record<string, VoiceOption[]>>({});
    const [ttsLoadState, setTtsLoadState] = useState<"loading" | "ready" | "error">("loading");
    const [ttsError, setTtsError] = useState("");

    const hasWarnedTts = useRef(false);

    const refreshStatus = useCallback(async () => {
        setTtsLoadState((current) => current === "ready" ? current : "loading");
        try {
            const data = await listTtsModels(ttsBaseUrl);
            setActiveTtsEngines(data.active ? [data.active] : []);
            setTtsEngines(
                Array.isArray(data.engines)
                    ? data.engines.map((engine: { id: string; name?: string }) => ({
                        id: engine.id,
                        name: engine.name || engine.id,
                    }))
                    : [],
            );
            hasWarnedTts.current = false;
            setTtsLoadState("ready");
            setTtsError("");

        } catch (error) {
            if (!hasWarnedTts.current) {
                console.warn("[VoiceManager] TTS service unavailable", error);
                hasWarnedTts.current = true;
            }
            setActiveTtsEngines([]);
            setTtsEngines([]);
            setTtsLoadState("error");
            setTtsError("语音合成服务暂时不可用，请稍后重试。 ");
        }
    }, [ttsBaseUrl]);

    const refreshVoices = useCallback(async () => {
        await refreshStatus();

        try {
            const models = await listTtsModels(ttsBaseUrl);
            const engines: { id: string; name?: string }[] = Array.isArray(models.engines)
                ? models.engines
                : [];
            const entries = await Promise.all(
                engines.map(async (engine) => [
                    engine.id,
                    normalizeVoices(await listTtsVoices(ttsBaseUrl, engine.id)),
                ] as const),
            );
            const byEngine = Object.fromEntries(entries);
            setVoicesByEngine(byEngine);
        } catch (error) {
            setVoicesByEngine({});
            setTtsLoadState("error");
            setTtsError("声音列表读取失败，请确认语音合成服务已启动。 ");
        }
    }, [refreshStatus]);

    useEffect(() => {
        if (!isActive) {
            return;
        }

        void refreshVoices();
    }, [isActive, refreshVoices]);

    return {
        activeTtsEngines,
        ttsEngines,
        voicesByEngine,
        ttsLoadState,
        ttsError,
        refreshStatus,
        refreshVoices,
    };
};
