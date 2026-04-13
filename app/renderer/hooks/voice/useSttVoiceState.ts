import { useCallback, useEffect, useRef, useState } from "react";

import { API_CONFIG } from "../../config";
import { AudioDevice, WhisperModelInfo } from "./types";

export const useSttVoiceState = (isActive: boolean) => {
    const [whisperModels, setWhisperModels] = useState<WhisperModelInfo[]>([]);
    const [currentWhisperModel, setCurrentWhisperModel] = useState("base");
    const [loadingStatus, setLoadingStatus] = useState("idle");
    const [sttEngineType, setSttEngineType] = useState("faster_whisper");
    const [audioDevices, setAudioDevices] = useState<AudioDevice[]>([]);
    const [currentAudioDevice, setCurrentAudioDevice] = useState<string | null>(null);

    const hasWarnedStt = useRef(false);

    const refreshModels = useCallback(async () => {
        try {
            const response = await fetch(`${API_CONFIG.STT_BASE_URL}/models/list`);
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            setWhisperModels(data.models || []);
            setCurrentWhisperModel(data.current_model || data.active_model || "base");
            setSttEngineType(data.engine_type || "faster_whisper");
            setLoadingStatus(data.loading_status || "idle");
        } catch (error) {
            console.error("Failed to fetch STT models", error);
        }
    }, []);

    const refreshAudioDevices = useCallback(async () => {
        try {
            const response = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/devices`);
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            setAudioDevices(data.devices || []);
            setCurrentAudioDevice(data.current || null);
            hasWarnedStt.current = false;
        } catch (error) {
            if (!hasWarnedStt.current) {
                console.warn("[VoiceManager] STT service unavailable", error);
                hasWarnedStt.current = true;
            }
        }
    }, []);

    const handleSttModelChange = useCallback(
        async (newModel: string) => {
            try {
                await fetch(`${API_CONFIG.STT_BASE_URL}/models/switch`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ model_name: newModel }),
                });
                setLoadingStatus("loading");
                await refreshModels();
            } catch (error) {
                alert("Failed to confirm model switch");
            }
        },
        [refreshModels],
    );

    const handleEngineChange = useCallback(
        async (newEngine: string) => {
            setSttEngineType(newEngine);

            let targetModel = "base";
            if (newEngine === "sense_voice") {
                targetModel = "sense-voice";
            } else if (newEngine === "paraformer_zh") {
                targetModel = "paraformer-zh";
            } else if (newEngine === "paraformer_en") {
                targetModel = "paraformer-en";
            }

            await handleSttModelChange(targetModel);
        },
        [handleSttModelChange],
    );

    const handleAudioDeviceChange = useCallback(async (deviceName: string) => {
        try {
            const response = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_name: deviceName }),
            });
            if (!response.ok) {
                alert("Failed to switch audio device");
                return;
            }
            setCurrentAudioDevice(deviceName);
        } catch (error) {
            alert("Failed to connect to STT server");
        }
    }, []);

    useEffect(() => {
        if (!isActive) {
            return;
        }

        void refreshModels();
        void refreshAudioDevices();

        const interval = setInterval(() => {
            void refreshModels();
        }, 2000);
        return () => clearInterval(interval);
    }, [isActive, refreshAudioDevices, refreshModels]);

    return {
        whisperModels,
        currentWhisperModel,
        loadingStatus,
        sttEngineType,
        audioDevices,
        currentAudioDevice,
        handleSttModelChange,
        handleEngineChange,
        handleAudioDeviceChange,
        refreshModels,
        refreshAudioDevices,
    };
};
