import { useCallback, useEffect, useState } from "react";
import {
    getAudioStatus,
    getVoiceprintStatus,
    updateSttAudioConfig,
} from "../../api/voiceApi";

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
    const [vadAggressiveness, setVadAggressiveness] = useState(3);
    const [vadStartThreshold, setVadStartThreshold] = useState(0);
    const [vadEndThreshold, setVadEndThreshold] = useState(0);

    const refreshVoiceprintConfig = useCallback(async () => {
        try {
            const voiceprint = await getVoiceprintStatus(sttBaseUrl);
            const profileLoaded = voiceprint.profile_loaded ?? false;
            let effectiveEnabled = (voiceprint.enabled ?? false) && profileLoaded;
            if (voiceprint.enabled && !profileLoaded) {
                try {
                    await updateSttAudioConfig(sttBaseUrl, {
                        enable_voiceprint_filter: false,
                    });
                } catch (error) {
                    console.warn("Failed to repair invalid voiceprint setting", error);
                }
                effectiveEnabled = false;
            }
            setVoiceprintEnabled(effectiveEnabled);
            setVoiceprintThreshold(voiceprint.threshold ?? 0);
            setVoiceprintProfile(voiceprint.profile ?? "");
            setVoiceprintLoaded(profileLoaded);
            setVoiceprintStatus(
                voiceprint.profile_loaded
                    ? `声纹“${voiceprint.profile}”已就绪`
                    : voiceprint.profile
                        ? `声纹“${voiceprint.profile}”尚未注册或未启用`
                        : "请先注册并选择一个已启用声纹",
            );

            const audioStatus = await getAudioStatus(sttBaseUrl);
            if (audioStatus.vad_aggressiveness != null) {
                setVadAggressiveness(audioStatus.vad_aggressiveness);
            }
            if (audioStatus.speech_start_threshold !== undefined) {
                setVadStartThreshold(audioStatus.speech_start_threshold);
            }
            if (audioStatus.speech_end_threshold !== undefined) {
                setVadEndThreshold(audioStatus.speech_end_threshold);
            }
        } catch (error) {
            console.warn("Failed to fetch voiceprint config", error);
            setVoiceprintStatus(error instanceof Error ? error.message : "声纹状态读取失败。 ");
            setVoiceprintLoaded(false);
        }
    }, [sttBaseUrl]);

    const pushAudioConfig = useCallback(
        async (payload: Record<string, unknown>) => {
            await updateSttAudioConfig(sttBaseUrl, payload);
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
                await refreshVoiceprintConfig();
            } catch (error) {
                console.error("[VoiceManager] Failed to update voiceprint toggle", error);
                setVoiceprintStatus(error instanceof Error ? error.message : "声纹过滤设置失败。 ");
                await refreshVoiceprintConfig();
            }
        },
        [
            currentAudioDevice,
            pushAudioConfig,
            refreshVoiceprintConfig,
            voiceprintProfile,
            voiceprintThreshold,
        ],
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
                await refreshVoiceprintConfig();
            } catch (error) {
                console.error("[VoiceManager] Failed to update voiceprint threshold", error);
                setVoiceprintStatus(error instanceof Error ? error.message : "声纹阈值保存失败。 ");
                await refreshVoiceprintConfig();
            }
        },
        [
            currentAudioDevice,
            pushAudioConfig,
            refreshVoiceprintConfig,
            voiceprintEnabled,
            voiceprintProfile,
        ],
    );

    const handleVoiceprintProfileChange = useCallback(
        async (profile: string) => {
            setVoiceprintProfile(profile);
            try {
                await pushAudioConfig({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: voiceprintEnabled,
                    voiceprint_threshold: voiceprintThreshold,
                    voiceprint_profile: profile,
                });
                await refreshVoiceprintConfig();
            } catch (error) {
                console.error("[VoiceManager] Failed to update voiceprint profile", error);
                setVoiceprintStatus(error instanceof Error ? error.message : "当前声纹保存失败。 ");
                await refreshVoiceprintConfig();
            }
        },
        [
            currentAudioDevice,
            pushAudioConfig,
            refreshVoiceprintConfig,
            voiceprintEnabled,
            voiceprintThreshold,
        ],
    );

    const handleVadChange = useCallback(
        async (
            key: "vad_aggressiveness" | "speech_start_threshold" | "speech_end_threshold",
            value: number,
        ) => {
            if (key === "vad_aggressiveness") {
                setVadAggressiveness(value);
            }
            if (key === "speech_start_threshold") {
                setVadStartThreshold(value);
            }
            if (key === "speech_end_threshold") {
                setVadEndThreshold(value);
            }

            try {
                await pushAudioConfig({ [key]: value });
                await refreshVoiceprintConfig();
            } catch (error) {
                console.error("[VoiceManager] Failed to update VAD setting", error);
                setVoiceprintStatus(error instanceof Error ? error.message : "语音检测设置保存失败。 ");
                await refreshVoiceprintConfig();
            }
        },
        [pushAudioConfig, refreshVoiceprintConfig],
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
        vadAggressiveness,
        vadStartThreshold,
        vadEndThreshold,
        handleVoiceprintProfileChange,
        handleVoiceprintToggle,
        handleVoiceprintThresholdChange,
        handleVadChange,
        refreshVoiceprintConfig,
    };
};
