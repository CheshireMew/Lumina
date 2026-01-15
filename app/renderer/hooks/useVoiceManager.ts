import { useState, useRef, useCallback, useEffect } from "react";
import { API_CONFIG } from "../config";

export interface WhisperModelInfo {
    name: string;
    desc?: string;
    size?: string;
    engine?: string;
    download_status: "idle" | "downloading" | "completed" | "failed";
}

export const useVoiceManager = (isActive: boolean) => {
    // STT / Whisper State
    const [whisperModels, setWhisperModels] = useState<WhisperModelInfo[]>([]);
    const [currentWhisperModel, setCurrentWhisperModel] = useState("base");
    const [loadingStatus, setLoadingStatus] = useState("idle");
    const [sttEngineType, setSttEngineType] =
        useState<string>("faster_whisper");

    // Audio I/O State
    const [audioDevices, setAudioDevices] = useState<
        { index: number; name: string; channels: number }[]
    >([]);
    const [currentAudioDevice, setCurrentAudioDevice] = useState<string | null>(
        null
    );

    // TTS Voices State
    const [edgeVoices, setEdgeVoices] = useState<
        { name: string; gender: string }[]
    >([]);
    const [gptVoices, setGptVoices] = useState<
        { name: string; gender: string }[]
    >([]);
    const [activeTtsEngines, setActiveTtsEngines] = useState<string[]>([]);
    const [ttsPlugins, setTtsPlugins] = useState<any[]>([]); // ⚡ Decoupled Plugins List

    // Voiceprint State
    const [voiceprintEnabled, setVoiceprintEnabled] = useState(false);
    const [voiceprintThreshold, setVoiceprintThreshold] = useState(0.6);
    const [voiceprintProfile, setVoiceprintProfile] = useState("default");
    const [voiceprintStatus, setVoiceprintStatus] = useState<string>("");

    // VAD State (Voice Activity Detection)
    const [vadStartThreshold, setVadStartThreshold] = useState(0.6);
    const [vadEndThreshold, setVadEndThreshold] = useState(0.05);

    // Suppression Refs
    const hasWarnedTTS = useRef(false);
    const hasWarnedSTT = useRef(false);

    // Fetch STT Models
    const fetchModels = useCallback(async () => {
        try {
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/models/list`);
            if (res.ok) {
                const data = await res.json();
                setWhisperModels(data.models || []);
                setCurrentWhisperModel(data.current_model);
                setSttEngineType(data.engine_type || "faster_whisper");
                setLoadingStatus(data.loading_status);
            }
        } catch (err) {
            console.error("Failed to fetch STT models", err);
        }
    }, []);

    // Fetch Audio Devices
    const fetchAudioDevices = useCallback(async () => {
        try {
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/devices`);
            if (res.ok) {
                const data = await res.json();
                setAudioDevices(data.devices || []);
                setCurrentAudioDevice(data.current || null);
                hasWarnedSTT.current = false;
            }
        } catch (e) {
            if (!hasWarnedSTT.current) {
                console.warn("[VoiceManager] STT Service unavailable", e);
                hasWarnedSTT.current = true;
            }
        }
    }, []);

    // Fetch TTS Status & Voices & Plugins
    const fetchTTSStatus = useCallback(async () => {
        try {
            // 1. Fetch Engine Status
            const res = await fetch(`${API_CONFIG.TTS_BASE_URL}/health`);
            if (res.ok) {
                const data = await res.json();
                setActiveTtsEngines(data.active_engines || []);
                hasWarnedTTS.current = false;
            }

            // 2. Fetch Plugins (for Schemas)
            try {
                // Hardcoded port 8010 for backend (API_CONFIG.BASE_URL)
                // Assuming API_CONFIG.BASE_URL matches python_backend port
                const pRes = await fetch(`${API_CONFIG.BASE_URL}/plugins/list`);
                if (pRes.ok) {
                    const pData = await pRes.json();
                    const tts = pData.filter((p: any) => p.category === "tts");
                    setTtsPlugins(tts);
                }
            } catch (pluginErr) {
                console.warn(
                    "Failed to fetch TTS plugins for schema",
                    pluginErr
                );
            }
        } catch (e) {
            if (!hasWarnedTTS.current) {
                console.warn("[VoiceManager] TTS Service unavailable", e);
                hasWarnedTTS.current = true;
            }
            setActiveTtsEngines([]);
        }
    }, []);

    const fetchTTSVoices = useCallback(async () => {
        await fetchTTSStatus();

        // Edge TTS
        try {
            const res = await fetch(
                `${API_CONFIG.TTS_BASE_URL}/tts/voices?engine=edge-tts`
            );
            if (res.ok) {
                const data = await res.json();
                setEdgeVoices([
                    ...(data.chinese || []),
                    ...(data.english || []),
                ]);
            }
        } catch (e) {}

        // GPT-SoVITS
        try {
            const res = await fetch(
                `${API_CONFIG.TTS_BASE_URL}/tts/voices?engine=gpt-sovits`
            );
            if (res.ok) {
                const data = await res.json();
                setGptVoices(data.voices || []);
            }
        } catch (e) {}
    }, [fetchTTSStatus]);

    // Fetch Voiceprint & VAD Config
    const fetchVoiceprintConfig = useCallback(async () => {
        try {
            const res = await fetch(
                `${API_CONFIG.STT_BASE_URL}/voiceprint/status`
            );
            if (res.ok) {
                const data = await res.json();
                setVoiceprintEnabled(data.enabled || false);
                setVoiceprintThreshold(data.threshold || 0.6);
                setVoiceprintProfile(data.profile || "default");
                setVoiceprintStatus(
                    data.profile_loaded ? "✓ 已加载声纹" : "⚠️ 未注册声纹"
                );
            }

            const statusRes = await fetch(
                `${API_CONFIG.STT_BASE_URL}/audio/status`
            );
            if (statusRes.ok) {
                const data = await statusRes.json();
                if (data.speech_start_threshold !== undefined)
                    setVadStartThreshold(data.speech_start_threshold);
                if (data.speech_end_threshold !== undefined)
                    setVadEndThreshold(data.speech_end_threshold);
            }
        } catch (e) {
            console.warn("Failed to fetch voice/vad config", e);
        }
    }, []);

    const handleSttModelChange = async (newModel: string) => {
        try {
            await fetch(`${API_CONFIG.STT_BASE_URL}/models/switch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model_name: newModel }),
            });
            setLoadingStatus("loading");
            fetchModels();
        } catch (err) {
            alert("Failed to confirm model switch");
        }
    };

    const handleEngineChange = async (newEngine: string) => {
        setSttEngineType(newEngine);
        let targetModel = "base";
        if (newEngine === "sense_voice") targetModel = "sense-voice";
        else if (newEngine === "paraformer_zh") targetModel = "paraformer-zh";
        else if (newEngine === "paraformer_en") targetModel = "paraformer-en";

        await handleSttModelChange(targetModel);
    };

    const handleAudioDeviceChange = async (deviceName: string) => {
        try {
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_name: deviceName }),
            });
            if (res.ok) {
                setCurrentAudioDevice(deviceName);
            } else {
                alert("Failed to switch audio device");
            }
        } catch (err) {
            alert("Failed to connect to STT server");
        }
    };

    const handleVoiceprintToggle = async (enabled: boolean) => {
        try {
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: enabled,
                    voiceprint_threshold: voiceprintThreshold,
                    voiceprint_profile: voiceprintProfile,
                }),
            });
            if (res.ok) {
                setVoiceprintEnabled(enabled);
                alert(
                    `声纹验证已${
                        enabled ? "启用" : "禁用"
                    }\n请重启 stt_server.py 使配置生效`
                );
            }
        } catch (e) {
            alert("无法连接到STT服务器");
        }
    };

    const handleVoiceprintThresholdChange = async (val: number) => {
        setVoiceprintThreshold(val);
        // Debounce logic omitted for simplicity, but could be added
        try {
            await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: voiceprintEnabled,
                    voiceprint_threshold: val,
                    voiceprint_profile: voiceprintProfile,
                }),
            });
        } catch (e) {}
    };

    const handleVadChange = async (
        key: "speech_start_threshold" | "speech_end_threshold",
        value: number
    ) => {
        if (key === "speech_start_threshold") setVadStartThreshold(value);
        if (key === "speech_end_threshold") setVadEndThreshold(value);
        try {
            await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [key]: value }),
            });
        } catch (e) {}
    };

    // Initial Load & Polling
    useEffect(() => {
        if (!isActive) return;

        fetchModels();
        fetchAudioDevices();
        fetchTTSVoices();
        fetchVoiceprintConfig();

        const interval = setInterval(fetchModels, 2000);
        return () => clearInterval(interval);
    }, [
        isActive,
        fetchModels,
        fetchAudioDevices,
        fetchTTSVoices,
        fetchVoiceprintConfig,
    ]);

    return {
        whisperModels,
        currentWhisperModel,
        loadingStatus,
        sttEngineType,
        audioDevices,
        currentAudioDevice,
        edgeVoices,
        gptVoices,
        activeTtsEngines,
        ttsPlugins, // ⚡ Export
        voiceprintEnabled,
        voiceprintThreshold,
        voiceprintProfile,
        voiceprintStatus,
        vadStartThreshold,
        vadEndThreshold,

        handleSttModelChange,
        handleEngineChange,
        handleAudioDeviceChange,
        handleVoiceprintToggle,
        handleVoiceprintThresholdChange,
        handleVadChange,
        setVoiceprintProfile,

        refreshVoiceData: fetchModels,
    };
};
