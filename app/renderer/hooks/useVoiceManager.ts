import { WhisperModelInfo } from "./voice/types";
import { useSttVoiceState } from "./voice/useSttVoiceState";
import { useTtsVoiceState } from "./voice/useTtsVoiceState";
import { useVoiceprintState } from "./voice/useVoiceprintState";

export type { WhisperModelInfo } from "./voice/types";

export interface VoiceManagerData {
    whisperModels: WhisperModelInfo[];
    currentWhisperModel: string;
    loadingStatus: string;
    sttEngineType: string;
    audioDevices: { index: number; name: string; channels: number }[];
    currentAudioDevice: string | null;
    edgeVoices: { name: string; gender: string }[];
    gptVoices: { name: string; gender: string }[];
    activeTtsEngines: string[];
    ttsPlugins: any[];
    voiceprintEnabled: boolean;
    voiceprintThreshold: number;
    voiceprintProfile: string;
    voiceprintStatus: string;
    voiceprintLoaded: boolean;
    vadStartThreshold: number;
    vadEndThreshold: number;
    handleSttModelChange: (newModel: string) => Promise<void>;
    handleEngineChange: (newEngine: string) => Promise<void>;
    handleAudioDeviceChange: (deviceName: string) => Promise<void>;
    handleVoiceprintToggle: (enabled: boolean) => Promise<void>;
    handleVoiceprintThresholdChange: (val: number) => Promise<void>;
    handleVadChange: (
        key: "speech_start_threshold" | "speech_end_threshold",
        value: number,
    ) => Promise<void>;
    setVoiceprintProfile: (val: string) => void;
    refreshVoiceData: () => Promise<void>;
}

export const useVoiceManager = (isActive: boolean): VoiceManagerData => {
    const stt = useSttVoiceState(isActive);
    const tts = useTtsVoiceState(isActive);
    const voiceprint = useVoiceprintState(isActive, stt.currentAudioDevice);

    const refreshVoiceData = async () => {
        await Promise.all([
            stt.refreshModels(),
            stt.refreshAudioDevices(),
            tts.refreshVoices(),
            voiceprint.refreshVoiceprintConfig(),
        ]);
    };

    return {
        whisperModels: stt.whisperModels,
        currentWhisperModel: stt.currentWhisperModel,
        loadingStatus: stt.loadingStatus,
        sttEngineType: stt.sttEngineType,
        audioDevices: stt.audioDevices,
        currentAudioDevice: stt.currentAudioDevice,
        edgeVoices: tts.edgeVoices,
        gptVoices: tts.gptVoices,
        activeTtsEngines: tts.activeTtsEngines,
        ttsPlugins: tts.ttsPlugins,
        voiceprintEnabled: voiceprint.voiceprintEnabled,
        voiceprintThreshold: voiceprint.voiceprintThreshold,
        voiceprintProfile: voiceprint.voiceprintProfile,
        voiceprintStatus: voiceprint.voiceprintStatus,
        voiceprintLoaded: voiceprint.voiceprintLoaded,
        vadStartThreshold: voiceprint.vadStartThreshold,
        vadEndThreshold: voiceprint.vadEndThreshold,
        handleSttModelChange: stt.handleSttModelChange,
        handleEngineChange: stt.handleEngineChange,
        handleAudioDeviceChange: stt.handleAudioDeviceChange,
        handleVoiceprintToggle: voiceprint.handleVoiceprintToggle,
        handleVoiceprintThresholdChange: voiceprint.handleVoiceprintThresholdChange,
        handleVadChange: voiceprint.handleVadChange,
        setVoiceprintProfile: voiceprint.setVoiceprintProfile,
        refreshVoiceData,
    };
};
