
import React, { useState, useEffect } from 'react';
import { CharacterProfile } from '@core/llm/types';
import { API_CONFIG } from '../config';
import { ProvidersTab } from './Settings/ProvidersTab';
import { VoiceTab } from './Settings/VoiceTab';
import { Settings, Mic, Puzzle, X, Save, Layers, Image as ImageIcon, Monitor } from 'lucide-react';

import { useLlmManager } from '../hooks/useLlmManager';
import { useVoiceManager } from '../hooks/useVoiceManager';

// ⚡ Dynamic Architecture
import { usePluginManager } from '../hooks/usePluginManager';
import { PluginConfigRenderer } from './Settings/PluginConfigRenderer';

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
    onBackgroundImageChange?: (url: string) => void;
    activeCharacterId: string;
    initialTab?: Tab;
    
    // Voice Props
    edgeVoices?: any[];
    gptVoices?: any[];
    activeTtsEngines?: string[];
    ttsPlugins?: any[];
}

type Tab = 'general' | 'voice' | 'characters' | 'interaction';

const SettingsModal: React.FC<SettingsModalProps> = ({
    isOpen, onClose, onClearHistory, onContextWindowChange, onLLMSettingsChange, onCharactersUpdated, onUserNameUpdated, onLive2DHighDpiChange, onCharacterSwitch,
    activeCharacterId, onThinkingModeChange, initialTab, onBackgroundImageChange,
    edgeVoices = [], gptVoices = [], activeTtsEngines = [], ttsPlugins = []
}) => {
    const [activeTab, setActiveTab] = useState<Tab>(initialTab || 'general');
    
    // Core Settings
    const [userName, setUserName] = useState('Master');
    const [highDpiEnabled, setHighDpiEnabled] = useState(false);
    const [contextWindow, setContextWindow] = useState(15);
    const [historyLimit, setHistoryLimit] = useState(100);
    const [overflowStrategy, setOverflowStrategy] = useState<'slide' | 'reset'>('reset');
    const [backgroundImage, setBackgroundImage] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // Hooks
    const { plugins, refreshPlugins, updateConfig, togglePlugin } = usePluginManager();
    const { refreshData: fetchLlmManagerData } = useLlmManager();
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    // Initial Load
    useEffect(() => {
        if (isOpen) {
            refreshPlugins();
            fetchLlmManagerData();
            loadCoreSettings();
        }
    }, [isOpen]);

    const loadCoreSettings = async () => {
        const settings = window.settings;
        setUserName(await settings.get('userName') || 'Master');
        setHighDpiEnabled(await settings.get('live2d_high_dpi') || false);
        setContextWindow(await settings.get('contextWindow') || 15);
        setHistoryLimit(await settings.get('historyLimit') || 100);
        setOverflowStrategy(await settings.get('overflowStrategy') || 'slide');
        setBackgroundImage(await settings.get('backgroundImage') || '');
    };

    const handleSave = async () => {
        setIsSaving(true);
        const settings = window.settings;
        
        await settings.set('userName', userName);
        await settings.set('contextWindow', contextWindow);
        await settings.set('activeCharacterId', activeCharacterId);
        await settings.set('live2d_high_dpi', highDpiEnabled);
        await settings.set('historyLimit', historyLimit);
        await settings.set('overflowStrategy', overflowStrategy);
        await settings.set('backgroundImage', backgroundImage);

        if (onUserNameUpdated) onUserNameUpdated(userName);
        
        setIsSaving(false);
        onClose();
    };

    if (!isOpen) return null;

    // --- STYLES ---
    const glassPanelStyle: React.CSSProperties = {
        backgroundColor: 'rgba(255, 255, 255, 0.75)',
        backdropFilter: 'blur(20px)',
        borderRadius: '24px',
        border: '1px solid rgba(255, 255, 255, 0.6)',
        boxShadow: '0 20px 50px rgba(0,0,0,0.1), inset 0 0 20px rgba(255,255,255,0.5)',
        width: '900px',
        height: '700px',
        display: 'flex',
        overflow: 'hidden',
        color: '#4B5563',
        transform: 'translateY(0)',
        animation: 'slideUp 0.3s ease-out'
    };

    const tabStyle = (isActive: boolean): React.CSSProperties => ({
        padding: '12px 20px',
        borderRadius: '16px',
        cursor: 'pointer',
        fontSize: '15px',
        fontWeight: 600,
        color: isActive ? '#fff' : '#6B7280',
        background: isActive ? 'linear-gradient(135deg, #F472B6 0%, #DB2777 100%)' : 'transparent',
        boxShadow: isActive ? '0 4px 12px rgba(219, 39, 119, 0.3)' : 'none',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '8px'
    });

    const inputStyle: React.CSSProperties = {
        width: "100%",
        padding: "10px 14px",
        borderRadius: "12px",
        border: "1px solid rgba(0,0,0,0.1)",
        backgroundColor: "rgba(255,255,255,0.5)",
        fontSize: "14px",
        color: "#1f2937",
        outline: "none",
        transition: "all 0.2s",
    };

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.3)', 
            display: 'flex', justifyContent: 'center', alignItems: 'center', 
            zIndex: 3000,
            backdropFilter: 'blur(5px)'
        }}>
            <div style={glassPanelStyle}>
                
                {/* SIDEBAR */}
                <div style={{
                    width: '240px',
                    background: 'rgba(255,255,255,0.4)',
                    borderRight: '1px solid rgba(255,255,255,0.5)',
                    padding: '30px 20px',
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    <h2 style={{ 
                        fontSize: '24px', fontWeight: 800, color: '#374151', 
                        marginBottom: '30px', paddingLeft: '10px',
                        background: 'linear-gradient(to right, #ec4899, #8b5cf6)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent'
                    }}>
                        Lumina <span style={{ fontSize: '14px', opacity: 0.6, fontWeight: 500 }}>Settings</span>
                    </h2>

                    <div style={{ flex: 1 }}>
                        <div onClick={() => setActiveTab('general')} style={tabStyle(activeTab === 'general')}>
                            <Settings size={18} /> <span>General</span>
                        </div>
                        <div onClick={() => setActiveTab('voice')} style={tabStyle(activeTab === 'voice')}>
                            <Mic size={18} /> <span>Voice</span>
                        </div>
                        <div onClick={() => setActiveTab('interaction')} style={tabStyle(activeTab === 'interaction')}>
                            <Puzzle size={18} /> <span>Plugins</span>
                        </div>
                    </div>

                    <button 
                        onClick={onClose}
                        style={{
                            padding: '12px',
                            marginTop: '20px',
                            borderRadius: '16px',
                            border: '1px solid rgba(0,0,0,0.1)',
                            background: 'white',
                            color: '#6B7280',
                            cursor: 'pointer',
                            fontWeight: 600,
                            transition: 'all 0.2s',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#f3f4f6'}
                        onMouseLeave={e => e.currentTarget.style.background = 'white'}
                    >
                        <X size={18} /> Close
                    </button>
                    <button 
                        onClick={handleSave}
                        disabled={isSaving}
                        style={{
                            marginTop: '10px',
                            padding: '12px',
                            borderRadius: '16px',
                            background: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
                            color: 'white',
                            border: 'none',
                            cursor: 'pointer',
                            fontWeight: 600,
                            boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                        }}
                    >
                        {isSaving ? <span className="spinner">⏳</span> : <Save size={18} />}
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>

                {/* CONTENT AREA */}
                <div style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#1f2937', marginBottom: '25px', paddingBottom: '10px', borderBottom: '2px solid rgba(0,0,0,0.05)' }}>
                        {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Settings
                    </h2>

                    {/* --- GENERAL TAB --- */}
                    {activeTab === 'general' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
                            <section>
                                <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px', color: '#4B5563' }}>Your Name</label>
                                <input 
                                    value={userName} 
                                    onChange={e => setUserName(e.target.value)}
                                    style={inputStyle}
                                    placeholder="Master"
                                    onFocus={(e) => e.target.style.borderColor = '#ec4899'}
                                    onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.1)'}
                                />
                            </section>

                            <section>
                                <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px', color: '#4B5563' }}>Background Image</label>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    <input 
                                        value={backgroundImage} 
                                        onChange={e => setBackgroundImage(e.target.value)}
                                        style={inputStyle}
                                        placeholder="Image URL or File Path..."
                                    />
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        onChange={(e) => {
                                            const file = e.target.files?.[0];
                                            if (file && (file as any).path) {
                                                const path = (file as any).path.replace(/\\/g, '/');
                                                const savedUrl = `file:///${path}`;
                                                setBackgroundImage(savedUrl);
                                                const previewUrl = URL.createObjectURL(file);
                                                if (onBackgroundImageChange) onBackgroundImageChange(previewUrl); 
                                            }
                                        }}
                                        style={{ display: 'none' }}
                                        accept="image/*"
                                    />
                                    <button 
                                        onClick={() => fileInputRef.current?.click()}
                                        style={{
                                            whiteSpace: 'nowrap',
                                            padding: '0 20px',
                                            borderRadius: '12px',
                                            border: '1px solid rgba(0,0,0,0.1)',
                                            background: 'white',
                                            cursor: 'pointer',
                                            fontWeight: 500
                                        }}
                                    >
                                        Browse
                                    </button>
                                </div>
                                <p style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '6px' }}>
                                    Tip: Use a high-res image for best visual effect.
                                </p>
                            </section>

                            <section>
                                <div style={{ 
                                    padding: '15px', 
                                    background: 'rgba(255,255,255,0.5)', 
                                    borderRadius: '12px',
                                    border: '1px solid rgba(0,0,0,0.05)',
                                    display: 'flex', alignItems: 'center', gap: '15px'
                                }}>
                                    <input 
                                        type="checkbox" 
                                        checked={highDpiEnabled} 
                                        onChange={e => setHighDpiEnabled(e.target.checked)}
                                        style={{ width: '20px', height: '20px', accentColor: '#ec4899' }}
                                    />
                                    <div>
                                        <div style={{ fontWeight: 600, color: '#374151' }}>High-DPI Rendering</div>
                                        <div style={{ fontSize: '13px', color: '#6B7280' }}>Enable Retina/4K support for clearer avatars.</div>
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}

                    {/* --- INTERACTION TAB --- */}
                    {activeTab === 'interaction' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                             <div style={{ padding: '15px', background: '#eff6ff', borderRadius: '12px', border: '1px solid #dbeafe', color: '#1e40af', fontSize: '14px' }}>
                                ✨ Control system plugins and external tools.
                            </div>

                            {/* Game Systems */}
                            <div>
                                <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '15px', color: '#374151' }}>Game Systems</h3>
                                <div style={{ display: 'grid', gap: '15px' }}>
                                    {plugins.filter(p => p.category === 'game' || p.category === 'interaction').map(plugin => (
                                         <div key={plugin.id} style={{
                                             background: 'white',
                                             padding: '20px',
                                             borderRadius: '16px',
                                             border: '1px solid rgba(0,0,0,0.05)',
                                             boxShadow: '0 4px 6px rgba(0,0,0,0.02)'
                                         }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                                                <div>
                                                    <h4 style={{ fontWeight: 700, color: '#111827' }}>{plugin.name}</h4>
                                                    <p style={{ fontSize: '13px', color: '#6B7280', marginTop: '4px' }}>{plugin.description}</p>
                                                </div>
                                                <button 
                                                    onClick={() => togglePlugin(plugin.id)}
                                                    style={{
                                                        padding: '6px 12px',
                                                        borderRadius: '20px',
                                                        fontSize: '12px',
                                                        fontWeight: 600,
                                                        border: 'none',
                                                        cursor: 'pointer',
                                                        background: plugin.enabled ? '#dcfce7' : '#fee2e2',
                                                        color: plugin.enabled ? '#166534' : '#991b1b',
                                                    }}
                                                >
                                                    {plugin.enabled ? 'Enabled' : 'Disabled'}
                                                </button>
                                            </div>
                                            {plugin.enabled && (
                                                <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: '15px' }}>
                                                    <PluginConfigRenderer 
                                                        plugin={plugin} 
                                                        onUpdate={(key, val) => updateConfig(plugin.id, key, val)} 
                                                    />
                                                </div>
                                            )}
                                         </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* --- VOICE TAB --- */}
                    {activeTab === 'voice' && <VoiceTab />}

                </div>
            </div>
            
            <style>{`
                @keyframes slideUp {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-track { background: transparent; }
                ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }
            `}</style>
        </div>
    );
};

export default SettingsModal;
