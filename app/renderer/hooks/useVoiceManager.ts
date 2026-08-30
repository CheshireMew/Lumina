import { AudioDevice, WhisperModelInfo } from "./voice/types";
import { useSttVoiceState } from "./voice/useSttVoiceState";
import { useTtsVoiceState } from "./voice/useTtsVoiceState";
import { useVoiceprintState } from "./voice/useVoiceprintState";
import { RuntimeConfig } from "../runtime/runtimeConfig";

export type { WhisperModelInfo } from "./voice/types";

export interface VoiceManagerData {
    apiBaseUrl: string;
    whisperModels: WhisperModelInfo[];
    currentWhisperModel: string;
    loadingStatus: string;
    audioDevices: AudioDevice[];
    currentAudioDevice: string | null;
    sttLoadState: "loading" | "ready" | "error";
    sttError: string;
    activeTtsEngines: string[];
    ttsEngines: { id: string; name: string }[];
    voicesByEngine: Record<string, { name: string; gender: string }[]>;
    ttsLoadState: "loading" | "ready" | "error";
    ttsError: string;
    voiceprintEnabled: boolean;
    voiceprintThreshold: number;
    voiceprintProfile: string;
    voiceprintStatus: string;
    voiceprintLoaded: boolean;
    vadAggressiveness: number;
    vadStartThreshold: number;
    vadEndThreshold: number;
    handleSttModelChange: (newModel: string) => Promise<void>;
    handleAudioDeviceChange: (deviceName: string) => Promise<void>;
    handleVoiceprintToggle: (enabled: boolean) => Promise<void>;
    handleVoiceprintThresholdChange: (val: number) => Promise<void>;
    handleVadChange: (
        key: "vad_aggressiveness" | "speech_start_threshold" | "speech_end_threshold",
        value: number,
    ) => Promise<void>;
    handleVoiceprintProfileChange: (val: string) => Promise<void>;
    refreshVoiceData: () => Promise<void>;
}

export const useVoiceManager = (
    isActive: boolean,
    runtimeConfig: RuntimeConfig,
): VoiceManagerData => {
    const stt = useSttVoiceState(isActive, runtimeConfig.sttBaseUrl);
    const tts = useTtsVoiceState(isActive, runtimeConfig.ttsBaseUrl);
    const voiceprint = useVoiceprintState(
        isActive,
        stt.currentAudioDevice,
        runtimeConfig.sttBaseUrl,
    );

    const refreshVoiceData = async () => {
        await Promise.all([
            stt.refreshModels(),
            stt.refreshAudioDevices(),
            tts.refreshVoices(),
            voiceprint.refreshVoiceprintConfig(),
        ]);
    };

    return {
        apiBaseUrl: runtimeConfig.apiBaseUrl,
        whisperModels: stt.whisperModels,
        currentWhisperModel: stt.currentWhisperModel,
        loadingStatus: stt.loadingStatus,
        audioDevices: stt.audioDevices,
        currentAudioDevice: stt.currentAudioDevice,
        sttLoadState: stt.sttLoadState,
        sttError: stt.sttError,
        activeTtsEngines: tts.activeTtsEngines,
        ttsEngines: tts.ttsEngines,
        voicesByEngine: tts.voicesByEngine,
        ttsLoadState: tts.ttsLoadState,
        ttsError: tts.ttsError,
        voiceprintEnabled: voiceprint.voiceprintEnabled,
        voiceprintThreshold: voiceprint.voiceprintThreshold,
        voiceprintProfile: voiceprint.voiceprintProfile,
        voiceprintStatus: voiceprint.voiceprintStatus,
        voiceprintLoaded: voiceprint.voiceprintLoaded,
        vadAggressiveness: voiceprint.vadAggressiveness,
        vadStartThreshold: voiceprint.vadStartThreshold,
        vadEndThreshold: voiceprint.vadEndThreshold,
        handleSttModelChange: stt.handleSttModelChange,
        handleAudioDeviceChange: stt.handleAudioDeviceChange,
        handleVoiceprintToggle: voiceprint.handleVoiceprintToggle,
        handleVoiceprintThresholdChange: voiceprint.handleVoiceprintThresholdChange,
        handleVadChange: voiceprint.handleVadChange,
        handleVoiceprintProfileChange: voiceprint.handleVoiceprintProfileChange,
        refreshVoiceData,
    };
};
