import { useCallback, useEffect, useState } from "react";

export const useVoiceprintState = (
    isActive: boolean,
    currentAudioDevice: string | null,
    sttBaseUrl: string,
) => {
    const [voiceprintEnabled, setVoiceprintEnabled] = useState(false);
    const [voiceprintThreshold, setVoiceprintThreshold] = useState(0);
    const [voiceprintProfile, setVoiceprintProfile] = useState("");
    const [voiceprintStatus, setVoiceprintStatus] = useState("");
    const [voiceprintLoaded, setVoiceprintLoaded] = useState(false);
    const [vadStartThreshold, setVadStartThreshold] = useState(0);
    const [vadEndThreshold, setVadEndThreshold] = useState(0);

    const refreshVoiceprintConfig = useCallback(async () => {
        try {
            const voiceprintResponse = await fetch(
                `${sttBaseUrl}/voiceprint/status`,
            );
            if (voiceprintResponse.ok) {
                const data = await voiceprintResponse.json();
                setVoiceprintEnabled(data.enabled ?? false);
                setVoiceprintThreshold(data.threshold ?? 0);
                setVoiceprintProfile(data.profile ?? "");
                setVoiceprintLoaded(data.profile_loaded ?? false);
                setVoiceprintStatus(
                    data.profile_loaded ? "Loaded voiceprint" : "Voiceprint not registered",
                );
            }

            const audioStatusResponse = await fetch(
                `${sttBaseUrl}/audio/status`,
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
    }, [sttBaseUrl]);

    const pushAudioConfig = useCallback(
        async (payload: Record<string, unknown>) => {
            await fetch(`${sttBaseUrl}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
        },
        [sttBaseUrl],
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
