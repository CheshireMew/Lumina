import { useCallback, useEffect, useRef, useState } from "react";

import {
    listAudioDevices,
    listSttModels,
    switchSttModel,
    updateSttAudioConfig,
} from "../../api/voiceApi";
import { AudioDevice, WhisperModelInfo } from "./types";

const normalizeModel = (model: Partial<WhisperModelInfo> & { desc?: string }) => {
    const id = String(model.id || model.name || "");
    return {
        id,
        name: String(model.name || id),
        description: model.description || model.desc || model.type || "",
        type: model.type,
        active: Boolean(model.active),
        download_status: model.download_status,
    } satisfies WhisperModelInfo;
};

export const useSttVoiceState = (isActive: boolean, sttBaseUrl: string) => {
    const [whisperModels, setWhisperModels] = useState<WhisperModelInfo[]>([]);
    const [currentWhisperModel, setCurrentWhisperModel] = useState("");
    const [loadingStatus, setLoadingStatus] = useState("idle");
    const [audioDevices, setAudioDevices] = useState<AudioDevice[]>([]);
    const [currentAudioDevice, setCurrentAudioDevice] = useState<string | null>(null);

    const hasWarnedStt = useRef(false);

    const refreshModels = useCallback(async () => {
        try {
            const data = await listSttModels(sttBaseUrl);
            const models: WhisperModelInfo[] = Array.isArray(data.models)
                ? data.models
                    .map((model: Partial<WhisperModelInfo> & { desc?: string }) =>
                        normalizeModel(model),
                    )
                    .filter((model: WhisperModelInfo) => model.id)
                : [];
            const activeModel = models.find((model) => model.active);
            setWhisperModels(models);
            setCurrentWhisperModel(
                activeModel?.id || data.active_model || data.current_model || "",
            );
            setLoadingStatus(data.loading_status || "idle");
        } catch (error) {
            console.error("Failed to fetch STT models", error);
        }
    }, [sttBaseUrl]);

    const refreshAudioDevices = useCallback(async () => {
        try {
            const data = await listAudioDevices(sttBaseUrl);
            setAudioDevices(data.devices || []);
            setCurrentAudioDevice(data.current || null);
            hasWarnedStt.current = false;
        } catch (error) {
            if (!hasWarnedStt.current) {
                console.warn("[VoiceManager] STT service unavailable", error);
                hasWarnedStt.current = true;
            }
        }
    }, [sttBaseUrl]);

    const handleSttModelChange = useCallback(
        async (newModel: string) => {
            try {
                const data = await switchSttModel(sttBaseUrl, newModel);
                if (data.status && data.status !== "ok") {
                    throw new Error(data.detail || "Model switch failed");
                }
                setCurrentWhisperModel(newModel);
                setLoadingStatus("loading");
                await refreshModels();
            } catch (error) {
                console.error("[VoiceManager] Failed to switch STT model", error);
                alert("Failed to confirm model switch");
                await refreshModels();
            }
        },
        [refreshModels, sttBaseUrl],
    );

    const handleAudioDeviceChange = useCallback(async (deviceName: string) => {
        try {
            await updateSttAudioConfig(sttBaseUrl, { device_name: deviceName });
            setCurrentAudioDevice(deviceName);
            await refreshAudioDevices();
        } catch (error) {
            console.error("[VoiceManager] Failed to switch audio device", error);
            alert("Failed to connect to STT server");
        }
    }, [refreshAudioDevices, sttBaseUrl]);

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
        audioDevices,
        currentAudioDevice,
        handleSttModelChange,
        handleAudioDeviceChange,
        refreshModels,
        refreshAudioDevices,
    };
};
