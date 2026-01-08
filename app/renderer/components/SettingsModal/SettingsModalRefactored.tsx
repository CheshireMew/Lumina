/**
 * SettingsModal - 重构版
 * 使用模块化 Tab 组件，支持多角色切换
 */
import React, { useState, useEffect } from 'react';
import { CharacterProfile, DEFAULT_CHARACTERS } from '@core/llm/types';

// 导入模块化组件
import { GeneralTab } from './tabs/GeneralTab';
import { MemoryTab } from './tabs/MemoryTab';
import { VoiceTab } from './tabs/VoiceTab';
import { CharactersTab } from './tabs/CharactersTab';
import { buttonStyle } from './styles';
import { 
    Tab, SettingsModalProps, WhisperModelInfo, AudioDevice, VoiceInfo,
    AVAILABLE_MODELS, STT_SERVER_URL, MEMORY_SERVER_URL 
} from './types';

const SettingsModalRefactored: React.FC<SettingsModalProps> = ({
    isOpen, onClose, onClearHistory, onContextWindowChange, onLLMSettingsChange, 
    onCharactersUpdated, onUserNameUpdated, onLive2DHighDpiChange, onCharacterSwitch,
    activeCharacterId
}) => {
    const [activeTab, setActiveTab] = useState<Tab>('general');
    const [isSaving, setIsSaving] = useState(false);

    // ==================== General Tab State ====================
    const [apiKey, setApiKey] = useState('');
    const [apiBaseUrl, setApiBaseUrl] = useState('https://api.deepseek.com/v1');
    const [modelName, setModelName] = useState('deepseek-chat');
    const [userName, setUserName] = useState('Master');
    const [highDpiEnabled, setHighDpiEnabled] = useState(false);

    // ==================== Memory Tab State ====================
    const [contextWindow, setContextWindow] = useState(15);

    // ==================== Voice Tab State ====================
    const [whisperModels, setWhisperModels] = useState<WhisperModelInfo[]>([]);
    const [currentWhisperModel, setCurrentWhisperModel] = useState('base');
    const [loadingStatus, setLoadingStatus] = useState('idle');
    const [sttEngineType, setSttEngineType] = useState<string>('faster_whisper');
    const [audioDevices, setAudioDevices] = useState<AudioDevice[]>([]);
    const [currentAudioDevice, setCurrentAudioDevice] = useState<string | null>(null);
    const [voiceprintEnabled, setVoiceprintEnabled] = useState(false);
    const [voiceprintThreshold, setVoiceprintThreshold] = useState(0.6);
    const [voiceprintProfile, setVoiceprintProfile] = useState('default');
    const [voiceprintStatus, setVoiceprintStatus] = useState<string>('');
    const [edgeVoices, setEdgeVoices] = useState<VoiceInfo[]>([]);
    const [gptVoices, setGptVoices] = useState<VoiceInfo[]>([]);

    // ==================== Characters Tab State ====================
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    const [editingCharId, setEditingCharId] = useState<string | null>(null);
    const [deletedCharIds, setDeletedCharIds] = useState<string[]>([]);

    // ==================== Load Settings ====================
    useEffect(() => {
        if (isOpen) {
            loadAllSettings();
        }
    }, [isOpen]);

    const loadAllSettings = async () => {
        const settings = (window as any).settings;

        // LLM & User
        setApiKey(await settings.get('apiKey') || '');
        setApiBaseUrl(await settings.get('apiBaseUrl') || 'https://api.deepseek.com/v1');
        setModelName(await settings.get('modelName') || 'deepseek-chat');
        setUserName(await settings.get('userName') || 'Master');
        setHighDpiEnabled(await settings.get('live2d_high_dpi') || false);
        setContextWindow(await settings.get('contextWindow') || 15);

        // Load characters from backend
        await loadCharactersFromBackend();

        // Voice settings
        fetchModels();
        fetchTTSVoices();
        fetchAudioDevices();
        fetchVoiceprintConfig();
    };

    const loadCharactersFromBackend = async () => {
        try {
            const response = await fetch(`${MEMORY_SERVER_URL}/characters`);
            if (response.ok) {
                const { characters: backendChars } = await response.json();
                
                const convertedChars: CharacterProfile[] = backendChars.map((char: any) => {
                    const modelDef = AVAILABLE_MODELS.find(m => m.name === char.live2d_model);
                    return {
                        id: char.character_id,
                        name: char.name,
                        description: char.description,
                        systemPrompt: char.system_prompt,
                        modelPath: modelDef ? modelDef.path : char.live2d_model,
                        voiceConfig: char.voice_config,
                        heartbeatEnabled: char.heartbeat_enabled ?? true,
                        proactiveThresholdMinutes: char.proactive_threshold_minutes ?? 15
                    };
                });
                
                // Sort: Active character first
                const sortedChars = convertedChars.sort((a, b) => {
                    if (a.id === activeCharacterId) return -1;
                    if (b.id === activeCharacterId) return 1;
                    return 0;
                });

                setCharacters(sortedChars);
                setDeletedCharIds([]);
                console.log('[Settings] ✅ Loaded characters from backend:', convertedChars.length);
            }
        } catch (error) {
            console.error('[Settings] Error loading characters:', error);
            // Fallback to local
            const settings = (window as any).settings;
            const loadedChars = await settings.get('characters') as CharacterProfile[];
            if (loadedChars) setCharacters(loadedChars);
        }
    };

    // ==================== Voice Functions ====================
    const fetchModels = async () => {
        try {
            const res = await fetch(`${STT_SERVER_URL}/models/list`);
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

    const fetchTTSVoices = async () => {
        try {
            const edgeRes = await fetch('http://127.0.0.1:8766/tts/voices?engine=edge-tts');
            if (edgeRes.ok) {
                const data = await edgeRes.json();
                setEdgeVoices([...(data.chinese || []), ...(data.english || [])]);
            }
        } catch (e) { console.warn("Failed to fetch Edge voices", e); }

        try {
            const gptRes = await fetch('http://127.0.0.1:8766/tts/voices?engine=gpt-sovits');
            if (gptRes.ok) {
                const data = await gptRes.json();
                setGptVoices(data.voices || []);
            }
        } catch (e) { console.warn("Failed to fetch GPT-SoVITS voices", e); }
    };

    const fetchAudioDevices = async () => {
        try {
            const res = await fetch(`${STT_SERVER_URL}/audio/devices`);
            if (res.ok) {
                const data = await res.json();
                setAudioDevices(data.devices || []);
                setCurrentAudioDevice(data.current || null);
            }
        } catch (e) {
            console.error("Failed to fetch audio devices", e);
        }
    };

    const fetchVoiceprintConfig = async () => {
        try {
            const res = await fetch(`${STT_SERVER_URL}/voiceprint/status`);
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

    const handleAudioDeviceChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        const deviceName = e.target.value;
        try {
            const res = await fetch(`${STT_SERVER_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_name: deviceName })
            });
            if (res.ok) {
                setCurrentAudioDevice(deviceName);
            }
        } catch (err) {
            console.error("Failed to set audio device", err);
        }
    };

    const handleSttModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        const newModel = e.target.value;
        try {
            await fetch(`${STT_SERVER_URL}/models/switch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: newModel })
            });
            setLoadingStatus('loading');
            fetchModels();
        } catch (err) {
            alert("Failed to switch model");
        }
    };

    const handleVoiceprintToggle = async (enabled: boolean) => {
        try {
            await fetch(`${STT_SERVER_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: enabled,
                    voiceprint_threshold: voiceprintThreshold,
                    voiceprint_profile: voiceprintProfile
                })
            });
            setVoiceprintEnabled(enabled);
        } catch (e) {
            console.error('Failed to toggle voiceprint', e);
        }
    };

    const handleVoiceprintThresholdChange = async (threshold: number) => {
        setVoiceprintThreshold(threshold);
        try {
            await fetch(`${STT_SERVER_URL}/audio/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_name: currentAudioDevice,
                    enable_voiceprint_filter: voiceprintEnabled,
                    voiceprint_threshold: threshold,
                    voiceprint_profile: voiceprintProfile
                })
            });
        } catch (e) {
            console.warn('Failed to update threshold', e);
        }
    };

    // ==================== Character Functions ====================
    const handleAddCharacter = () => {
        const tempId = `new_${Date.now()}`;
        const newChar: CharacterProfile = {
            id: tempId,
            name: 'New Character',
            description: 'A new digital soul.',
            systemPrompt: 'You are a helpful AI assistant.',
            voiceConfig: { service: 'gpt-sovits', voiceId: 'default', rate: '+0%', pitch: '+0Hz' }
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
                // Auto-generate ID for new characters
                if (id.startsWith('new_') && updates.name) {
                    const safeId = updates.name.trim().toLowerCase()
                        .replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_')
                        .replace(/_+/g, '_');
                    if (safeId.length > 0) {
                        updatedChar.id = safeId;
                        setEditingCharId(safeId);
                    }
                }
                return updatedChar;
            }
            return c;
        }));
    };

    const handleVoiceConfigChange = (id: string, key: string, value: any) => {
        setCharacters(prev => prev.map(c => {
            if (c.id !== id) return c;
            return { ...c, voiceConfig: { ...c.voiceConfig, [key]: value } };
        }));
    };

    const handleActivateCharacter = (id: string) => {
        console.log(`[SettingsModal] Activating character: ${id}`);
        if (onCharacterSwitch) {
            onCharacterSwitch(id);
        }
    };

    // ==================== Save ====================
    const handleSave = async () => {
        setIsSaving(true);
        const settings = (window as any).settings;
        
        // Save to localStorage
        await settings.set('apiKey', apiKey);
        await settings.set('apiBaseUrl', apiBaseUrl);
        await settings.set('modelName', modelName);
        await settings.set('userName', userName);
        await settings.set('contextWindow', contextWindow);
        await settings.set('activeCharacterId', activeCharacterId);
        await settings.set('live2d_high_dpi', highDpiEnabled);

        // Save characters to backend
        try {
            const savePromises = characters.map(char => {
                const payload = {
                    character_id: char.id,
                    name: char.name,
                    display_name: char.name,
                    description: char.description,
                    system_prompt: char.systemPrompt,
                    live2d_model: char.modelPath,
                    voice_config: char.voiceConfig,
                    heartbeat_enabled: char.heartbeatEnabled,
                    proactive_threshold_minutes: char.proactiveThresholdMinutes
                };
                return fetch(`${MEMORY_SERVER_URL}/characters/${char.id}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            });

            const deletePromises = deletedCharIds.map(id => 
                fetch(`${MEMORY_SERVER_URL}/characters/${id}`, { method: 'DELETE' })
            );

            await Promise.all([...savePromises, ...deletePromises]);
            setDeletedCharIds([]);

            // Reload heartbeat config
            await fetch(`${MEMORY_SERVER_URL}/heartbeat/reload`, { method: 'POST' });
        } catch (e) {
            console.error('[Settings] Failed to sync characters:', e);
        }

        // Trigger callbacks
        if (onContextWindowChange) onContextWindowChange(contextWindow);
        if (onLLMSettingsChange) onLLMSettingsChange(apiKey, apiBaseUrl, modelName);
        if (onCharactersUpdated) onCharactersUpdated(characters, activeCharacterId);
        if (onUserNameUpdated) onUserNameUpdated(userName);
        if (onLive2DHighDpiChange) onLive2DHighDpiChange(highDpiEnabled);

        setIsSaving(false);
        onClose();
    };

    // ==================== Render ====================
    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', 
            justifyContent: 'center', alignItems: 'center', zIndex: 1000,
            backdropFilter: 'blur(3px)'
        }}>
            <div style={{
                backgroundColor: 'white', borderRadius: '12px', 
                width: '600px', height: '600px',
                boxShadow: '0 8px 30px rgba(0,0,0,0.2)',
                display: 'flex', flexDirection: 'column',
                fontFamily: '"Segoe UI", Roboto, Helvetica, Arial, sans-serif',
                overflow: 'hidden'
            }}>
                {/* Header with Tabs */}
                <div style={{ padding: '20px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ margin: 0, fontSize: '20px', color: '#1a1a1a', fontWeight: 600 }}>Settings</h2>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {(['general', 'voice', 'memory', 'characters'] as Tab[]).map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                style={{
                                    padding: '6px 12px', borderRadius: '6px', border: 'none',
                                    background: activeTab === tab ? '#e0e7ff' : 'transparent',
                                    color: activeTab === tab ? '#4f46e5' : '#666',
                                    cursor: 'pointer',
                                    fontWeight: activeTab === tab ? 600 : 400,
                                    textTransform: 'capitalize', fontSize: '14px'
                                }}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content Area */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '20px', backgroundColor: '#f9fafb' }}>
                    {activeTab === 'general' && (
                        <GeneralTab
                            userName={userName} setUserName={setUserName}
                            apiBaseUrl={apiBaseUrl} setApiBaseUrl={setApiBaseUrl}
                            apiKey={apiKey} setApiKey={setApiKey}
                            modelName={modelName} setModelName={setModelName}
                            highDpiEnabled={highDpiEnabled} setHighDpiEnabled={setHighDpiEnabled}
                        />
                    )}

                    {activeTab === 'voice' && (
                        <VoiceTab
                            audioDevices={audioDevices}
                            currentAudioDevice={currentAudioDevice}
                            onAudioDeviceChange={handleAudioDeviceChange}
                            sttEngineType={sttEngineType}
                            setSttEngineType={setSttEngineType}
                            whisperModels={whisperModels}
                            currentWhisperModel={currentWhisperModel}
                            loadingStatus={loadingStatus}
                            onSttModelChange={handleSttModelChange}
                            voiceprintEnabled={voiceprintEnabled}
                            voiceprintThreshold={voiceprintThreshold}
                            voiceprintProfile={voiceprintProfile}
                            voiceprintStatus={voiceprintStatus}
                            onVoiceprintToggle={handleVoiceprintToggle}
                            onVoiceprintThresholdChange={handleVoiceprintThresholdChange}
                            setVoiceprintProfile={setVoiceprintProfile}
                        />
                    )}

                    {activeTab === 'memory' && (
                        <MemoryTab
                            contextWindow={contextWindow}
                            setContextWindow={setContextWindow}
                            onClearHistory={onClearHistory}
                        />
                    )}

                    {activeTab === 'characters' && (
                        <CharactersTab
                            characters={characters}
                            activeCharacterId={activeCharacterId}
                            editingCharId={editingCharId}
                            setEditingCharId={setEditingCharId}
                            edgeVoices={edgeVoices}
                            gptVoices={gptVoices}
                            onAddCharacter={handleAddCharacter}
                            onDeleteCharacter={handleDeleteCharacter}
                            onUpdateCharacter={handleUpdateCharacter}
                            onVoiceConfigChange={handleVoiceConfigChange}
                            onActivateCharacter={handleActivateCharacter}
                        />
                    )}
                </div>

                {/* Footer */}
                <div style={{ padding: '20px', borderTop: '1px solid #eee', display: 'flex', justifyContent: 'flex-end', gap: '10px', backgroundColor: 'white' }}>
                    <button 
                        onClick={onClose} 
                        disabled={isSaving} 
                        style={{ ...buttonStyle, backgroundColor: 'white', border: '1px solid #d1d5db', color: '#374151', opacity: isSaving ? 0.7 : 1 }}
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={handleSave} 
                        disabled={isSaving} 
                        style={{ ...buttonStyle, backgroundColor: '#2563eb', color: 'white', opacity: isSaving ? 0.7 : 1 }}
                    >
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SettingsModalRefactored;
