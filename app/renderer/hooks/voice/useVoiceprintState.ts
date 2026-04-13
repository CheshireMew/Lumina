import { useCallback, useEffect, useState } from "react";

import { API_CONFIG } from "../../config";

export const useVoiceprintState = (
    isActive: boolean,
    currentAudioDevice: string | null,
) => {
    const [voiceprintEnabled, setVoiceprintEnabled] = useState(false);
    const [voiceprintThreshold, setVoiceprintThreshold] = useState(0.6);
    const [voiceprintProfile, setVoiceprintProfile] = useState("default");
    const [voiceprintStatus, setVoiceprintStatus] = useState("");
    const [voiceprintLoaded, setVoiceprintLoaded] = useState(false);
    const [vadStartThreshold, setVadStartThreshold] = useState(0.6);
    const [vadEndThreshold, setVadEndThreshold] = useState(0.05);

    const refreshVoiceprintConfig = useCallback(async () => {
        try {
            const voiceprintResponse = await fetch(
                `${API_CONFIG.STT_BASE_URL}/voiceprint/status`,
            );
            if (voiceprintResponse.ok) {
                const data = await voiceprintResponse.json();
                setVoiceprintEnabled(data.enabled || false);
                setVoiceprintThreshold(data.threshold || 0.6);
                setVoiceprintProfile(data.profile || "default");
                setVoiceprintLoaded(data.profile_loaded || false);
                setVoiceprintStatus(
                    data.profile_loaded ? "Loaded voiceprint" : "Voiceprint not registered",
                );
            }

            const audioStatusResponse = await fetch(
                `${API_CONFIG.STT_BASE_URL}/audio/status`,
            );
            if (audioStatusResponse.ok) {
                const data = await audioStatusResponse.json();
                if (data.speech_start_threshold !== undefined) {
                    setVadStartThreshold(data.speech_start_threshold);
                }
                if (data.speech_end_threshold !== undefined) {
                    setVadEndThreshold(data.speech_end_threshold);
                }
            }
        } catch (error) {
            console.warn("Failed to fetch voiceprint config", error);
        }
    }, []);

    const pushAudioConfig = useCallback(
        async (payload: Record<string, unknown>) => {
            await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
        },
        [],
    );

    const handleVoiceprintToggle = useCallback(
        async (enabled: boolean) => {
            try {
                await pushAudioConfig({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: enabled,
                    voiceprint_threshold: voiceprintThreshold,
                    voiceprint_profile: voiceprintProfile,
                });
                setVoiceprintEnabled(enabled);
            } catch (error) {
                alert("Unable to connect to the STT server");
            }
        },
        [currentAudioDevice, pushAudioConfig, voiceprintProfile, voiceprintThreshold],
    );

    const handleVoiceprintThresholdChange = useCallback(
        async (value: number) => {
            setVoiceprintThreshold(value);
            try {
                await pushAudioConfig({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: voiceprintEnabled,
                    voiceprint_threshold: value,
                    voiceprint_profile: voiceprintProfile,
                });
            } catch (error) {}
        },
        [currentAudioDevice, pushAudioConfig, voiceprintEnabled, voiceprintProfile],
    );

    const handleVadChange = useCallback(
        async (
            key: "speech_start_threshold" | "speech_end_threshold",
            value: number,
        ) => {
            if (key === "speech_start_threshold") {
                setVadStartThreshold(value);
            }
            if (key === "speech_end_threshold") {
                setVadEndThreshold(value);
            }

            try {
                await pushAudioConfig({ [key]: value });
            } catch (error) {}
        },
        [pushAudioConfig],
    );

    useEffect(() => {
        if (!isActive) {
            return;
        }

        void refreshVoiceprintConfig();
    }, [isActive, refreshVoiceprintConfig]);

    return {
        voiceprintEnabled,
        voiceprintThreshold,
        voiceprintProfile,
        voiceprintStatus,
        voiceprintLoaded,
        vadStartThreshold,
        vadEndThreshold,
        setVoiceprintProfile,
        handleVoiceprintToggle,
        handleVoiceprintThresholdChange,
        handleVadChange,
        refreshVoiceprintConfig,
    };
};
