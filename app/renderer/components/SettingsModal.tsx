import React, { useState, useEffect } from 'react';
import { CharacterProfile, DEFAULT_CHARACTERS } from '@core/llm/types';
import { ttsService } from '@core/voice/tts_service';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onClearHistory?: () => void;
    onContextWindowChange?: (newWindow: number) => void;
    onLLMSettingsChange?: (apiKey: string, baseUrl: string, model: string) => void;
    onCharactersUpdated?: (characters: CharacterProfile[], activeId: string) => void;
    onUserNameUpdated?: (newName: string) => void;
    onLive2DHighDpiChange?: (enabled: boolean) => void;
}

interface WhisperModelInfo {
    name: string;
    desc?: string; // Updated from 'size'
    size?: string;
    engine?: string; // Newly added
    download_status: 'idle' | 'downloading' | 'completed' | 'failed';
}

type Tab = 'general' | 'voice' | 'memory' | 'characters';

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

const SettingsModal: React.FC<SettingsModalProps> = ({
    isOpen, onClose, onClearHistory, onContextWindowChange, onLLMSettingsChange, onCharactersUpdated, onUserNameUpdated, onLive2DHighDpiChange
}) => {
    const [activeTab, setActiveTab] = useState<Tab>('general');

    // LLM Settings
    const [apiKey, setApiKey] = useState('');
    const [apiBaseUrl, setApiBaseUrl] = useState('https://api.deepseek.com/v1');
    const [modelName, setModelName] = useState('deepseek-chat');

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

    // Character Settings
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    const [activeCharacterId, setActiveCharacterId] = useState<string>('');
    const [editingCharId, setEditingCharId] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            const loadSettings = async () => {
                const settings = (window as any).settings;

                // LLM
                setApiKey(await settings.get('apiKey') || '');
                setApiBaseUrl(await settings.get('apiBaseUrl') || 'https://api.deepseek.com/v1');
                setModelName(await settings.get('modelName') || 'deepseek-chat');
                setUserName(await settings.get('userName') || 'Master');

                // Visual
                setHighDpiEnabled(await settings.get('live2d_high_dpi') || false);

                // Memory
                setContextWindow(await settings.get('contextWindow') || 15);

                // Characters
                const loadedChars = await settings.get('characters') as CharacterProfile[];
                const loadedActiveId = await settings.get('activeCharacterId') as string;
                if (loadedChars) setCharacters(loadedChars);
                if (loadedActiveId) setActiveCharacterId(loadedActiveId);

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

    const fetchTTSVoices = async () => {
        try {
            // Fetch Edge TTS Voices
            try {
                const res = await fetch('http://127.0.0.1:8766/tts/voices?engine=edge-tts');
                if (res.ok) {
                    const data = await res.json();
                    const allVoices = [...(data.chinese || []), ...(data.english || [])];
                    setEdgeVoices(allVoices);
                }
            } catch (e) { console.warn("Failed to fetch Edge voices", e); }

            // Fetch GPT-SoVITS Voices
            try {
                const res = await fetch('http://127.0.0.1:8766/tts/voices?engine=gpt-sovits');
                if (res.ok) {
                    const data = await res.json();
                    setGptVoices(data.voices || []);
                }
            } catch (e) { console.warn("Failed to fetch GPT-SoVITS voices", e); }

        } catch (e) {
            console.error("Failed to fetch TTS voices", e);
        }
    };

    // Audio Devices Fetching
    const fetchAudioDevices = async () => {
        try {
            const res = await fetch(`${sttServerUrl}/audio/devices`);
            if (res.ok) {
                const data = await res.json();
                setAudioDevices(data.devices || []);
                setCurrentAudioDevice(data.current || null);
            }
        } catch (e) {
            console.error("Failed to fetch audio devices", e);
        }
    };

    const handleAudioDeviceChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        const deviceName = e.target.value;
        try {
            const res = await fetch(`${sttServerUrl}/audio/config`, {
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

    // Voiceprint Functions
    const fetchVoiceprintConfig = async () => {
        try {
            const res = await fetch(`${sttServerUrl}/voiceprint/status`);
            if (res.ok) {
                const data = await res.json();
                setVoiceprintEnabled(data.enabled || false);
                setVoiceprintThreshold(data.threshold || 0.6);
                setVoiceprintProfile(data.profile || 'default');
                setVoiceprintStatus(data.profile_loaded ? '✓ 已加载声纹' : '⚠️ 未注册声纹');
            }
        } catch (e) {
            console.warn('Failed to fetch voiceprint config', e);
        }
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
            const res = await fetch(`${sttServerUrl}/audio/config`, {
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
            await fetch(`${sttServerUrl}/audio/config`, {
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
        const settings = (window as any).settings;
        await settings.set('apiKey', apiKey);
        await settings.set('apiBaseUrl', apiBaseUrl);
        await settings.set('modelName', modelName);
        await settings.set('userName', userName);
        await settings.set('contextWindow', contextWindow);
        await settings.set('characters', characters);
        await settings.set('activeCharacterId', activeCharacterId);
        await settings.set('live2d_high_dpi', highDpiEnabled);

        // 保存声纹配置并应用到后端
        if (voiceprintEnabled || voiceprintThreshold !== 0.6 || voiceprintProfile !== 'default') {
            try {
                await fetch(`${sttServerUrl}/audio/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        device_name: currentAudioDevice,
                        enable_voiceprint_filter: voiceprintEnabled,
                        voiceprint_threshold: voiceprintThreshold,
                        voiceprint_profile: voiceprintProfile
                    })
                });

                // Removed alert - check console logs for voiceprint config status
                if (voiceprintEnabled) {
                    console.log('[Settings] Voiceprint configuration saved. Please restart stt_server.py for changes to take effect.');
                }
            } catch (e) {
                console.error('Failed to save voiceprint config', e);
            }
        }

        // 同步配置到后端 core_profile.json
        try {
            // 同步 user_name
            await fetch('http://localhost:8001/soul/update_user_name', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_name: userName })
            });

            // 同步当前活跃角色的 identity (name, description)
            const activeChar = characters.find(c => c.id === activeCharacterId);
            if (activeChar) {
                const payload = {
                    name: activeChar.name,
                    description: activeChar.systemPrompt || activeChar.description
                };
                console.log('[Settings] 📤 Sending to backend:', payload);
                console.log('[Settings] Description length:', payload.description.length, 'chars');
                
                const response = await fetch('http://localhost:8001/soul/update_identity', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log('[Settings] ✅ Backend confirmed:', result);
                } else {
                    console.error('[Settings] ❌ API Error:', response.status, await response.text());
                }
            }
        } catch (e) {
            console.error('[Settings] Failed to sync to backend:', e);
        }

        if (onContextWindowChange) onContextWindowChange(contextWindow);
        if (onLLMSettingsChange) onLLMSettingsChange(apiKey, apiBaseUrl, modelName);
        if (onCharactersUpdated) onCharactersUpdated(characters, activeCharacterId);
        if (onUserNameUpdated) onUserNameUpdated(userName);
        if (onLive2DHighDpiChange) onLive2DHighDpiChange(highDpiEnabled);

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
        const newChar: CharacterProfile = {
            id: `char_${Date.now()}`,
            name: 'New Character',
            description: 'A brief description',
            systemPrompt: 'An 18 years cute human girl with a distinct personality.',
            voiceConfig: {
                service: 'gpt-sovits',
                voiceId: 'default_voice',
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
            const newChars = characters.filter(c => c.id !== id);
            setCharacters(newChars);
            if (activeCharacterId === id) {
                setActiveCharacterId(newChars[0].id);
            }
        }
    };

    const handleUpdateCharacter = (id: string, updates: Partial<CharacterProfile>) => {
        setCharacters(characters.map(c => c.id === id ? { ...c, ...updates } : c));
    };

    const handleVoiceConfigChange = (id: string, field: keyof CharacterProfile['voiceConfig'], value: string) => {
        setCharacters(characters.map(c => {
            if (c.id === id) {
                return {
                    ...c,
                    voiceConfig: { ...c.voiceConfig, [field]: value }
                };
            }
            return c;
        }));

        // Immediately apply voice change if this is the active character and voiceId is being changed
        if (field === 'voiceId' && id === activeCharacterId) {
            console.log(`[SettingsModal] Immediately switching TTS voice to: ${value}`);
            ttsService.setDefaultVoice(value);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000,
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
                        {(['general', 'voice', 'memory', 'characters'] as Tab[]).map(tab => (
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

                    {/* Voice Tab */}
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
                                {characters.map(char => {
                                    const isExpanded = editingCharId === char.id;
                                    const isActive = activeCharacterId === char.id;

                                    return (
                                        <div key={char.id} style={{
                                            backgroundColor: 'white', borderRadius: '8px',
                                            border: isActive ? '2px solid #6366f1' : '1px solid #e5e7eb',
                                            overflow: 'hidden', transition: 'all 0.2s'
                                        }}>
                                            {/* Card Header */}
                                            <div
                                                onClick={() => setEditingCharId(isExpanded ? null : char.id)}
                                                style={{
                                                    padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                    cursor: 'pointer', backgroundColor: isActive ? '#f5f7ff' : 'white'
                                                }}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                    <div style={{
                                                        width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#e0e7ff',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px'
                                                    }}>
                                                        {char.avatar ? '🖼️' : '👤'}
                                                    </div>
                                                    <div>
                                                        <div style={{ fontWeight: 600, fontSize: '14px', color: '#1f2937' }}>{char.name} {isActive && <span style={{ fontSize: '11px', color: '#4f46e5', backgroundColor: '#e0e7ff', padding: '2px 6px', borderRadius: '4px', marginLeft: '6px' }}>Active</span>}</div>
                                                        <div style={{ fontSize: '12px', color: '#6b7280' }}>{char.description}</div>
                                                    </div>
                                                </div>
                                                <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                                                    {isExpanded ? '▲' : '▼'}
                                                </div>
                                            </div>

                                            {/* Expanded Edit Form */}
                                            {isExpanded && (
                                                <div style={{ padding: '15px', borderTop: '1px solid #f3f4f6', backgroundColor: '#fff' }}>
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
                                                            placeholder="你是一个18岁的活泼可爱的女孩子，你正在你的恋人聊天。\n对话一定要使用英语，除非对方问某个东西是什么或者某个单词什么意思。"
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
                                                                <option value="edge-tts">Edge TTS (Cloud / Free)</option>
                                                                <option value="gpt-sovits">GPT-SoVITS (Local / Emotional)</option>
                                                            </select>
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
                                                                onClick={() => setActiveCharacterId(char.id)}
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
                    <button onClick={onClose} style={{ ...buttonStyle, backgroundColor: 'white', border: '1px solid #d1d5db', color: '#374151' }}>Cancel</button>
                    <button onClick={handleSave} style={{ ...buttonStyle, backgroundColor: '#2563eb', color: 'white', border: 'none' }}>Save Changes</button>
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

export default SettingsModal;
