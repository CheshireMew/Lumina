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
    size: string;
    download_status: 'idle' | 'downloading' | 'completed' | 'failed';
}

type Tab = 'general' | 'voice' | 'memory' | 'characters';

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

                // Whisper & TTS Voices & Audio Devices
                fetchModels();
                fetchTTSVoices();
                fetchAudioDevices();
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

    // Poll status for Whisper models
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isOpen && activeTab === 'voice') {
            interval = setInterval(fetchModels, 2000);
        }
        return () => clearInterval(interval);
    }, [isOpen, activeTab]);

    const fetchModels = async () => {
        try {
            const res = await fetch(`${sttServerUrl}/models/list`);
            if (res.ok) {
                const data = await res.json();
                setWhisperModels(data.models);
                setCurrentWhisperModel(data.current_model);
                setLoadingStatus(data.loading_status);
            }
        } catch (err) {
            console.error("Failed to fetch Whisper models", err);
        }
    };

    const handleWhisperModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        const newModel = e.target.value;
        try {
            await fetch(`${sttServerUrl}/models/switch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: newModel })
            });
            fetchModels();
        } catch (err) {
            alert("Failed to connect to STT server");
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
            description: 'A new AI personality',
            systemPromptTemplate: 'You are {char}, a helpful assistant.',
            voiceConfig: {
                service: 'edge-tts',
                voiceId: 'zh-CN-XiaoxiaoNeural',
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
                                    <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Whisper Model</label>
                                    <select
                                        value={currentWhisperModel}
                                        onChange={handleWhisperModelChange}
                                        disabled={loadingStatus === 'loading'}
                                        style={inputStyle}
                                    >
                                        {whisperModels.length > 0 ? whisperModels.map(m => (
                                            <option key={m.name} value={m.name}>
                                                {m.name.toUpperCase()} ({m.size})
                                                {m.download_status === 'downloading' ? ' [Downloading...]' : ''}
                                                {m.download_status === 'completed' || (m.download_status === 'idle' && m.name === currentWhisperModel) ? ' [Ready]' : ''}
                                            </option>
                                        )) : <option>Connecting...</option>}
                                    </select>
                                    {loadingStatus === 'loading' && <div style={{ fontSize: '12px', color: '#2563eb', marginTop: '5px' }}>Loading/Downloading model...</div>}
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
                                                            <label style={labelStyle}>Description</label>
                                                            <input
                                                                value={char.description}
                                                                onChange={(e) => handleUpdateCharacter(char.id, { description: e.target.value })}
                                                                style={inputStyle}
                                                            />
                                                        </div>
                                                    </div>

                                                    <div style={{ marginBottom: '10px' }}>
                                                        <label style={labelStyle}>
                                                            System Prompt Template
                                                            <span style={{ fontWeight: 400, color: '#9ca3af', marginLeft: '5px' }}>(Optional: Use {'{char}'} for Name, {'{user}'} for User Name)</span>
                                                        </label>
                                                        <textarea
                                                            value={char.systemPromptTemplate}
                                                            onChange={(e) => handleUpdateCharacter(char.id, { systemPromptTemplate: e.target.value })}
                                                            style={{ ...inputStyle, minHeight: '80px', fontFamily: 'monospace', fontSize: '12px' }}
                                                        />
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
