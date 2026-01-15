
import React, { useState, useEffect } from 'react';
import { CharacterProfile } from '@core/llm/types';
import { API_CONFIG } from '../config';
import { ProvidersTab } from './Settings/ProvidersTab';
import { VoiceTab } from './Settings/VoiceTab';
import { CharactersTab } from './Settings/CharactersTab';
import { useLlmManager } from '../hooks/useLlmManager';
import { useVoiceManager } from '../hooks/useVoiceManager';

// ⚡ Dynamic Architecture
import { usePluginManager } from '../hooks/usePluginManager';
import { PluginConfigRenderer } from './Settings/PluginConfigRenderer';
import { LLMEngineConfig } from './Settings/LLMEngineConfig';

import { inputStyle, labelStyle, buttonStyle } from './Settings/styles';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onClearHistory?: () => void;
    onContextWindowChange?: (newWindow: number) => void;
    onLLMSettingsChange?: (apiKey: string, baseUrl: string, model: string, temperature: number, thinkingEnabled: boolean, historyLimit: number, overflowStrategy: 'slide' | 'reset', topP: number, presencePenalty: number, frequencyPenalty: number) => void;
    onCharactersUpdated?: (characters: CharacterProfile[], activeId: string) => void;
    onUserNameUpdated?: (newName: string) => void;
    onLive2DHighDpiChange?: (enabled: boolean) => void;
    onCharacterSwitch?: (characterId: string) => void;
    onThinkingModeChange?: (enabled: boolean) => void;
    activeCharacterId: string;
}

type Tab = 'general' | 'voice' | 'memory' | 'characters' | 'interaction';

const SettingsModal: React.FC<SettingsModalProps> = ({
    isOpen, onClose, onClearHistory, onContextWindowChange, onLLMSettingsChange, onCharactersUpdated, onUserNameUpdated, onLive2DHighDpiChange, onCharacterSwitch,
    activeCharacterId, onThinkingModeChange
}) => {
    const [activeTab, setActiveTab] = useState<Tab>('general');
    
    // Core Settings (Not yet Plugins)
    const [userName, setUserName] = useState('Master');
    const [highDpiEnabled, setHighDpiEnabled] = useState(false);
    const [contextWindow, setContextWindow] = useState(15);
    const [historyLimit, setHistoryLimit] = useState(100);
    const [overflowStrategy, setOverflowStrategy] = useState<'slide' | 'reset'>('slide');
    const [isSaving, setIsSaving] = useState(false);

    // Legacy Character Management (Preserved for now)
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    const [isLoadingCharacters, setIsLoadingCharacters] = useState(false);
    const [availableModels, setAvailableModels] = useState<{name:string, path:string}[]>([]);
    const [deletedCharIds, setDeletedCharIds] = useState<string[]>([]);

    // ⚡ Hooks
    const { plugins, refreshPlugins, updateConfig, togglePlugin } = usePluginManager();
    const { refreshData: fetchLlmManagerData } = useLlmManager();
    const { edgeVoices, gptVoices, activeTtsEngines, ttsPlugins } = useVoiceManager(isOpen);

    // Initial Load
    useEffect(() => {
        if (isOpen) {
            refreshPlugins();
            fetchLlmManagerData();
            loadCoreSettings();
            fetchCharacters();
        }
    }, [isOpen]);

    const loadCoreSettings = async () => {
        const settings = window.settings;
        setUserName(await settings.get('userName') || 'Master');
        setHighDpiEnabled(await settings.get('live2d_high_dpi') || false);
        setContextWindow(await settings.get('contextWindow') || 15);
        setHistoryLimit(await settings.get('historyLimit') || 100);
        setOverflowStrategy(await settings.get('overflowStrategy') || 'slide');
    };

    const fetchCharacters = async () => {
        setIsLoadingCharacters(true);
        try {
            // Models
            let models: {name:string, path:string}[] = [];
            try {
                const mRes = await fetch(`${API_CONFIG.BASE_URL}/characters/models`);
                if (mRes.ok) {
                    const mData = await mRes.json();
                    models = mData.models || [];
                    setAvailableModels(models);
                }
            } catch (err) {}

            // Characters
            const response = await fetch(`${API_CONFIG.BASE_URL}/characters`);
            if (response.ok) {
                const { characters: backendChars } = await response.json();
                const converted = backendChars.map((char: any) => {
                    const modelDef = models.find(m => m.name === char.live2d_model);
                    const realPath = modelDef ? modelDef.path : 
                                     (char.live2d_model.includes('/') ? char.live2d_model : `/live2d/${char.live2d_model}/${char.live2d_model}.model3.json`);
                    return {
                        id: char.character_id, 
                        name: char.name, 
                        description: char.description,
                        systemPrompt: char.system_prompt,
                        modelPath: realPath,
                        voiceConfig: char.voice_config,
                        heartbeatEnabled: char.heartbeat_enabled ?? true,
                        proactiveChatEnabled: char.proactive_chat_enabled ?? true,
                        galgameModeEnabled: char.galgame_mode_enabled ?? true,
                        soulEvolutionEnabled: char.soul_evolution_enabled ?? true,
                        proactiveThresholdMinutes: char.proactive_threshold_minutes ?? 15,
                        bilibili: char.bilibili || { enabled: false, roomId: 0 }
                    };
                });
                
                // Sort active first
                const sorted = converted.sort((a: any, b: any) => a.id === activeCharacterId ? -1 : (b.id === activeCharacterId ? 1 : 0));
                setCharacters(sorted);
                setDeletedCharIds([]);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoadingCharacters(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        const settings = window.settings;
        
        // Save Core
        await settings.set('userName', userName);
        await settings.set('contextWindow', contextWindow);
        await settings.set('activeCharacterId', activeCharacterId);
        await settings.set('live2d_high_dpi', highDpiEnabled);
        await settings.set('historyLimit', historyLimit);
        await settings.set('overflowStrategy', overflowStrategy);

        // Sync Characters (Legacy Sync for Voice/Paths)
        // Note: Interaction settings are now Global System Plugin settings, 
        // BUT Characters still have local overrides in database.
        // For now, we assume System Plugin Settings override character settings in logic, 
        // OR we should continue to sync them?
        // Current compromise: We sync characters as they are in the 'characters' state.
        // Since 'Interaction' tab now updates System Plugins directly, it doesn't touch 'characters' state.
        // Ideally, backend should prefer System Plugin setting if enabled.
        await syncCharacters();

        // Notify Parent
        if (onUserNameUpdated) onUserNameUpdated(userName);
        if (onLive2DHighDpiChange) onLive2DHighDpiChange(highDpiEnabled);
        if (onContextWindowChange) onContextWindowChange(contextWindow);
        
        // Propagate legacy LLM settings if callback exists (dummies to satisfy interface)
        if (onLLMSettingsChange) onLLMSettingsChange("", "", "dynamic", 0.7, false, historyLimit, overflowStrategy, 1.0, 0, 0);

        setIsSaving(false);
        onClose();
    };

    const syncCharacters = async () => {
        try {
            const savePromises = characters.map(char => {
                // We perform a "Safe Save" - preserving existing interaction flags which might be managed elsewhere
                // Or we accept that CharactersTab updates them.
                const payload = {
                    character_id: char.id,
                    name: char.name,
                    live2d_model: char.modelPath,
                    system_prompt: char.systemPrompt,
                    description: char.description,
                    voice_config: char.voiceConfig,
                    // Pass legacy flags as-is
                    heartbeat_enabled: char.heartbeatEnabled,
                    proactive_chat_enabled: char.proactiveChatEnabled,
                    galgame_mode_enabled: char.galgameModeEnabled,
                    soul_evolution_enabled: char.soulEvolutionEnabled,
                    proactive_threshold_minutes: char.proactiveThresholdMinutes,
                    bilibili: char.bilibili
                };
                return fetch(`${API_CONFIG.BASE_URL}/characters/${char.id}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            });

            const deletePromises = deletedCharIds.map(id => fetch(`${API_CONFIG.BASE_URL}/characters/${id}`, { method: 'DELETE' }));
            await Promise.all([...savePromises, ...deletePromises]);
            
            // Reload heartbeat
            try { await fetch(`${API_CONFIG.BASE_URL}/heartbeat/reload`, { method: 'POST' }); } catch {}
            
            if (onCharactersUpdated) onCharactersUpdated(characters, activeCharacterId);
        } catch (e) {
            console.error("Character sync failed", e);
        }
    };

    const handleActivateCharacter = (id: string) => {
        if (onCharacterSwitch) onCharacterSwitch(id);
    };

    const handleDeleteCharacter = (id: string) => {
        if (characters.length <= 1) return alert("Must keep at least one character!");
        if (confirm('Delete character?')) {
            setDeletedCharIds([...deletedCharIds, id]);
            const newChars = characters.filter(c => c.id !== id);
            setCharacters(newChars);
            if (activeCharacterId === id && newChars.length > 0) {
                if (onCharacterSwitch) onCharacterSwitch(newChars[0].id);
            }
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
                backgroundColor: 'white', borderRadius: '12px', width: '850px', height: '650px',
                boxShadow: '0 8px 30px rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column',
                fontFamily: '"Segoe UI", Roboto, Helvetica, Arial, sans-serif', overflow: 'hidden'
            }}>
                {/* Header */}
                <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-white">
                    <h2 className="text-xl font-semibold text-gray-800">Settings</h2>
                    <div className="flex gap-2">
                        {(['general', 'voice', 'memory', 'characters', 'interaction'] as Tab[]).map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                                    activeTab === tab ? 'bg-indigo-50 text-indigo-600' : 'text-gray-500 hover:bg-gray-50'
                                }`}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 bg-gray-50 text-gray-800">
                    
                    {/* --- GENERAL TAB (Includes User & LLM) --- */}
                    {activeTab === 'general' && (
                        <div className="space-y-6">
                            <section>
                                <h3 className="text-sm font-semibold text-gray-700 mb-2">User Profile</h3>
                                <div>
                                    <label className="block text-xs text-gray-500 mb-1">Your Name</label>
                                    <input 
                                        value={userName} 
                                        onChange={e => setUserName(e.target.value)}
                                        className="w-full bg-white border border-gray-300 rounded px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:border-indigo-500"
                                        placeholder="User"
                                    />
                                </div>
                            </section>
                            
                            <div className="h-px bg-gray-200 my-4" />
                            
                             <section className='bg-gray-900 rounded-lg p-4 border border-gray-700 shadow-inner'>
                                {/* ⚡ Configured for Dark Mode style inside the LLM Config component */}
                                <LLMEngineConfig />
                            </section>

                            <div className="h-px bg-gray-200 my-4" />

                            <section>
                                <h3 className="text-sm font-semibold text-gray-700 mb-2">Visual Settings</h3>
                                <div className="flex items-center gap-2 bg-white p-3 rounded border border-gray-200">
                                    <input 
                                        type="checkbox" 
                                        checked={highDpiEnabled} 
                                        onChange={e => setHighDpiEnabled(e.target.checked)}
                                        className="w-4 h-4 text-indigo-600"
                                    />
                                    <div>
                                        <div className="text-sm font-medium text-gray-800">High-DPI Rendering</div>
                                        <div className="text-xs text-gray-500">Enable Retina/4K support for Live2D (Higher GPU usage)</div>
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}

                    {/* --- INTERACTION TAB (Dynamic Plugins) --- */}
                    {activeTab === 'interaction' && (
                        <div className="space-y-6">
                            <div className="bg-blue-50 border border-blue-100 rounded p-3 mb-4">
                                <p className="text-xs text-blue-700">
                                    ✨ These settings control global system plugins. They affect how the AI interacts across all characters.
                                </p>
                            </div>

                            {/* Game / Logic Plugins */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-700 mb-3">Game Systems</h3>
                                <div className="space-y-2">
                                    {plugins.filter(p => p.category === 'game' || p.category === 'interaction').length === 0 && (
                                        <div className="text-sm text-gray-400 italic">No game plugins loaded.</div>
                                    )}
                                    {plugins.filter(p => p.category === 'game' || p.category === 'interaction').map(plugin => (
                                         <div key={plugin.id} className="bg-gray-800 rounded-lg p-4 text-white">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <h4 className="font-medium text-cyan-400">{plugin.name}</h4>
                                                    <p className="text-xs text-gray-400">{plugin.description}</p>
                                                </div>
                                                <button 
                                                    onClick={() => togglePlugin(plugin.id)}
                                                    className={`text-xs px-2 py-1 rounded ${plugin.enabled ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}
                                                >
                                                    {plugin.enabled ? 'Enabled' : 'Disabled'}
                                                </button>
                                            </div>
                                            {plugin.enabled && (
                                                <div className="mt-3 pt-3 border-t border-gray-700">
                                                    <PluginConfigRenderer 
                                                        plugin={plugin} 
                                                        onUpdate={(key, val) => updateConfig(plugin.id, key, val)} 
                                                    />
                                                </div>
                                            )}
                                         </div>
                                    ))}
                                </div>
                            </section>

                            {/* MCP / External Tools (Bilibili etc) */}
                            <section>
                                <h3 className="text-sm font-semibold text-gray-700 mb-3">External Tools (MCP)</h3>
                                <div className="space-y-2">
                                    {plugins.filter(p => p.id.startsWith('mcp.')).length === 0 && (
                                        <div className="text-sm text-gray-400 italic">No external tools loaded.</div>
                                    )}
                                    {plugins.filter(p => p.id.startsWith('mcp.')).map(plugin => (
                                         <div key={plugin.id} className="bg-gray-800 rounded-lg p-4 text-white">
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                     <h4 className="font-medium text-purple-400">{plugin.name}</h4>
                                                     <p className="text-xs text-gray-400">{plugin.description}</p>
                                                </div>
                                                {/* MCP can't be toggled via system plugin manager yet, usually auto-run */}
                                            </div>
                                            <div className="mt-3 pt-3 border-t border-gray-700">
                                                 <PluginConfigRenderer 
                                                    plugin={plugin} 
                                                    onUpdate={(key, val) => updateConfig(plugin.id, key, val)} 
                                                />
                                            </div>
                                         </div>
                                    ))}
                                </div>
                            </section>
                        </div>
                    )}

                    {activeTab === 'voice' && <VoiceTab />}
                    {activeTab === 'characters' && (
                        <CharactersTab
                            characters={characters}
                            setCharacters={setCharacters}
                            activeCharacterId={activeCharacterId}
                            onActivateCharacter={handleActivateCharacter}
                            onDeleteCharacter={handleDeleteCharacter}
                            edgeVoices={edgeVoices}
                            gptVoices={gptVoices}
                            activeTtsEngines={activeTtsEngines}
                            availableModels={availableModels}
                            ttsPlugins={ttsPlugins}
                        />
                    )}
                    {activeTab === 'memory' && (
                        <div className="space-y-6">
                            <section>
                                <h3 className="text-sm font-semibold text-gray-700 mb-2">Local Session Memory</h3>
                                <div className="bg-white p-4 rounded border border-gray-200 space-y-4">
                                    <div>
                                        <div className="flex justify-between mb-1">
                                            <label className="text-sm font-medium text-gray-700">Context Window</label>
                                            <span className="text-xs font-bold text-indigo-600">{contextWindow} turns</span>
                                        </div>
                                        <input 
                                            type="range" min="5" max="50" value={contextWindow} 
                                            onChange={e => setContextWindow(Number(e.target.value))}
                                            className="w-full accent-indigo-600"
                                        />
                                    </div>
                                    <div>
                                        <div className="flex justify-between mb-1">
                                            <label className="text-sm font-medium text-gray-700">History Limit</label>
                                            <span className="text-xs font-bold text-indigo-600">{historyLimit} msgs</span>
                                        </div>
                                        <input 
                                            type="range" min="10" max="500" step="10" value={historyLimit} 
                                            onChange={e => setHistoryLimit(Number(e.target.value))}
                                            className="w-full accent-indigo-600"
                                        />
                                    </div>
                                    <div className="flex justify-between items-center">
                                         <label className="text-sm font-medium text-gray-700">Overflow Strategy</label>
                                         <select 
                                            value={overflowStrategy} 
                                            onChange={e => setOverflowStrategy(e.target.value as any)}
                                            className="px-2 py-1 text-sm border border-gray-300 rounded"
                                         >
                                            <option value="slide">Slide (Drop Oldest)</option>
                                            <option value="reset">Reset</option>
                                         </select>
                                    </div>
                                    <button 
                                        onClick={() => { if(confirm('Clear history?')) onClearHistory?.(); }}
                                        className="w-full mt-2 py-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded hover:bg-red-100"
                                    >
                                        Clear History & Reset
                                    </button>
                                </div>
                            </section>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-5 border-t border-gray-100 bg-white flex justify-end gap-3">
                    <button 
                        onClick={onClose}
                        className="px-4 py-2 rounded-md text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                        disabled={isSaving}
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={handleSave}
                        className="px-4 py-2 rounded-md text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                        disabled={isSaving}
                    >
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
            {/* Styles */}
            <style>{`
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-track { background: transparent; }
                ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
            `}</style>
        </div>
    );
};

export default SettingsModal;
