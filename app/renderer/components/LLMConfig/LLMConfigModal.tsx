import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Brain, Cpu, Wand2, X } from 'lucide-react';
import { API_CONFIG } from '../../config';

interface LLMConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentLlmSettings: {
        apiKey: string;
        apiBaseUrl: string;
        modelName: string;
        temperature: number;
        thinkingEnabled: boolean;
        historyLimit?: number;
        overflowStrategy?: 'slide' | 'reset';
        topP?: number;
        presencePenalty?: number;
        frequencyPenalty?: number;
    };
    onSettingsChange: (apiKey: string, baseUrl: string, model: string, temperature: number, thinkingEnabled: boolean, historyLimit: number, overflowStrategy: 'slide' | 'reset', topP?: number, presencePenalty?: number, frequencyPenalty?: number) => void;
}

const PRESET_PROVIDERS: Record<string, { baseUrl: string; defaultModel: string }> = {
    deepseek: { baseUrl: 'https://api.deepseek.com', defaultModel: 'deepseek-chat' }, // V3
    openai: { baseUrl: 'https://api.openai.com/v1', defaultModel: 'gpt-4o' },
    anthropic: { baseUrl: 'https://api.anthropic.com/v1', defaultModel: 'claude-3-5-sonnet-20240620' },
    google: { baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/', defaultModel: 'gemini-1.5-flash' },
    siliconflow: { baseUrl: 'https://api.siliconflow.cn/v1', defaultModel: 'deepseek-ai/DeepSeek-V3' },
    custom: { baseUrl: '', defaultModel: '' } // Manual entry
};

const LLMConfigModal: React.FC<LLMConfigModalProps> = ({ 
    isOpen, 
    onClose, 
    currentLlmSettings,
    onSettingsChange 
}) => {
    // Local State
    const [providerType, setProviderType] = useState<'free' | 'custom'>('free'); // 'free' or 'custom'
    const [selectedPlatform, setSelectedPlatform] = useState<string>('custom');
    const [apiKey, setApiKey] = useState('');
    const [baseUrl, setBaseUrl] = useState('');
    const [modelName, setModelName] = useState('');
    const [temperature, setTemperature] = useState(0.7);
    const [topP, setTopP] = useState(1.0);
    const [presencePenalty, setPresencePenalty] = useState(0.0);
    const [frequencyPenalty, setFrequencyPenalty] = useState(0.0);
    const [thinkingEnabled, setThinkingEnabled] = useState(false);
    const [historyLimit, setHistoryLimit] = useState(20);
    const [overflowStrategy, setOverflowStrategy] = useState<'slide' | 'reset'>('slide');
    
    // Advanced Routing (Optional for now, but UI should support it eventually)
    // For now, let's keep it simple: Main Chat Model

    // Initialize from props when opening
    useEffect(() => {
        if (isOpen) {
            setApiKey(currentLlmSettings.apiKey);
            setBaseUrl(currentLlmSettings.apiBaseUrl);
            setModelName(currentLlmSettings.modelName);
            setTemperature(currentLlmSettings.temperature);
            setTopP(currentLlmSettings.topP ?? 1.0);
            setPresencePenalty(currentLlmSettings.presencePenalty ?? 0.0);
            setFrequencyPenalty(currentLlmSettings.frequencyPenalty ?? 0.0);
            setThinkingEnabled(currentLlmSettings.thinkingEnabled);
            setHistoryLimit(currentLlmSettings.historyLimit ?? 20);
            setOverflowStrategy(currentLlmSettings.overflowStrategy ?? 'slide');
            
            // Heuristic to detect provider type & platform
            const url = currentLlmSettings.apiBaseUrl;
            const isFree = url.includes('localhost:8010') || url.includes('127.0.0.1:8010');
            setProviderType(isFree ? 'free' : 'custom');
            
            if (!isFree) {
                // Detect Platform
                let foundPlatform = 'custom';
                for (const [key, val] of Object.entries(PRESET_PROVIDERS)) {
                    if (val.baseUrl && url.includes(val.baseUrl)) {
                         foundPlatform = key;
                         break;
                    }
                }
                // Special case: DeepSeek variations
                if (url.includes('deepseek')) foundPlatform = 'deepseek';
                
                setSelectedPlatform(foundPlatform);
            }
        }
    }, [isOpen, currentLlmSettings]);

    const handleSave = () => {
        // Enforce provider defaults if Free Mode
        let finalBaseUrl = baseUrl;
        let finalModel = modelName;

        if (providerType === 'free') {
             // If Free Mode, ensure we point to our backend or free provider logic
             // Actually, the backend handles the routing if we are in free mode.
             // But traditionally in this app, 'free mode' meant pointing to a specific URL or letting the backend decide?
             // Looking at SettingsModal, free mode set URL to `${API_CONFIG.BASE_URL}/v1` usually.
             // Let's stick to what the user had or defaults.
        }

        onSettingsChange(apiKey, finalBaseUrl, finalModel, temperature, thinkingEnabled, historyLimit, overflowStrategy, topP, presencePenalty, frequencyPenalty);
        onClose();
    };

    const inputStyle = {
        width: '100%',
        padding: '10px 12px',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        fontSize: '14px',
        marginTop: '6px',
        boxSizing: 'border-box' as const,
        outline: 'none',
        transition: 'all 0.2s'
    };

    const labelStyle = {
        display: 'block',
        fontSize: '13px',
        fontWeight: 600,
        color: '#4b5563',
        marginTop: '16px'
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(5px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 20000 // Higher than Plugin Store (10000)
        }}>
            <div style={{
                width: '500px',
                backgroundColor: 'white',
                borderRadius: '24px',
                boxShadow: '0 20px 50px rgba(0,0,0,0.2)',
                padding: '0',
                overflow: 'hidden',
                animation: 'slideIn 0.3s ease-out'
            }}>
                {/* Header */}
                <div style={{ 
                    padding: '24px', 
                    background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                    color: 'white',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ background: 'rgba(255,255,255,0.2)', padding: '8px', borderRadius: '12px' }}>
                            <Brain size={24} color="white" />
                        </div>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>Neural Configuration</h2>
                            <p style={{ margin: '4px 0 0 0', fontSize: '13px', opacity: 0.8 }}>Manage Large Language Model behavior</p>
                        </div>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', opacity: 0.8 }}>
                        <X size={24} />
                    </button>
                </div>

                <div style={{ padding: '24px' }}>
                    {/* Provider Toggle */}
                    <div style={{ display: 'flex', background: '#f3f4f6', padding: '4px', borderRadius: '12px', marginBottom: '24px' }}>
                        <button
                             onClick={() => {
                                 setProviderType('free');
                                 // Set Defaults for Free
                                 // setBaseUrl(`${API_CONFIG.BASE_URL}/v1`); // Usually this, or keep as is?
                             }}
                             style={{
                                 flex: 1, padding: '10px', borderRadius: '10px',
                                 background: providerType === 'free' ? 'white' : 'transparent',
                                 boxShadow: providerType === 'free' ? '0 2px 8px rgba(0,0,0,0.05)' : 'none',
                                 border: 'none', cursor: 'pointer', fontWeight: 600,
                                 color: providerType === 'free' ? '#6366f1' : '#6b7280',
                                 transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                             }}
                        >
                            <Wand2 size={16} /> Free AI (免配置)
                        </button>
                        <button
                             onClick={() => {
                                 setProviderType('custom');
                                 // Set Defaults for Custom (DeepSeek)
                                 if (!baseUrl.includes('http')) setBaseUrl('https://api.deepseek.com/v1');
                                 if (!modelName) setModelName('deepseek-reasoner');
                             }}
                             style={{
                                 flex: 1, padding: '10px', borderRadius: '10px',
                                 background: providerType === 'custom' ? 'white' : 'transparent',
                                 boxShadow: providerType === 'custom' ? '0 2px 8px rgba(0,0,0,0.05)' : 'none',
                                 border: 'none', cursor: 'pointer', fontWeight: 600,
                                 color: providerType === 'custom' ? '#6366f1' : '#6b7280',
                                 transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                             }}
                        >
                            <Cpu size={16} /> Custom / DeepSeek
                        </button>
                    </div>

                    {/* Configuration Form */}
                    <div style={{ animation: 'fadeIn 0.3s ease' }}>
                        {providerType === 'free' ? (
                            <div style={{ background: '#eef2ff', padding: '16px', borderRadius: '12px', border: '1px solid #c7d2fe' }}>
                                <div style={{ fontSize: '14px', fontWeight: 600, color: '#4f46e5', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Wand2 size={16} /> Pollinations AI (Unlimited)
                                </div>
                                <div style={{ fontSize: '13px', color: '#4b5563', lineHeight: 1.5 }}>
                                    Using privacy-focused AI models (OpenAI, Claude, Llama, Mixtral) proxied via Pollinations. No API key required.
                                </div>
                                
                                <label style={labelStyle}>Select Model</label>
                                <select 
                                    style={inputStyle}
                                    value={modelName}
                                    onChange={(e) => setModelName(e.target.value)}
                                >
                                    <option value="gpt-4o-mini">GPT-4o Mini (Fast & Smart)</option>
                                    <option value="claude-3-haiku">Claude 3 Haiku</option>
                                    <option value="llama-3-70b">Llama 3 70B</option>
                                    <option value="mixtral-8x7b">Mixtral 8x7B</option>
                                    <option value="midijourney">Midijourney (Musical)</option>
                                    <option value="rtist">Rtist (Creative)</option>
                                    <option value="searchgpt">SearchGPT (Web Connected)</option>
                                </select>
                            </div>
                        ) : (
                            // Custom / DeepSeek / OpenAI
                            <>
                                <div>
                                    <label style={labelStyle}>Platform</label>
                                    <select 
                                        style={inputStyle}
                                        value={selectedPlatform}
                                        onChange={(e) => {
                                            const plat = e.target.value;
                                            setSelectedPlatform(plat);
                                            if (plat !== 'custom') {
                                                const preset = PRESET_PROVIDERS[plat];
                                                setBaseUrl(preset.baseUrl);
                                                if (plat === 'deepseek') {
                                                    // Default to V3 (Chat) on switch, or R1 if thinking was enabled
                                                    setModelName(thinkingEnabled ? 'deepseek-reasoner' : 'deepseek-chat');
                                                } else {
                                                    setModelName(preset.defaultModel);
                                                }
                                            } else {
                                                setBaseUrl(''); // Clear for custom or keep previous? Keep previous is better UX.
                                            }
                                        }}
                                    >
                                        <option value="deepseek">DeepSeek (Open Source King)</option>
                                        <option value="openai">OpenAI (GPT-4)</option>
                                        <option value="google">Google Gemini (Flash/Pro)</option>
                                        <option value="anthropic">Anthropic (Claude)</option>
                                        <option value="siliconflow">SiliconFlow (Cloud)</option>
                                        <option value="custom">Custom Implementation</option>
                                    </select>
                                </div>

                                {/* Dynamic Endpoint Input */}
                                {selectedPlatform === 'custom' && (
                                    <div>
                                        <label style={labelStyle}>API Endpoint</label>
                                        <input 
                                            style={inputStyle} 
                                            value={baseUrl} 
                                            onChange={e => setBaseUrl(e.target.value)}
                                            placeholder="https://api.example.com/v1"
                                        />
                                    </div>
                                )}

                                <div>
                                    <label style={labelStyle}>API Key</label>
                                    <input 
                                        type="password"
                                        style={inputStyle} 
                                        value={apiKey} 
                                        onChange={e => setApiKey(e.target.value)}
                                        placeholder="sk-..."
                                    />
                                </div>

                                {/* DeepSeek Special Logic */}
                                {selectedPlatform === 'deepseek' ? (
                                    <div style={{ marginTop: '16px', padding: '16px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <div style={{ fontSize: '14px', fontWeight: 600, color: '#334155' }}>
                                                    {thinkingEnabled ? 'DeepSeek R1 (Reasoner)' : 'DeepSeek V3 (Chat)'}
                                                </div>
                                                <div style={{ fontSize: '12px', color: '#64748b', marginTop:'4px' }}>
                                                    {thinkingEnabled ? 'Uses Chain-of-Thought (CoT) for complex reasoning.' : 'Standard fast chat model.'}
                                                </div>
                                            </div>
                                            <label className="switch">
                                                <input 
                                                    type="checkbox" 
                                                    checked={thinkingEnabled} 
                                                    onChange={e => {
                                                        const isR1 = e.target.checked;
                                                        setThinkingEnabled(isR1);
                                                        setModelName(isR1 ? 'deepseek-reasoner' : 'deepseek-chat');
                                                    }} 
                                                />
                                                <span className="slider round"></span>
                                            </label>
                                        </div>
                                    </div>
                                ) : (
                                    // Standard Model Input for others
                                    <div>
                                        <label style={labelStyle}>Model Name</label>
                                        <input 
                                            style={inputStyle} 
                                            value={modelName} 
                                            onChange={e => setModelName(e.target.value)}
                                            placeholder="gpt-4o"
                                        />
                                    </div>
                                )}
                            </>
                        )}

                        {/* Common Settings */}
                        <div style={{ marginTop: '20px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <label style={{ ...labelStyle, marginTop: 0 }}>Temperature ({temperature})</label>
                                <span style={{ fontSize: '12px', color: '#9ca3af' }}>Creativity</span>
                            </div>
                            <input 
                                type="range" 
                                min="0" max="2" step="0.1"
                                value={temperature}
                                onChange={e => setTemperature(parseFloat(e.target.value))}
                                style={{ width: '100%', marginTop: '8px', accentColor: '#6366f1' }}
                            />
                            
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                                <label style={{ ...labelStyle, marginTop: 0 }}>Top P ({topP})</label>
                                <span style={{ fontSize: '12px', color: '#9ca3af' }}>Vocabulary</span>
                            </div>
                            <input 
                                type="range" 
                                min="0" max="1" step="0.05"
                                value={topP}
                                onChange={e => setTopP(parseFloat(e.target.value))}
                                style={{ width: '100%', marginTop: '8px', accentColor: '#6366f1' }}
                            />
                            
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <label style={{ ...labelStyle, marginTop: 0 }}>Presence Pen. ({presencePenalty})</label>
                                    </div>
                                    <input 
                                        type="range" 
                                        min="0" max="2" step="0.1"
                                        value={presencePenalty}
                                        onChange={e => setPresencePenalty(parseFloat(e.target.value))}
                                        style={{ width: '100%', marginTop: '8px', accentColor: '#6366f1' }}
                                    />
                                    <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>New Topics</div>
                                </div>
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <label style={{ ...labelStyle, marginTop: 0 }}>Frequency Pen. ({frequencyPenalty})</label>
                                    </div>
                                    <input 
                                        type="range" 
                                        min="0" max="2" step="0.1"
                                        value={frequencyPenalty}
                                        onChange={e => setFrequencyPenalty(parseFloat(e.target.value))}
                                        style={{ width: '100%', marginTop: '8px', accentColor: '#6366f1' }}
                                    />
                                    <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>No Repeat</div>
                                </div>
                            </div>
                            
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                                <label style={{ ...labelStyle, marginTop: 0 }}>Context History ({historyLimit} turns)</label>
                                <span style={{ fontSize: '12px', color: '#9ca3af' }}>Memory Size</span>
                            </div>
                            <input 
                                type="range" 
                                min="0" max="50" step="1"
                                value={historyLimit}
                                onChange={e => setHistoryLimit(parseInt(e.target.value))}
                                style={{ width: '100%', marginTop: '8px', accentColor: '#6366f1' }}
                            />
                            {providerType === 'free' && historyLimit > 5 && (
                                <div style={{ fontSize: '11px', color: '#f59e0b', marginTop: '4px' }}>
                                    ⚠️ Free Tier limited to 5 turns max (Auto-capped).
                                </div>
                            )}

                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                                <label style={{ ...labelStyle, marginTop: 0 }}>Overflow Strategy</label>
                                <span style={{ fontSize: '12px', color: '#9ca3af' }}>Memory Management</span>
                            </div>
                            <div style={{ display: 'flex', background: '#f3f4f6', padding: '4px', borderRadius: '8px', marginTop: '8px' }}>
                                <button
                                     onClick={() => setOverflowStrategy('slide')}
                                     style={{
                                         flex: 1, padding: '8px', borderRadius: '6px',
                                         background: overflowStrategy === 'slide' ? 'white' : 'transparent',
                                         boxShadow: overflowStrategy === 'slide' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                                         border: 'none', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                                         color: overflowStrategy === 'slide' ? '#6366f1' : '#6b7280',
                                         transition: 'all 0.2s'
                                     }}
                                >
                                    Slide (Fluid)
                                </button>
                                <button
                                     onClick={() => setOverflowStrategy('reset')}
                                     style={{
                                         flex: 1, padding: '8px', borderRadius: '6px',
                                         background: overflowStrategy === 'reset' ? 'white' : 'transparent',
                                         boxShadow: overflowStrategy === 'reset' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                                         border: 'none', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                                         color: overflowStrategy === 'reset' ? '#6366f1' : '#6b7280',
                                         transition: 'all 0.2s'
                                     }}
                                >
                                    Reset (Cache+)
                                </button>
                            </div>
                            <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px', lineHeight: 1.4 }}>
                                {overflowStrategy === 'slide' 
                                    ? 'Removes oldest message when full. Keeps conversation seamless.' 
                                    : 'Clears entire memory when full. Maximizes reuse of LLM prompt cache.'}
                            </div>
                        </div>
                    </div>

                    <div style={{ marginTop: '32px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                        <button 
                            onClick={onClose}
                            style={{ padding: '10px 20px', borderRadius: '8px', border: 'none', background: '#f3f4f6', color: '#4b5563', fontWeight: 600, cursor: 'pointer' }}
                        >
                            Cancel
                        </button>
                        <button 
                            onClick={handleSave}
                            style={{ padding: '10px 24px', borderRadius: '8px', border: 'none', background: '#6366f1', color: 'white', fontWeight: 600, cursor: 'pointer', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)' }}
                        >
                            Save Configuration
                        </button>
                    </div>
                </div>
            </div>
            
            <style>{`
                @keyframes slideIn {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
                .switch input { opacity: 0; width: 0; height: 0; }
                .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .4s; borderRadius: 24px; }
                .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; borderRadius: 50%; }
                input:checked + .slider { background-color: #6366f1; }
                input:checked + .slider:before { transform: translateX(20px); }
            `}</style>
        </div>
    );
};

export default LLMConfigModal;
