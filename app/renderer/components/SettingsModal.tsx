
import React, { useState, useEffect } from 'react';
import { CharacterProfile, DEFAULT_CHARACTERS } from '@core/llm/types';
import { ttsService } from '@core/voice/tts_service';
import { API_CONFIG } from '../config';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onClearHistory?: () => void;
    onContextWindowChange?: (newWindow: number) => void;
    onLLMSettingsChange?: (apiKey: string, baseUrl: string, model: string, temperature: number) => void;
    onCharactersUpdated?: (characters: CharacterProfile[], activeId: string) => void;
    onUserNameUpdated?: (newName: string) => void;
    onLive2DHighDpiChange?: (enabled: boolean) => void;
    onCharacterSwitch?: (characterId: string) => void;
    onThinkingModeChange?: (enabled: boolean) => void;
    activeCharacterId: string; // ⚡ Lifted State
}

interface WhisperModelInfo {
    name: string;
    desc?: string; // Updated from 'size'
    size?: string;
    engine?: string; // Newly added
    download_status: 'idle' | 'downloading' | 'completed' | 'failed';
}

type Tab = 'general' | 'voice' | 'memory' | 'characters' | 'interaction';

const AVAILABLE_MODELS = [
    { name: 'Hiyori (Default)', path: '/live2d/Hiyori/Hiyori.model3.json' },
    { name: 'Laffey II (拉菲)', path: '/live2d/imported/Laffey_II/Laffey Ⅱ.model3.json' },
    { name: 'PinkFox', path: '/live2d/imported/PinkFox/PinkFox.model3.json' },
    { name: 'Kasane Teto (重音テト)', path: '/live2d/imported/KasaneTeto/重音テト.model3.json' },
    { name: 'Haru', path: '/live2d/imported/Haru/Haru.model3.json' },
    { name: 'MaoPro', path: '/live2d/imported/MaoPro/mao_pro.model3.json' },
    { name: 'MemuCat', path: '/live2d/imported/MemuCat/memu_cat.model3.json' },
    { name: 'Hiyori (Mic Ver)', path: '/live2d/imported/Hiyori_Mic/hiyori_pro_mic.model3.json' },
];

const inputStyle = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    color: '#1f2937',
    outline: 'none',
    boxSizing: 'border-box' as const,
    transition: 'border-color 0.2s'
};

const labelStyle = {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: '#4b5563',
    marginBottom: '4px'
};

const buttonStyle = {
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s'
};

const SettingsModal: React.FC<SettingsModalProps> = ({
    isOpen, onClose, onClearHistory, onContextWindowChange, onLLMSettingsChange, onCharactersUpdated, onUserNameUpdated, onLive2DHighDpiChange, onCharacterSwitch,
    activeCharacterId, onThinkingModeChange
}) => {
    const [activeTab, setActiveTab] = useState<Tab>('general');

    // LLM Settings
    const [apiKey, setApiKey] = useState('');
    const [apiBaseUrl, setApiBaseUrl] = useState('https://api.deepseek.com/v1');
    const [modelName, setModelName] = useState('deepseek-chat');
    const [temperature, setTemperature] = useState(0.7);
    // ⚡ DeepSeek Custom Settings
    const [thinkingEnabled, setThinkingEnabled] = useState(false);

    // Visual Settings
    const [highDpiEnabled, setHighDpiEnabled] = useState(false);

    // User Settings
    const [userName, setUserName] = useState('Master');

    // Conversation Memory Settings
    const [contextWindow, setContextWindow] = useState(15);

    // Whisper Settings
    const [whisperModels, setWhisperModels] = useState<WhisperModelInfo[]>([]);
    const [currentWhisperModel, setCurrentWhisperModel] = useState('base');
    const [loadingStatus, setLoadingStatus] = useState('idle');
    const [sttServerUrl] = useState('http://127.0.0.1:8765');

    // Audio Device Settings
    const [audioDevices, setAudioDevices] = useState<{ index: number, name: string, channels: number }[]>([]);
    const [currentAudioDevice, setCurrentAudioDevice] = useState<string | null>(null);

    // Voiceprint Settings
    const [voiceprintEnabled, setVoiceprintEnabled] = useState(false);
    const [voiceprintThreshold, setVoiceprintThreshold] = useState(0.6);
    const [voiceprintProfile, setVoiceprintProfile] = useState('default');
    const [voiceprintStatus, setVoiceprintStatus] = useState<string>('');

    // VAD Settings
    const [vadStartThreshold, setVadStartThreshold] = useState(0.6);
    const [vadEndThreshold, setVadEndThreshold] = useState(0.05);

    // Character Settings
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    // const [activeCharacterId, setActiveCharacterId] = useState<string>(''); // REMOVED local state: Lifted to props
    const [editingCharId, setEditingCharId] = useState<string | null>(null);
    // Track deleted characters for batch removal on save
    const [isLoadingCharacters, setIsLoadingCharacters] = useState(false);

    // Interaction Settings (Global Tab State)
    const [globalGalgameEnabled, setGlobalGalgameEnabled] = useState(true);
    const [globalSoulEvolutionEnabled, setGlobalSoulEvolutionEnabled] = useState(true); // ⚡ New toggle
    const [globalProactiveEnabled, setGlobalProactiveEnabled] = useState(true);
    const [globalHeartbeatEnabled, setGlobalHeartbeatEnabled] = useState(false); // "Use Custom Duration"
    const [globalProactiveThreshold, setGlobalProactiveThreshold] = useState(15);
    
    // ⚡ Bilibili Settings
    const [globalBilibiliEnabled, setGlobalBilibiliEnabled] = useState(false);
    const [globalBilibiliRoomId, setGlobalBilibiliRoomId] = useState('');

    const [deletedCharIds, setDeletedCharIds] = useState<string[]>([]);
    const [isSaving, setIsSaving] = useState(false); // ⚡ Loading State

    const fetchCharacters = async () => {
        setIsLoadingCharacters(true);
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/characters`);
            if (response.ok) {
                const { characters: backendChars } = await response.json();
                
                // 转换后端格式到前端 CharacterProfile 格式
                const convertedChars: CharacterProfile[] = backendChars.map((char: any) => {
                    // 查找对应的模型路径
                    const modelDef = AVAILABLE_MODELS.find(m => m.name === char.live2d_model);
                    const realPath = modelDef ? modelDef.path : char.live2d_model; // Fallback to raw value if not found

                    return {
                        id: char.character_id,
                        name: char.name,
                        description: char.description,
                        systemPrompt: char.system_prompt,
                        modelPath: realPath, // ⚡ 使用真正的路径
                        voiceConfig: char.voice_config,
                        heartbeatEnabled: char.heartbeat_enabled ?? true, // Strategy: False=Auto, True=Fixed
                        proactiveChatEnabled: char.proactive_chat_enabled ?? true, // Master Switch
                        galgameModeEnabled: char.galgame_mode_enabled ?? true, // ⚡ Galgame Mode
                        soulEvolutionEnabled: char.soul_evolution_enabled ?? true, // ⚡ Soul Evolution Mode
                        proactiveThresholdMinutes: char.proactive_threshold_minutes ?? 15,
                        bilibili: char.bilibili || { enabled: false, roomId: 0 } // ⚡ Bilibili Config
                    };
                });
                
                // ⚡ Sort on Load: Active character first
                const activeId = activeCharacterId; // Use current prop value
                
                // ⚡ Initialize Global Interaction Settings from Active Character (or first)
                const activeChar = convertedChars.find(c => c.id === activeId) || convertedChars[0];
                if (activeChar) {
                    setGlobalGalgameEnabled(activeChar.galgameModeEnabled !== false);
                    setGlobalSoulEvolutionEnabled(activeChar.soulEvolutionEnabled !== false); // ⚡ Init
                    setGlobalProactiveEnabled(activeChar.proactiveChatEnabled !== false);
                    setGlobalHeartbeatEnabled(activeChar.heartbeatEnabled === true);
                    setGlobalProactiveThreshold(activeChar.proactiveThresholdMinutes || 15);
                    setGlobalBilibiliEnabled(activeChar.bilibili?.enabled || false);
                    setGlobalBilibiliRoomId(activeChar.bilibili?.roomId?.toString() || '');
                }

                const sortedChars = convertedChars.sort((a, b) => {
                     if (a.id === activeId) return -1;
                     if (b.id === activeId) return 1;
                     return 0;
                });

                setCharacters(sortedChars);
                setDeletedCharIds([]); // Reset deleted list on open
                
                console.log('[Settings] ✅ Loaded characters from backend:', convertedChars.length);
            } else {
                console.error('[Settings] Failed to load characters from backend');
                // Fallback: 使用本地数据
                const settings = (window as any).settings;
                const loadedChars = await settings.get('characters') as CharacterProfile[];
                if (loadedChars) setCharacters(loadedChars);
            }
        } catch (error) {
            console.error('[Settings] Error loading characters:', error);
            // Fallback: 使用本地数据
            const settings = (window as any).settings;
            const loadedChars = await settings.get('characters') as CharacterProfile[];
            if (loadedChars) setCharacters(loadedChars);
        } finally {
            setIsLoadingCharacters(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            const loadSettings = async () => {
                const settings = (window as any).settings;

                // LLM
                setApiKey(await settings.get('apiKey') || '');
                let url = await settings.get('apiBaseUrl') || `${API_CONFIG.BASE_URL}/v1`;
                // ⚡ Auto-migrate stale /free-llm prefix
                if (url.includes('/free-llm')) {
                    url = url.replace('/free-llm', '');
                    console.log('[Settings] Migrated stale Free LLM URL to:', url);
                    await settings.set('apiBaseUrl', url); // Persist fix immediately
                }
                setApiBaseUrl(url);
                // ⚡ Detect Free Mode if URL points to our backend (127.0.0.1:8010)
                setLlmProvider(url.includes('127.0.0.1:8010') || url.includes('localhost:8010') ? 'free' : 'custom');
                
        setModelName(await settings.get('modelName') || 'gpt-4o-mini');
        setTemperature(await settings.get('llm_temperature') || 0.7);
        
        // ⚡ DeepSeek Thinking
        setThinkingEnabled(await settings.get('thinking_enabled') || false); // Default false

        setUserName(await settings.get('userName') || 'Master');

        // Visual
        setHighDpiEnabled(await settings.get('live2d_high_dpi') || false);

        // Memory
        setContextWindow(await settings.get('contextWindow') || 15);

        // ⚡ 新逻辑：从后端 API 加载角色列表
        fetchCharacters();

        // Whisper & TTS Voices & Audio Devices & Voiceprint
        fetchModels();
        fetchTTSVoices();
        fetchAudioDevices();
        fetchVoiceprintConfig();
    };
            loadSettings();
        }
    }, [isOpen]);

    // TTS Voices Fetching
    const [edgeVoices, setEdgeVoices] = useState<{ name: string, gender: string }[]>([]);
    const [gptVoices, setGptVoices] = useState<{ name: string, gender: string }[]>([]);
    const [activeTtsEngines, setActiveTtsEngines] = useState<string[]>([]); // ⚡ Track active engines
    const [llmProvider, setLlmProvider] = useState<'free' | 'custom'>('free'); // ⚡ Provider Toggle

    // ⚡ LLM Manager State
    const [llmRoutes, setLlmRoutes] = useState<any[]>([]);
    const [llmProviders, setLlmProviders] = useState<any[]>([]);
    const [advancedModelTab, setAdvancedModelTab] = useState(false); // Toggle for simple vs advanced

    // ⚡ Log Suppression Refs
    const hasWarnedTTS = React.useRef(false);
    const hasWarnedSTT = React.useRef(false);

    const fetchTTSStatus = async () => {
        try {
            const res = await fetch(`${API_CONFIG.TTS_BASE_URL}/health`);
            if (res.ok) {
                const data = await res.json();
                setActiveTtsEngines(data.active_engines || []);
                hasWarnedTTS.current = false; // Reset warning on success
            }
        } catch (e) {
             if (!hasWarnedTTS.current) {
                 console.warn("[Settings] TTS Service unavailable (suppressing further errors)");
                 hasWarnedTTS.current = true;
             }
             setActiveTtsEngines([]);
        }
    };

    const fetchTTSVoices = async () => {
        await fetchTTSStatus(); // ⚡ Check health first
        try {
            // Fetch Edge TTS Voices
            try {
                const res = await fetch(`${API_CONFIG.TTS_BASE_URL}/tts/voices?engine=edge-tts`);
                if (res.ok) {
                    const data = await res.json();
                    const allVoices = [...(data.chinese || []), ...(data.english || [])];
                    setEdgeVoices(allVoices);
                }
            } catch (e) { 
                // Silent catch if status already warned
                if (!hasWarnedTTS.current) console.warn("Failed to fetch Edge voices", e); 
            }

            // Fetch GPT-SoVITS Voices
            try {
                const res = await fetch(`${API_CONFIG.TTS_BASE_URL}/tts/voices?engine=gpt-sovits`);
                if (res.ok) {
                    const data = await res.json();
                    setGptVoices(data.voices || []);
                }
            } catch (e) { 
                if (!hasWarnedTTS.current) console.warn("Failed to fetch GPT-SoVITS voices", e); 
            }

        } catch (e) {
            if (!hasWarnedTTS.current) console.error("Failed to fetch TTS voices", e);
        }
    };

    // Audio Devices Fetching
    const fetchAudioDevices = async () => {
        try {
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/devices`);
            if (res.ok) {
                const data = await res.json();
                setAudioDevices(data.devices || []);
                setCurrentAudioDevice(data.current || null);
                hasWarnedSTT.current = false; // Reset warning
            }
        } catch (e) {
            if (!hasWarnedSTT.current) {
                console.warn("[Settings] STT Service unavailable (suppressing further errors)");
                hasWarnedSTT.current = true;
            }
        }
    };

    // ⚡ Fetch LLM Manager Data
    const fetchLlmManagerData = async () => {
        try {
            const routesRes = await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/routes`);
            const provRes = await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/providers`);
            
            if (routesRes.ok && provRes.ok) {
                const rData = await routesRes.json();
                const pData = await provRes.json();
                setLlmRoutes(rData.routes || []);
                setLlmProviders(pData.providers || []);
            }
        } catch (e) {
            console.warn("[Settings] Failed to fetch LLM Manager data (backend might be old version)", e);
        }
    };

    const handleRouteUpdate = async (feature: string, providerId: string, model: string, temp?: number, topP?: number, presPenalty?: number, freqPenalty?: number) => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/routes/${feature}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    provider_id: providerId, 
                    model: model, 
                    temperature: temp,
                    top_p: topP,
                    presence_penalty: presPenalty,
                    frequency_penalty: freqPenalty
                })
            });
            if (res.ok) {
                fetchLlmManagerData(); // Refresh
            }
        } catch (e) {
            console.error("Failed to update route", e);
        }
    };

    const handleAudioDeviceChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        const deviceName = e.target.value;
        try {
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_name: deviceName })
            });
            if (res.ok) {
                setCurrentAudioDevice(deviceName);
                console.log(`Audio device switched to: ${deviceName}`);
            } else {
                alert("Failed to switch audio device");
            }
        } catch (err) {
            console.error("Failed to set audio device", err);
            alert("Failed to connect to STT server");
        }
    };

    // Voiceprint & VAD Functions
    const fetchVoiceprintConfig = async () => {
        try {
            // Fetch Voiceprint Status
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/voiceprint/status`);
            if (res.ok) {
                const data = await res.json();
                setVoiceprintEnabled(data.enabled || false);
                setVoiceprintThreshold(data.threshold || 0.6);
                setVoiceprintProfile(data.profile || 'default');
                setVoiceprintStatus(data.profile_loaded ? '✓ 已加载声纹' : '⚠️ 未注册声纹');
            }
            // Fetch VAD Status (New)
            const statusRes = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/status`);
            if (statusRes.ok) {
                const data = await statusRes.json();
                if (data.speech_start_threshold !== undefined) setVadStartThreshold(data.speech_start_threshold);
                if (data.speech_end_threshold !== undefined) setVadEndThreshold(data.speech_end_threshold);
            }
        } catch (e) {
            console.warn('Failed to fetch voice/vad config', e);
        }
    };

    const handleVadChange = async (key: 'speech_start_threshold' | 'speech_end_threshold', value: number) => {
        if (key === 'speech_start_threshold') setVadStartThreshold(value);
        if (key === 'speech_end_threshold') setVadEndThreshold(value);
        
        // Debounced save could be better, but direct set is okay for settings
        try {
            await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    [key]: value
                })
            });
        } catch (e) { console.error("Failed to update VAD param", e); }
    };

    // Migration: Initialize systemPrompt from description if missing (for legacy characters)
    useEffect(() => {
        let changed = false;
        const migratedCharacters = characters.map(char => {
            if (char.systemPrompt === undefined) {
                changed = true;
                return {
                    ...char,
                    systemPrompt: char.description // Copy legacy description to systemPrompt
                };
            }
            return char;
        });

        if (changed) {
            console.log('[Settings] Migrated legacy characters: separated description and systemPrompt');
            setCharacters(migratedCharacters);
        }
    }, [characters]); // Run whenever characters list updates (safe due to undefined check)

    const handleVoiceprintToggle = async (enabled: boolean) => {
        try {
            // Always use current state values, never hardcoded defaults
            const res = await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: enabled,
                    voiceprint_threshold: voiceprintThreshold, // Use current state
                    voiceprint_profile: voiceprintProfile // Use current state (NOT "default"!)
                })
            });
            if (res.ok) {
                setVoiceprintEnabled(enabled);
                alert(`声纹验证已${enabled ? '启用' : '禁用'}\n请重启 stt_server.py 使配置生效`);
            }
        } catch (e) {
            console.error('Failed to toggle voiceprint', e);
            alert('无法连接到STT服务器');
        }
    };

    const handleVoiceprintThresholdChange = async (threshold: number) => {
        setVoiceprintThreshold(threshold);
        try {
            await fetch(`${API_CONFIG.STT_BASE_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: voiceprintEnabled,
                    voiceprint_threshold: threshold,
                    voiceprint_profile: voiceprintProfile // Preserve profile from state!
                })
            });
        } catch (e) {
            console.warn('Failed to update threshold', e);
        }
    };

    // Poll status for STT models
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isOpen && activeTab === 'voice') {
            fetchModels(); // Fetch immediately
            interval = setInterval(fetchModels, 2000);
        }
        return () => clearInterval(interval);
    }, [isOpen, activeTab]);

    // ⚡ Poll LLM Manager Data when open
    useEffect(() => {
        if (isOpen && activeTab === 'general') {
            fetchLlmManagerData();
        }
    }, [isOpen, activeTab]);

    const [sttEngineType, setSttEngineType] = useState<string>('faster_whisper');

    const fetchModels = async () => {
        try {
            const res = await fetch(`${sttServerUrl}/models/list`);
            if (res.ok) {
                const data = await res.json();
                setWhisperModels(data.models);
                setCurrentWhisperModel(data.current_model);
                setSttEngineType(data.engine_type || 'faster_whisper');
                setLoadingStatus(data.loading_status);
            }
        } catch (err) {
            console.error("Failed to fetch STT models", err);
        }
    };

    const handleSttModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        // This handles both Engine switching (to sense-voice) and Model switching (within Whisper)
        const newModel = e.target.value;
        try {
            await fetch(`${sttServerUrl}/models/switch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: newModel })
            });
            setLoadingStatus('loading'); // Optimistic update
            fetchModels();
        } catch (err) {
            alert("Failed to confirm model switch");
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        const settings = (window as any).settings;
        
        // 保存 LLM 配置到 localStorage
        await settings.set('apiKey', apiKey);
        await settings.set('apiBaseUrl', apiBaseUrl);
        await settings.set('modelName', modelName);
        await settings.set('llm_temperature', temperature);
        await settings.set('thinking_enabled', thinkingEnabled); // ⚡ Save Thinking Mode
        await settings.set('userName', userName);
        await settings.set('contextWindow', contextWindow);
        await settings.set('activeCharacterId', activeCharacterId);
        await settings.set('live2d_high_dpi', highDpiEnabled);

        // 保存声纹及VAD配置并应用到后端
        // ⚡ Now includes VAD Thresholds so they are also persisted!
        if (voiceprintEnabled || voiceprintThreshold !== 0.6 || voiceprintProfile !== 'default' || vadStartThreshold !== 0.6 || vadEndThreshold !== 0.15) {
            try {
                await fetch(`${sttServerUrl}/audio/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        device_name: currentAudioDevice,
                        // Voiceprint
                        enable_voiceprint_filter: voiceprintEnabled,
                        voiceprint_threshold: voiceprintThreshold,
                        voiceprint_profile: voiceprintProfile,
                        // VAD (Persisted)
                        speech_start_threshold: vadStartThreshold,
                        speech_end_threshold: vadEndThreshold
                    })
                });

                if (voiceprintEnabled) {
                    console.log('[Settings] Voiceprint configuration saved. Please restart stt_server.py for changes to take effect.');
                }
            } catch (e) {
                console.error('Failed to save voiceprint/VAD config', e);
            }
        }

        // ⚡ 修复逻辑：保存所有角色配置到后端 API (批量并发)
        try {
            console.log(`[Settings] 📤 Saving ${characters.length} characters...`);
            
            // 1. Save/Update all current characters
            const savePromises = characters.map(char => {
                const payload = {
                    character_id: char.id,
                    name: char.name,
                    display_name: char.name,
                    description: char.description,
                    system_prompt: char.systemPrompt,
                    live2d_model: char.modelPath,
                    // voice_config: char.voiceConfig, // Already included above, removed duplicate
                    
                    // ⚡ Apply Global Interaction Settings to ALL characters on save
                    heartbeat_enabled: globalHeartbeatEnabled,
                    proactive_chat_enabled: globalProactiveEnabled,
                    galgame_mode_enabled: globalGalgameEnabled,
                    soul_evolution_enabled: globalSoulEvolutionEnabled, // ⚡ Save to backend
                    proactive_threshold_minutes: globalProactiveThreshold,
                    bilibili: {
                        enabled: globalBilibiliEnabled,
                        room_id: parseInt(globalBilibiliRoomId) || 0
                    }
                };
                return fetch(`${API_CONFIG.BASE_URL}/characters/${char.id}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            });

            // 2. Delete removed characters
            const deletePromises = deletedCharIds.map(id => {
               console.log(`[Settings] 🗑️ Deleting character: ${id}`);
               return fetch(`${API_CONFIG.BASE_URL}/characters/${id}`, {
                   method: 'DELETE'
               }); 
            });

            await Promise.all([...savePromises, ...deletePromises]);
            console.log('[Settings] ✅ All character changes synced to backend');
            
            setDeletedCharIds([]); // Clear deleted list

            // ⚡ Lightweight heartbeat reload (no Memory reinit)
            try {
                const reloadRes = await fetch(`${API_CONFIG.BASE_URL}/heartbeat/reload`, { method: 'POST' });
                if (reloadRes.ok) {
                    const data = await reloadRes.json();
                    console.log(`[Settings] ❤️ Heartbeat reloaded: Enabled=${data.heartbeat_enabled}, Threshold=${data.proactive_threshold_minutes}min`);
                }
            } catch (e) {
                console.warn('[Settings] Heartbeat reload failed (non-critical):', e);
            }

        } catch (e) {
            console.error('[Settings] Failed to sync characters to backend:', e);
        }


        // ⚡ Sync LLM Settings to Backend Manager (Global Toggle overrides Advanced Routing)
        try {
            console.log('[Settings] Syncing LLM Manager Configuration...');
            // 1. If Custom, update Provider Config first
            if (llmProvider === 'custom') {
                 await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/providers/custom_provider`, {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({
                         api_key: apiKey,
                         base_url: apiBaseUrl
                     })
                 });
            }

            // 2. Update Routes (Chat, Dreaming, Memory) based on Global Toggle
            const targetProvider = llmProvider === 'free' ? 'free_tier' : 'custom_provider';
            // ⚡ Fix: Use selected modelName for Free Tier too! (Don't hardcode gpt-4o-mini)
            const targetModel = modelName;

            const features = ['chat', 'dreaming', 'memory']; // Core features to sync
            
            await Promise.all(features.map(feature => 
                fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/routes/${feature}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider_id: targetProvider,
                        model: targetModel
                    })
                })
            ));
            console.log(`[Settings] ✅ LLM Routes synced to ${targetProvider}`);
            
            // Refresh Manager Data for UI
            fetchLlmManagerData();

        } catch (e) {
             console.error('[Settings] Failed to sync LLM Manager settings:', e);
        }

        // ⚡ Construct Updated Characters List with Global Settings
        const updatedCharacters = characters.map(char => ({
            ...char,
            galgameModeEnabled: globalGalgameEnabled,
            soulEvolutionEnabled: globalSoulEvolutionEnabled, // ⚡ Update local
            proactiveChatEnabled: globalProactiveEnabled,
            heartbeatEnabled: globalHeartbeatEnabled,
            proactiveThresholdMinutes: globalProactiveThreshold,
            bilibili: {
                enabled: globalBilibiliEnabled,
                roomId: parseInt(globalBilibiliRoomId) || 0
            }
        }));

        // 触发回调 (Use updated characters)
        if (onContextWindowChange) onContextWindowChange(contextWindow);
        if (onLLMSettingsChange) onLLMSettingsChange(apiKey, apiBaseUrl, modelName, temperature);
        if (onCharactersUpdated) onCharactersUpdated(updatedCharacters, activeCharacterId); // Pass NEW list
        if (onUserNameUpdated) onUserNameUpdated(userName);
        if (onLive2DHighDpiChange) onLive2DHighDpiChange(highDpiEnabled);
        if (onThinkingModeChange) onThinkingModeChange(thinkingEnabled); // ⚡ Callback

        // ⚡ 同步用户名到后端（批量 API）
        try {
            console.log(`[Settings] Syncing user name to backend (Bulk): ${userName}`);
            await fetch(`${API_CONFIG.BASE_URL}/soul/user_name_bulk`, { // Use backend URL properly
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_name: userName })
            });
            console.log('[Settings] ✅ User name bulk synced');
        } catch (e) {
            console.error('[Settings] Failed to sync user name to backend:', e);
        }
        
        setIsSaving(false);
        onClose();
    };



    const handleClearHistory = () => {
        if (confirm('确定要清空所有对话历史吗？此操作不可恢复。')) {
            if (onClearHistory) onClearHistory();
            alert('对话历史已清空');
        }
    };

    // Character Management Handlers
    const handleAddCharacter = () => {
        const timestamp = Date.now();
        // Use a temporary ID for new characters
        const tempId = `new_${timestamp}`;
        
        const newChar: CharacterProfile = {
            id: tempId,
            name: 'New Character',
            description: 'A new digital soul.',
            systemPrompt: 'You are a helpful AI assistant.',
            voiceConfig: {
                service: 'gpt-sovits',
                voiceId: 'default',
                rate: '+0%',
                pitch: '+0Hz'
            }
        };
        setCharacters([...characters, newChar]);
        setEditingCharId(newChar.id);
    };

    const handleDeleteCharacter = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (characters.length <= 1) {
            alert("必须至少保留一个角色!");
            return;
        }
        if (confirm('确定要删除这个角色吗？')) {
            // Track for deletion on save
            setDeletedCharIds([...deletedCharIds, id]);
            
            const newChars = characters.filter(c => c.id !== id);
            setCharacters(newChars);
            if (activeCharacterId === id && newChars.length > 0) {
                 if (onCharacterSwitch) onCharacterSwitch(newChars[0].id);
            }
        }
    };

    const handleUpdateCharacter = (id: string, updates: Partial<CharacterProfile>) => {
        setCharacters(characters.map(c => {
            if (c.id === id) {
                const updatedChar = { ...c, ...updates };
                
                // ⚡ 智能 ID 生成逻辑：
                // 如果是新角色（ID 以 "new_" 开头），且用户正在修改名字
                // 自动将 ID 更新为名字的拼音/英文形式
                if (id.startsWith('new_') && updates.name) {
                    // 简单的 slugify: 转小写，空格变下划线，去除非法字符
                    const safeId = updates.name
                        .trim()
                        .toLowerCase()
                        .replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_') // 保留中文、英文、数字、下划线
                        .replace(/_+/g, '_'); // 合并多个下划线
                    
                    if (safeId.length > 0) {
                        updatedChar.id = safeId;
                        // 同时更新 editingCharId 以保持焦点
                        // 注意：Changing ID while editing might cause focus loss if key uses ID. 
                        // But React usually handles this if key is stable or index-based (here using random keys in map might help, but let's see).
                    }
                }
                return updatedChar;
            }
            return c;
        }));
        
        // 如果 ID 变了，我们需要更新 editingCharId 和 deletedCharIds (如果是在未保存状态下)
        // 但由于是在 map 里面改的，我们在外面很难捕捉。
        // 为了简化，我们只在 map 里修改。如果 editingCharId 失效了，用户可能需要重新点一下编辑，但这比逻辑复杂要好。
        // 实际上，如果 updates.name 导致 id 变化，我们需要同步更新 editingCharId，否则编辑框会关掉。
        
        if (id.startsWith('new_') && updates.name) {
             const safeId = updates.name.trim().toLowerCase().replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_').replace(/_+/g, '_');
             if (safeId.length > 0) {
                 setEditingCharId(safeId);
             }
        }
    };

    const handleVoiceConfigChange = (id: string, key: string, value: any) => {
         setCharacters(prev => prev.map(c => {
            if (c.id !== id) return c;
            return {
                ...c,
                voiceConfig: {
                    ...c.voiceConfig,
                    [key]: value
                }
            };
         }));
    };

    const handleActivateCharacter = (id: string) => {
        console.log(`[SettingsModal] Set as Active clicked for: ${id}`);
        if (onCharacterSwitch) {
            console.log('[SettingsModal] Invoking onCharacterSwitch callback');
            onCharacterSwitch(id); // Only notify parent, parent updates prop
        } else {
            console.error('[SettingsModal] onCharacterSwitch prop is missing!');
        }
    };



    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 3000,
            backdropFilter: 'blur(3px)'
        }}>
            <div style={{
                backgroundColor: 'white', borderRadius: '12px', width: '600px', height: '600px', // Fixed height
                boxShadow: '0 8px 30px rgba(0,0,0,0.2)',
                display: 'flex', flexDirection: 'column',
                fontFamily: '"Segoe UI", Roboto, Helvetica, Arial, sans-serif',
                overflow: 'hidden'
            }}>
                {/* Header */}
                <div style={{ padding: '20px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ margin: 0, fontSize: '20px', color: '#1a1a1a', fontWeight: 600 }}>Settings</h2>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {(['general', 'voice', 'memory', 'characters', 'interaction'] as Tab[]).map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                style={{
                                    padding: '6px 12px',
                                    borderRadius: '6px',
                                    border: 'none',
                                    background: activeTab === tab ? '#e0e7ff' : 'transparent',
                                    color: activeTab === tab ? '#4f46e5' : '#666',
                                    cursor: 'pointer',
                                    fontWeight: activeTab === tab ? 600 : 400,
                                    textTransform: 'capitalize',
                                    fontSize: '14px',
                                    transition: 'all 0.2s'
                                }}
                            >
                                {tab === 'general' ? 'General' : tab}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content Area */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '20px', backgroundColor: '#f9fafb' }}>

                    {/* General / LLM Tab */}
                    {activeTab === 'general' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            <section>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>User Profile</h3>
                                <div style={{ marginBottom: 15 }}>
                                    <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Your Name (What AI calls you)</label>
                                    <input
                                        value={userName}
                                        onChange={(e) => setUserName(e.target.value)}
                                        style={inputStyle}
                                        placeholder="Master"
                                    />
                                </div>
                            </section>

                            <section>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>LLM Configuration</h3>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    
                                    {/* Provider Switch */}
                                    <div style={{ display: 'flex', gap: '10px', marginBottom: '5px' }}>
                                        <button
                                            onClick={() => {
                                                setLlmProvider('free');
                                                setApiBaseUrl(`${API_CONFIG.BASE_URL}/free-llm/v1`);
                                                setModelName('gpt-4o-mini');
                                                setApiKey('sk-free-demo'); 

                                                // ⚡ Visual Sync: Update routes to reflect Free changes immediately (Optimistic)
                                                setLlmRoutes(prev => prev.map(r => ({
                                                    ...r,
                                                    provider_id: 'free_tier',
                                                    model: 'gpt-4o-mini'
                                                })));
                                            }}
                                            style={{
                                                flex: 1, padding: '8px', borderRadius: '6px', cursor: 'pointer',
                                                border: llmProvider === 'free' ? '1px solid #4f46e5' : '1px solid #e5e7eb',
                                                backgroundColor: llmProvider === 'free' ? '#eef2ff' : 'white',
                                                color: llmProvider === 'free' ? '#4f46e5' : '#374151',
                                                fontWeight: 600, fontSize: '13px'
                                            }}
                                        >
                                            🚀 Free AI (免配置)
                                        </button>
                                        <button
                                            onClick={() => {
                                                setLlmProvider('custom');
                                                setApiBaseUrl('https://api.deepseek.com/v1');
                                                setModelName('deepseek-chat');

                                                // ⚡ Visual Sync: Update routes to reflect Custom changes immediately (Optimistic)
                                                setLlmRoutes(prev => prev.map(r => ({
                                                    ...r,
                                                    provider_id: 'custom_provider',
                                                    model: 'deepseek-chat'
                                                })));
                                            }}
                                            style={{
                                                flex: 1, padding: '8px', borderRadius: '6px', cursor: 'pointer',
                                                border: llmProvider === 'custom' ? '1px solid #4f46e5' : '1px solid #e5e7eb',
                                                backgroundColor: llmProvider === 'custom' ? '#eef2ff' : 'white',
                                                color: llmProvider === 'custom' ? '#4f46e5' : '#374151',
                                                fontWeight: 600, fontSize: '13px'
                                            }}
                                        >
                                            🔧 Custom / DeepSeek
                                        </button>
                                    </div>

                                    {/* Settings based on Provider */}
                                    {llmProvider === 'free' ? (
                                        <>
                                            <div>
                                                <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Model</label>
                                                <select
                                                    value={modelName}
                                                    onChange={(e) => {
                                                        const newVal = e.target.value;
                                                        setModelName(newVal);
                                                        
                                                        // ⚡ Visual Sync: Update routes when main model changes
                                                        setLlmRoutes(prev => prev.map(r => ({
                                                            ...r,
                                                            provider_id: 'free_tier',
                                                            model: newVal
                                                        })));
                                                    }}
                                                    style={inputStyle}
                                                >
                                                    <option value="gpt-4o-mini">GPT-4o Mini (Fast & Smart)</option>
                                                    <option value="claude-3-haiku">Claude 3 Haiku</option>
                                                    <option value="llama-3-70b">Llama 3 70B</option>
                                                    <option value="mixtral-8x7b">Mixtral 8x7B</option>
                                                </select>
                                                <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                                                    Based on DuckDuckGo AI. No API Key required.
                                                </div>
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <div>
                                                <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>API Host</label>
                                                <input
                                                    value={apiBaseUrl}
                                                    onChange={(e) => setApiBaseUrl(e.target.value)}
                                                    style={inputStyle}
                                                    placeholder="https://api.deepseek.com/v1"
                                                />
                                            </div>
                                            <div>
                                                <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>API Key</label>
                                                <input
                                                    type="password"
                                                    value={apiKey}
                                                    onChange={(e) => setApiKey(e.target.value)}
                                                    style={inputStyle}
                                                    placeholder="sk-..."
                                                />
                                            </div>
                                            <div>
                                                <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Model Name</label>
                                                <input
                                                    value={modelName}
                                                    onChange={(e) => setModelName(e.target.value)}
                                                    style={inputStyle}
                                                    placeholder="deepseek-chat"
                                                />
                                            </div>
                                            
                                            <div>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                                    <label style={{ fontSize: '13px', color: '#6b7280' }}>Temperature (Creativity)</label>
                                                    <span style={{ fontSize: '12px', color: '#6366f1', fontWeight: 600 }}>{temperature}</span>
                                                </div>
                                                <input
                                                    type="range"
                                                    min="0"
                                                    max="2"
                                                    step="0.1"
                                                    value={temperature}
                                                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                                    style={{ width: '100%', cursor: 'pointer', accentColor: '#6366f1' }}
                                                />
                                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#9ca3af' }}>
                                                    <span>Precise (0.0)</span>
                                                    <span>Balanced (0.7)</span>
                                                    <span>Creative (1.3+)</span>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                                
                                {/* ⚡ Advanced Route Config */}
                                <div style={{ marginTop: '15px' }}>
                                    {/* ⚡ Hide Advanced Routing for Free Tier (Auto-managed) */}
                                    {llmProvider !== 'free' && (
                                        <button 
                                            onClick={() => setAdvancedModelTab(!advancedModelTab)}
                                            style={{ fontSize: '12px', color: '#4f46e5', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                                        >
                                            {advancedModelTab ? 'Hide Advanced Model Routing' : 'Show Advanced Model Routing (Per-Feature Configuration)'}
                                        </button>
                                    )}
                                    
                                    {llmProvider === 'free' && (
                                         <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '8px', fontStyle: 'italic' }}>
                                            ✨ Free Mode actively manages memory optimization for you. (Advanced routing disabled)
                                        </div>
                                    )}
                                    
                                    {advancedModelTab && llmProvider !== 'free' && (
                                        <div style={{ marginTop: '10px', background: '#eef2ff', padding: '10px', borderRadius: '8px', border: '1px solid #c7d2fe' }}>
                                            <div style={{ fontSize: '12px', fontWeight: 600, color: '#374151', marginBottom: '8px' }}>Feature Routing</div>
                                            
                                            {llmRoutes.map(route => {
                                                const currentProv = llmProviders.find(p => p.id === route.provider_id);
                                                return (
                                                    <div key={route.feature} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '12px' }}>
                                                        <div style={{ width: '80px', fontWeight: 500, textTransform: 'capitalize' }}>{route.feature}</div>
                                                        
                                                        <select 
                                                            value={route.provider_id} 
                                                            onChange={(e) => handleRouteUpdate(route.feature, e.target.value, route.model)}
                                                            style={{ ...inputStyle, width: '120px', padding: '4px' }}
                                                        >
                                                            {llmProviders.map(p => (
                                                                <option key={p.id} value={p.id}>{p.id}</option>
                                                            ))}
                                                        </select>
                                                        
                                                        <select 
                                                            value={route.model}
                                                            onChange={(e) => handleRouteUpdate(route.feature, route.provider_id, e.target.value)}
                                                            style={{ ...inputStyle, width: '150px', padding: '4px' }}
                                                        >
                                                            {/* Show models from current provider */}
                                                            {currentProv?.models?.map((m: string) => (
                                                                <option key={m} value={m}>{m}</option>
                                                            ))}
                                                            {/* Fallback if model not in list */}
                                                            {!currentProv?.models?.includes(route.model) && <option value={route.model}>{route.model}</option>}
                                                        </select>

                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '4px' }}>
                                                            {/* Temperature */}
                                                            <div title="Temperature (0.0-2.0)" style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                                                                <span style={{ fontSize: '10px' }}>🌡️</span>
                                                                <input
                                                                    type="number" step="0.1" min="0" max="2"
                                                                    value={route.temperature ?? 0.7}
                                                                    onChange={(e) => handleRouteUpdate(route.feature, route.provider_id, route.model, parseFloat(e.target.value), route.top_p, route.presence_penalty, route.frequency_penalty)}
                                                                    style={{ ...inputStyle, width: '45px', padding: '2px' }}
                                                                />
                                                            </div>
                                                            {/* Top P */}
                                                            <div title="Top P (0.0-1.0)" style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                                                                <span style={{ fontSize: '10px' }}>🎯</span>
                                                                <input
                                                                    type="number" step="0.05" min="0" max="1"
                                                                    value={route.top_p ?? 1.0}
                                                                    onChange={(e) => handleRouteUpdate(route.feature, route.provider_id, route.model, route.temperature, parseFloat(e.target.value), route.presence_penalty, route.frequency_penalty)}
                                                                    style={{ ...inputStyle, width: '45px', padding: '2px' }}
                                                                />
                                                            </div>
                                                            {/* Presence Penalty */}
                                                            <div title="Presence Penalty (0.0-2.0)" style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                                                                <span style={{ fontSize: '10px' }}>🆕</span>
                                                                <input
                                                                    type="number" step="0.1" min="0" max="2"
                                                                    value={route.presence_penalty ?? 0.0}
                                                                    onChange={(e) => handleRouteUpdate(route.feature, route.provider_id, route.model, route.temperature, route.top_p, parseFloat(e.target.value), route.frequency_penalty)}
                                                                    style={{ ...inputStyle, width: '45px', padding: '2px' }}
                                                                />
                                                            </div>
                                                            {/* Frequency Penalty */}
                                                            <div title="Frequency Penalty (0.0-2.0)" style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                                                                <span style={{ fontSize: '10px' }}>🔁</span>
                                                                <input
                                                                    type="number" step="0.1" min="0" max="2"
                                                                    value={route.frequency_penalty ?? 0.0}
                                                                    onChange={(e) => handleRouteUpdate(route.feature, route.provider_id, route.model, route.temperature, route.top_p, route.presence_penalty, parseFloat(e.target.value))}
                                                                    style={{ ...inputStyle, width: '45px', padding: '2px' }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                    {/* ⚡ DeepSeek Thinking Mode Toggle */}
                                    {llmProvider === 'custom' && (
                                        <div style={{ padding: '12px', border: '1px solid #eee', borderRadius: '8px', marginBottom: '16px', backgroundColor: '#f9fafb' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                                                <label style={{ ...labelStyle, fontSize: '13px', color: '#6366f1' }}>
                                                    🧠 DeepSeek 思考模式 (Thinking Mode)
                                                </label>
                                                <label className="switch" style={{ position: 'relative', display: 'inline-block', width: '36px', height: '20px' }}>
                                                    <input 
                                                        type="checkbox" 
                                                        checked={thinkingEnabled}
                                                        onChange={(e) => setThinkingEnabled(e.target.checked)}
                                                        style={{ opacity: 0, width: 0, height: 0 }}
                                                    />
                                                    <span style={{ 
                                                        position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0, 
                                                        backgroundColor: thinkingEnabled ? '#6366f1' : '#ccc', borderRadius: '20px', transition: '.4s' 
                                                    }}>
                                                        <span style={{ 
                                                            position: 'absolute', content: '""', height: '16px', width: '16px', left: '2px', bottom: '2px', 
                                                            backgroundColor: 'white', borderRadius: '50%', transition: '.4s',
                                                            transform: thinkingEnabled ? 'translateX(16px)' : 'translateX(0)'
                                                        }}></span>
                                                    </span>
                                                </label>
                                            </div>
                                            <div style={{ fontSize: '12px', color: '#666' }}>
                                                启用后将使用 Chain of Thought (Reasoning) 进行深度思考，展示即时思考过程。
                                                <br/>
                                                <span style={{ fontSize: '11px', color: '#999' }}>注意：需要支持 deepseek-reasoner 或兼容的 API 端点。</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </section>

                            <section>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Visual Settings</h3>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: 'white', padding: '12px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                    <input
                                        type="checkbox"
                                        checked={highDpiEnabled}
                                        onChange={(e) => setHighDpiEnabled(e.target.checked)}
                                        style={{ height: '16px', width: '16px', cursor: 'pointer' }}
                                    />
                                    <div>
                                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>Enable High-DPI (Retina) Rendering</div>
                                        <div style={{ fontSize: '12px', color: '#6b7280' }}>Significantly improves quality on high-res screens but increases GPU usage.</div>
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}

                    {/* Interaction Tab (New Global Tab) */}
                    {activeTab === 'interaction' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            <section>
                                 <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Global Interaction Control</h3>
                                 <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                     
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                        {/* 0. Galgame Mode (Master Switch) */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <input
                                                type="checkbox"
                                                checked={globalGalgameEnabled}
                                                onChange={(e) => setGlobalGalgameEnabled(e.target.checked)}
                                                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                            />
                                            <div>
                                                <div style={{ fontSize: '13px', color: '#1f2937', fontWeight: 500 }}>Enable Galgame System (恋爱养成系统)</div>
                                                <div style={{ fontSize: '11px', color: '#6b7280' }}>Enable Intimacy, Mood, Energy mechanics & Context injection.</div>
                                            </div>
                                        </div>
                                        
                                        {/* 0.5 Soul Evolution (Logic Switch) */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <input
                                                type="checkbox"
                                                checked={globalSoulEvolutionEnabled}
                                                onChange={(e) => setGlobalSoulEvolutionEnabled(e.target.checked)}
                                                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                            />
                                            <div>
                                                <div style={{ fontSize: '13px', color: '#1f2937', fontWeight: 500 }}>Enable Soul Evolution (性格自动演化)</div>
                                                <div style={{ fontSize: '11px', color: '#6b7280' }}>Allow AI personality (MBTI, Mood) to change based on conversation.</div>
                                            </div>
                                        </div>

                                        {/* 1. Master Switch: Proactive Chat */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <input
                                                type="checkbox"
                                                checked={globalProactiveEnabled}
                                                // disabled={!globalGalgameEnabled} // Decoupled as requested
                                                onChange={(e) => setGlobalProactiveEnabled(e.target.checked)}
                                                style={{ width: '16px', height: '16px', cursor: 'pointer' }} // Opacity removed
                                            />
                                            <div>
                                                <div style={{ fontSize: '13px', color: '#1f2937', fontWeight: 500 }}>
                                                    Enable Proactive Chat (主动搭话模式)
                                                </div>
                                                <div style={{ fontSize: '11px', color: '#9ca3af' }}>AI will initiate conversation when idle (applies to all characters).</div>
                                            </div>
                                        </div>

                                        {/* 2. Strategy Settings */}
                                        {globalProactiveEnabled && (
                                            <div style={{ marginLeft: '24px', paddingLeft: '10px', borderLeft: '2px solid #e5e7eb', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                                {/* Custom Duration Toggle */}
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                    <input
                                                        type="checkbox"
                                                        checked={globalHeartbeatEnabled}
                                                        onChange={(e) => setGlobalHeartbeatEnabled(e.target.checked)}
                                                        style={{ width: '14px', height: '14px', cursor: 'pointer' }}
                                                    />
                                                     <div style={{ fontSize: '13px', color: '#374151' }}>Use Custom Silence Duration</div>
                                                </div>

                                                {/* Duration Input */}
                                                {globalHeartbeatEnabled ? (
                                                     <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                                                        <label style={{ fontSize: '12px', color: '#6b7280' }}>Silence (mins):</label>
                                                        <input
                                                            type="number"
                                                            min="0.1"
                                                            max="120"
                                                            step="0.1"
                                                            value={globalProactiveThreshold}
                                                            onChange={(e) => setGlobalProactiveThreshold(Number(e.target.value))}
                                                            style={{ ...inputStyle, width: '80px', padding: '4px 8px' }}
                                                        />
                                                    </div>
                                                ) : (
                                                    <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                                        Using <strong>Auto-Intimacy Mode</strong> (Duration depends on character's relationship level).
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                    <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#f9fafb', borderRadius: '4px', border: '1px dashed #d1d5db', fontSize: '12px', color: '#6b7280' }}>
                                        🎨 <strong>Note:</strong> These settings control the interaction logic for ALL characters. Audio and Voice settings are still individual per character card.
                                    </div>
                                 </div>
                            </section>

                            <section>
                                 <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Live Streaming Integration (Plugin)</h3>
                                 <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                                        <input
                                            type="checkbox"
                                            checked={globalBilibiliEnabled}
                                            onChange={(e) => setGlobalBilibiliEnabled(e.target.checked)}
                                            style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                        />
                                        <div>
                                            <div style={{ fontSize: '13px', color: '#1f2937', fontWeight: 500 }}>
                                                Enable Bilibili Danmaku Monitor (B站弹幕监听)
                                            </div>
                                            <div style={{ fontSize: '11px', color: '#9ca3af' }}>Allow AI to read and respond to live comments.</div>
                                        </div>
                                    </div>

                                    {globalBilibiliEnabled && (
                                        <div style={{ marginLeft: '24px' }}>
                                            <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Bilibili Room ID</label>
                                            <input
                                                type="text"
                                                value={globalBilibiliRoomId}
                                                onChange={(e) => setGlobalBilibiliRoomId(e.target.value)}
                                                style={{ ...inputStyle, width: '150px' }}
                                                placeholder="e.g. 123456"
                                            />
                                        </div>
                                    )}
                                 </div>
                            </section>
                        </div>
                    )}
                    {activeTab === 'voice' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            <div>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Audio Input Device</h3>
                                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                    <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Microphone</label>
                                    <select
                                        value={currentAudioDevice || ''}
                                        onChange={handleAudioDeviceChange}
                                        style={inputStyle}
                                    >
                                        {audioDevices.length > 0 ? audioDevices.map(dev => (
                                            <option key={dev.index} value={dev.name}>
                                                {dev.name} ({dev.channels} ch)
                                            </option>
                                        )) : <option>No devices found</option>}
                                    </select>
                                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                                        💡 Select your physical microphone to avoid system audio loopback
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Voice Recognition (STT)</h3>
                                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                    {/* Dropdown 1: STT Engine Selection */}
                                    <div style={{ marginBottom: '10px' }}>
                                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>STT Engine (方案)</label>
                                        <select
                                            value={sttEngineType}
                                            onChange={(e) => {
                                                const newEngine = e.target.value;
                                                setSttEngineType(newEngine);
                                                // Auto-switch logic
                                                if (newEngine === 'sense_voice') {
                                                    handleSttModelChange({ target: { value: 'sense-voice' } } as any);
                                                } else if (newEngine === 'paraformer_zh') {
                                                    handleSttModelChange({ target: { value: 'paraformer-zh' } } as any);
                                                } else if (newEngine === 'paraformer_en') {
                                                    handleSttModelChange({ target: { value: 'paraformer-en' } } as any);
                                                } else {
                                                    handleSttModelChange({ target: { value: 'base' } } as any);
                                                }
                                            }}
                                            style={inputStyle}
                                        >
                                            <option value="sense_voice">SenseVoice (推荐 - 多语言/情感)</option>
                                            <option value="paraformer_zh">Paraformer (中文专用/会议级)</option>
                                            <option value="paraformer_en">Paraformer (English Only)</option>
                                            <option value="faster_whisper">Faster-Whisper (通用 - 可选大小)</option>
                                        </select>
                                    </div>

                                    {/* Dropdown 2: Model Selection (Dynamic based on Engine) */}
                                    <div style={{ marginBottom: '5px' }}>
                                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Model (模型)</label>
                                        <select
                                            value={currentWhisperModel}
                                            onChange={handleSttModelChange}
                                            disabled={loadingStatus === 'loading'}
                                            style={inputStyle}
                                        >
                                            {/* Show models relevant to the selected engine */}
                                            {whisperModels.filter(m => {
                                                if (sttEngineType === 'faster_whisper') return m.engine === 'faster_whisper';
                                                if (sttEngineType === 'sense_voice') return m.name === 'sense-voice';
                                                if (sttEngineType === 'paraformer_zh') return m.name === 'paraformer-zh';
                                                if (sttEngineType === 'paraformer_en') return m.name === 'paraformer-en';
                                                return false;
                                            }).map(m => (
                                                <option key={m.name} value={m.name}>
                                                    {m.name} ({m.desc})
                                                    {m.download_status === 'downloading' ? ' [Downloading...]' : ''}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {loadingStatus === 'loading' && <div style={{ 
                                        fontSize: '12px', color: '#2563eb', marginTop: '8px', 
                                        backgroundColor: '#eff6ff', padding: '8px', borderRadius: '6px',
                                        display: 'flex', alignItems: 'center', gap: '6px'
                                    }}>
                                        <span className="spinner">⏳</span> 
                                        <span>正在切换/下载模型，请留意控制台日志...</span>
                                    </div>}
                                </div>
                            </div>

                            {/* VAD Settings */}
                            <div>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>语音活动检测 (VAD Settings)</h3>
                                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '20px' }}>
                                    
                                    {/* Sensitivity Slider */}
                                    <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <label style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                                触发灵敏度 (Start Threshold)
                                            </label>
                                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                                {vadStartThreshold.toFixed(2)}
                                            </span>
                                        </div>
                                        <input
                                            type="range"
                                            min="0.3"
                                            max="0.95"
                                            step="0.05"
                                            value={vadStartThreshold}
                                            onChange={(e) => handleVadChange('speech_start_threshold', parseFloat(e.target.value))}
                                            style={{ width: '100%', cursor: 'pointer' }}
                                        />
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                                            <span>容易触发 (0.3)</span>
                                            <span>严格过滤 (0.95)</span>
                                        </div>
                                    </div>

                                    {/* Pause Tolerance Slider */}
                                    <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <label style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                                断句延迟 (End Threshold)
                                            </label>
                                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                                {vadEndThreshold.toFixed(2)}
                                            </span>
                                        </div>
                                        <input
                                            type="range"
                                            min="0.01"
                                            max="0.3"
                                            step="0.01"
                                            value={vadEndThreshold}
                                            onChange={(e) => handleVadChange('speech_end_threshold', parseFloat(e.target.value))}
                                            style={{ width: '100%', cursor: 'pointer' }}
                                        />
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                                            <span>容忍停顿 (0.01)</span>
                                            <span>快速切断 (0.3)</span>
                                        </div>
                                        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                                            ⚠️ 值越小，允许的停顿越长 (更不容易被打断)。建议 0.05 - 0.15。
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>声纹过滤 (Voiceprint Filter)</h3>
                                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                    {/* Enable Toggle */}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                                        <input
                                            type="checkbox"
                                            checked={voiceprintEnabled}
                                            onChange={(e) => handleVoiceprintToggle(e.target.checked)}
                                            style={{ height: '16px', width: '16px', cursor: 'pointer' }}
                                        />
                                        <div>
                                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>启用声纹验证</div>
                                            <div style={{ fontSize: '12px', color: '#6b7280' }}>只接受你的声音，过滤环境噪声和他人语音</div>
                                        </div>
                                    </div>

                                    {/* Threshold Slider */}
                                    <div style={{ marginBottom: '15px' }}>
                                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '6px' }}>
                                            相似度阈值: <strong style={{ color: '#1f2937' }}>{voiceprintThreshold.toFixed(2)}</strong>
                                        </label>
                                        <input
                                            type="range"
                                            min="0.1"
                                            max="0.9"
                                            step="0.05"
                                            value={voiceprintThreshold}
                                            onChange={(e) => handleVoiceprintThresholdChange(Number(e.target.value))}
                                            disabled={!voiceprintEnabled}
                                            style={{ width: '100%', accentColor: '#4f46e5' }}
                                        />
                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                                            低阈值=容易通过 | 高阈值=严格过滤
                                        </div>
                                    </div>

                                    {/* Profile Name */}
                                    <div style={{ marginBottom: '15px' }}>
                                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Profile 名称</label>
                                        <input
                                            type="text"
                                            value={voiceprintProfile}
                                            onChange={(e) => setVoiceprintProfile(e.target.value)}
                                            style={inputStyle}
                                            placeholder="default"
                                        />
                                    </div>

                                    {/* Status */}
                                    {voiceprintStatus && (
                                        <div style={{
                                            fontSize: '12px',
                                            padding: '8px',
                                            borderRadius: '6px',
                                            backgroundColor: voiceprintStatus.includes('✓') ? '#d1fae5' : '#fef3c7',
                                            color: voiceprintStatus.includes('✓') ? '#065f46' : '#92400e',
                                            textAlign: 'center',
                                            marginBottom: '10px'
                                        }}>
                                            {voiceprintStatus}
                                        </div>
                                    )}

                                    <div style={{ fontSize: '11px', color: '#9ca3af', lineHeight: '1.4' }}>
                                        💡 <strong>使用提示：</strong><br />
                                        1. 运行 <code>python python_backend/register_voiceprint.py</code><br />
                                        2. 启用声纹验证开关<br />
                                        3. 调整阈值以达到最佳效果<br />
                                        4. 重启 stt_server.py 使配置生效
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Memory Tab */}
                    {activeTab === 'memory' && (
                        <div>
                            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Conversation Memory</h3>
                            <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
                                    Context Window: <strong>{contextWindow} turns</strong>
                                </label>
                                <input
                                    type="range"
                                    min="5"
                                    max="50"
                                    value={contextWindow}
                                    onChange={(e) => setContextWindow(Number(e.target.value))}
                                    style={{ width: '100%', accentColor: '#4f46e5' }}
                                />
                                <div style={{ marginTop: '20px' }}>
                                    <button
                                        onClick={handleClearHistory}
                                        style={{ ...buttonStyle, backgroundColor: '#fee2e2', color: '#dc2626', border: '1px solid #fecaca' }}
                                    >
                                        Clear History & Reset
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Characters Tab (New) */}
                    {activeTab === 'characters' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#374151' }}>Character Profiles ({characters.length})</h3>
                                <button onClick={handleAddCharacter} style={{ ...buttonStyle, padding: '4px 10px', fontSize: '12px' }}>+ Add New</button>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {[...characters].sort((a, b) => {
                                    if (a.id === activeCharacterId) return -1;
                                    if (b.id === activeCharacterId) return 1;
                                    return 0;
                                }).map(char => {
                                    const isExpanded = editingCharId === char.id;
                                    const isActive = activeCharacterId === char.id;

                                    return (
                                        <div key={char.id} style={{
                                            backgroundColor: 'white', borderRadius: '8px',
                                            border: isActive ? '2px solid #6366f1' : '1px solid #e5e7eb',
                                            overflow: 'hidden', transition: 'all 0.2s',
                                            boxShadow: isActive ? '0 4px 6px -1px rgba(99, 102, 241, 0.1), 0 2px 4px -1px rgba(99, 102, 241, 0.06)' : 'none'
                                        }}>
                                            {/* Card Header */}
                                            <div
                                                onClick={() => handleActivateCharacter(char.id)}
                                                style={{
                                                    padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                    cursor: 'pointer', backgroundColor: isActive ? '#f5f7ff' : 'white'
                                                }}
                                                title="点击切换到此角色"
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
                                                    <div style={{
                                                        width: '32px', height: '32px', borderRadius: '50%', backgroundColor: isActive ? '#c7d2fe' : '#e0e7ff',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px'
                                                    }}>
                                                        {char.avatar ? '🖼️' : (char.id.startsWith('new_') ? '🆕' : '👤')}
                                                    </div>
                                                    <div>
                                                        <div style={{ fontWeight: 600, fontSize: '14px', color: '#1f2937' }}>
                                                            {char.name} 
                                                            {isActive && <span style={{ fontSize: '11px', color: '#ffffff', backgroundColor: '#6366f1', padding: '2px 8px', borderRadius: '10px', marginLeft: '8px' }}>Active</span>}
                                                        </div>
                                                        <div style={{ fontSize: '12px', color: '#6b7280' }}>{char.description}</div>
                                                    </div>
                                                </div>
                                                
                                                {/* Edit Toggle Button (Independent) */}
                                                <div 
                                                    onClick={(e) => {
                                                        e.stopPropagation(); // 防止触发切换
                                                        setEditingCharId(isExpanded ? null : char.id);
                                                    }}
                                                    style={{ 
                                                        padding: '8px', 
                                                        borderRadius: '4px',
                                                        color: '#9ca3af',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        minWidth: '30px'
                                                    }}
                                                    title={isExpanded ? "收起编辑" : "编辑详情"}
                                                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f3f4f6')}
                                                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                                                >
                                                    {isExpanded ? '▲' : '⚙️'}
                                                </div>
                                            </div>

                                            {/* Expanded Edit Form */}
                                            {isExpanded && (
                                                <div style={{ padding: '15px', borderTop: '1px solid #f3f4f6', backgroundColor: '#fff' }} onClick={(e) => e.stopPropagation()}>
                                                    
                                                    {/* Folder Name / ID Display */}
                                                    <div style={{ marginBottom: '10px' }}>
                                                        <label style={labelStyle}>
                                                            Folder Name / ID
                                                            <span style={{ fontWeight: 400, color: '#9ca3af', marginLeft: '5px', fontSize: '11px' }}>
                                                                {char.id.startsWith('new_') ? '(将作为文件夹名)' : '(不可修改)'}
                                                            </span>
                                                        </label>
                                                        <input
                                                            value={char.id}
                                                            readOnly
                                                            style={{ 
                                                                ...inputStyle, 
                                                                backgroundColor: '#f9fafb', 
                                                                color: char.id.startsWith('new_') ? '#4f46e5' : '#6b7280',
                                                                fontFamily: 'monospace',
                                                                borderColor: char.id.startsWith('new_') ? '#c7d2fe' : '#e5e7eb'
                                                            }}
                                                        />
                                                        {char.id.startsWith('new_') && (
                                                            <div style={{ fontSize: '11px', color: '#6366f1', marginTop: '4px' }}>
                                                                ✨ 输入下方 "Name" 时自动生成
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                                                        <div>
                                                            <label style={labelStyle}>Name</label>
                                                            <input
                                                                value={char.name}
                                                                onChange={(e) => handleUpdateCharacter(char.id, { name: e.target.value })}
                                                                style={inputStyle}
                                                            />
                                                        </div>
                                                        <div>
                                                            <label style={labelStyle}>Brief Description (Card Preview)</label>
                                                            <input
                                                                value={char.description}
                                                                onChange={(e) => handleUpdateCharacter(char.id, { description: e.target.value })}
                                                                style={inputStyle}
                                                                placeholder="一名18岁的活泼可爱的女孩子"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div style={{ marginBottom: '10px' }}>
                                                        <label style={labelStyle}>
                                                            System Prompt (AI Identity)
                                                            <span style={{ fontWeight: 400, color: '#9ca3af', marginLeft: '5px' }}>(Full instructions for AI behavior)</span>
                                                        </label>
                                                        <textarea
                                                            value={char.systemPrompt || ''}
                                                            onChange={(e) => handleUpdateCharacter(char.id, { systemPrompt: e.target.value })}
                                                            style={{ ...inputStyle, minHeight: '100px', fontFamily: 'inherit', fontSize: '13px' }}
                                                            placeholder="你是一个18岁的活泼可爱的女孩子。"
                                                        />
                                                    </div>

                                                    <div style={{ marginBottom: '15px' }}>
                                                        <label style={labelStyle}>Live2D Model</label>
                                                        <select
                                                            value={char.modelPath || '/live2d/Hiyori/Hiyori.model3.json'}
                                                            onChange={(e) => handleUpdateCharacter(char.id, { modelPath: e.target.value })}
                                                            style={inputStyle}
                                                        >
                                                            {AVAILABLE_MODELS.map(m => (
                                                                <option key={m.path} value={m.path}>{m.name}</option>
                                                            ))}
                                                        </select>
                                                    </div>

                                                    <div style={{ marginBottom: '15px' }}>
                                                        <label style={labelStyle}>Voice Configuration</label>

                                                        {/* Service Selection */}
                                                        <div style={{ marginBottom: '8px' }}>
                                                            <select
                                                                value={char.voiceConfig.service || 'edge-tts'}
                                                                onChange={(e) => handleVoiceConfigChange(char.id, 'service', e.target.value)}
                                                                style={{ ...inputStyle, marginBottom: '5px' }}
                                                            >
                                                                <option value="edge-tts">
                                                                    Edge TTS (Cloud / Free) 
                                                                    {activeTtsEngines.includes('Edge TTS') ? ' ✅' : ' ⚠️ Unavailable'}
                                                                </option>
                                                                <option value="gpt-sovits" disabled={!activeTtsEngines.includes('GPT-SoVITS')}>
                                                                    GPT-SoVITS (Local / Emotional) 
                                                                    {activeTtsEngines.includes('GPT-SoVITS') ? ' ✅' : ' ❌ Offline'}
                                                                </option>
                                                            </select>
                                                            {char.voiceConfig.service === 'gpt-sovits' && !activeTtsEngines.includes('GPT-SoVITS') && (
                                                                <div style={{ color: '#ef4444', fontSize: '12px', marginTop: '2px' }}>
                                                                    ⚠️ 该服务未启动，将无法发声 (自动降级到 Edge TTS)
                                                                </div>
                                                            )}
                                                        </div>

                                                        {/* Voice Selection */}
                                                        <div style={{ display: 'flex', gap: '10px' }}>
                                                            <select
                                                                value={char.voiceConfig.voiceId}
                                                                onChange={(e) => handleVoiceConfigChange(char.id, 'voiceId', e.target.value)}
                                                                style={{ ...inputStyle, flex: 2 }}
                                                            >
                                                                {char.voiceConfig.service === 'gpt-sovits' ? (
                                                                    // List GPT-SoVITS Voices
                                                                    gptVoices.length > 0 ? (
                                                                        gptVoices.map(v => (
                                                                            <option key={v.name} value={v.name}>
                                                                                {v.name} (Local Ref)
                                                                            </option>
                                                                        ))
                                                                    ) : <option disabled>No local voices found (Default only)</option>
                                                                ) : (
                                                                    // List Edge TTS Voices
                                                                    edgeVoices.length > 0 ? (
                                                                        <>
                                                                            <optgroup label="中文 (Chinese)">
                                                                                {edgeVoices
                                                                                    .filter(v => v.name.includes('zh-'))
                                                                                    .map(v => (
                                                                                        <option key={v.name} value={v.name}>
                                                                                            {v.name.replace('zh-CN-', '').replace('Neural', '')} ({v.gender})
                                                                                        </option>
                                                                                    ))
                                                                                }
                                                                            </optgroup>
                                                                            <optgroup label="English">
                                                                                {edgeVoices
                                                                                    .filter(v => v.name.includes('en-'))
                                                                                    .map(v => (
                                                                                        <option key={v.name} value={v.name}>
                                                                                            {v.name.replace('en-US-', '').replace('Neural', '')} ({v.gender})
                                                                                        </option>
                                                                                    ))
                                                                                }
                                                                            </optgroup>
                                                                        </>
                                                                    ) : (
                                                                        <option>Loading voices...</option>
                                                                    )
                                                                )}
                                                            </select>

                                                            {/* Rate control - only for Edge for now? or both? GPT-SoVITS params might differ */}
                                                            {char.voiceConfig.service !== 'gpt-sovits' && (
                                                                <input
                                                                    value={char.voiceConfig.rate}
                                                                    onChange={(e) => handleVoiceConfigChange(char.id, 'rate', e.target.value)}
                                                                    style={{ ...inputStyle, flex: 1 }}
                                                                    placeholder="+0%"
                                                                    title="Speed (e.g., +20%, -10%)"
                                                                />
                                                            )}
                                                        </div>
                                                        {char.voiceConfig.service === 'gpt-sovits' && (
                                                            <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                                                                ℹ️ Place reference audio in assets/emotion_audio/{char.voiceConfig.voiceId || 'default_voice'}
                                                            </div>
                                                        )}
                                                    </div>



                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '10px', borderTop: '1px solid #f3f4f6' }}>
                                                        <button
                                                            onClick={(e) => handleDeleteCharacter(char.id, e)}
                                                            style={{ ...buttonStyle, backgroundColor: '#fee2e2', color: '#b91c1c', border: 'none', padding: '6px 12px', fontSize: '12px' }}
                                                        >
                                                            Delete
                                                        </button>

                                                        {activeCharacterId !== char.id && (
                                                            <button
                                                                onClick={() => handleActivateCharacter(char.id)}
                                                                style={{ ...buttonStyle, backgroundColor: '#e0e7ff', color: '#4338ca', border: 'none', padding: '6px 12px', fontSize: '12px' }}
                                                            >
                                                                Set as Active
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={{ padding: '20px', borderTop: '1px solid #eee', display: 'flex', justifyContent: 'flex-end', gap: '10px', backgroundColor: 'white' }}>
                    <button onClick={onClose} disabled={isSaving} style={{ ...buttonStyle, backgroundColor: 'white', border: '1px solid #d1d5db', color: '#374151', opacity: isSaving ? 0.7 : 1 }}>Cancel</button>
                    <button onClick={handleSave} disabled={isSaving} style={{ ...buttonStyle, backgroundColor: '#2563eb', color: 'white', border: 'none', opacity: isSaving ? 0.7 : 1 }}>
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
            <style>{`
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-track { background: transparent; }
                ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
            `}</style>
        </div >
    );
};



export default SettingsModal;
