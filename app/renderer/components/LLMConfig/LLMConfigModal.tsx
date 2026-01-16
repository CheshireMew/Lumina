import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Brain, Cpu, Wand2, X, Sparkles, MessageSquare, Zap } from 'lucide-react';
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
    activeCharacterId?: string;
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
    onSettingsChange,
    activeCharacterId = 'default'
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
    const [overflowStrategy, setOverflowStrategy] = useState<'slide' | 'reset'>('reset'); // Default to Reset (Cache+)
    
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
            
            // Normalize overflowStrategy (Handle legacy/invalid values)
            let strategy = currentLlmSettings.overflowStrategy;
            if (strategy !== 'slide' && strategy !== 'reset') {
                 strategy = 'reset'; // Force default
            }
            setOverflowStrategy(strategy);
            
            // Heuristic to detect provider type & platform
            const url = currentLlmSettings.apiBaseUrl;
            const isFree = url.includes('localhost:8010') || url.includes('127.0.0.1:8010') || !url;
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
        let finalBaseUrl = baseUrl;
        let finalModel = modelName;

        if (providerType === 'free') {
             // Force Free settings
             finalBaseUrl = 'http://127.0.0.1:8010/v1'; // Local marker for Free Tier
             finalModel = modelName || 'gpt-4o-mini';
        }

        onSettingsChange(apiKey, finalBaseUrl, finalModel, temperature, thinkingEnabled, historyLimit, overflowStrategy, topP, presencePenalty, frequencyPenalty);
        onClose();
    };

    // --- Galgame Styles ---
    const primaryColor = '#ec4899'; // Pink-500
    const secondaryColor = '#8b5cf6'; // Violet-500
    
    const glassStyle = {
        background: 'rgba(255, 255, 255, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.5)',
        boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
    };

    const inputStyle = {
        width: '100%',
        padding: '10px 14px',
        borderRadius: '12px',
        border: '1px solid rgba(236, 72, 153, 0.2)', // Pink-ish border
        fontSize: '14px',
        marginTop: '6px',
        boxSizing: 'border-box' as const,
        outline: 'none',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        background: 'rgba(255, 255, 255, 0.6)',
        color: '#4b5563'
    };

    const labelStyle = {
        display: 'block',
        fontSize: '13px',
        fontWeight: 600,
        color: '#6b7280', // Cool Gray
        marginTop: '16px',
        letterSpacing: '0.02em'
    };

    const sectionTitleStyle = {
        fontSize: '12px',
        fontWeight: 700,
        color: primaryColor,
        textTransform: 'uppercase' as const,
        letterSpacing: '0.05em',
        marginBottom: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.4)',
            backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 20000,
            padding: '20px' // Mobile safe
        }}>
            <div style={{
                width: '520px',
                maxHeight: '85vh', // Prevent overflow
                display: 'flex',
                flexDirection: 'column',
                ...glassStyle,
                borderRadius: '28px',
                animation: 'slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)', // Bouncy entrance
                overflow: 'hidden'
            }}>
                {/* Header - Fixed */}
                <div style={{ 
                    padding: '20px 24px', 
                    background: `linear-gradient(135deg, ${primaryColor}15 0%, ${secondaryColor}15 100%)`, // Very subtle gradient
                    borderBottom: '1px solid rgba(255,255,255,0.5)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    flexShrink: 0
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ 
                            background: 'white', 
                            padding: '8px', 
                            borderRadius: '14px',
                            boxShadow: '0 4px 12px rgba(236, 72, 153, 0.15)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}>
                            <Sparkles size={20} color={primaryColor} />
                        </div>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#1f2937', letterSpacing: '-0.02em' }}>
                                Neural Link
                            </h2>
                            <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: '#6b7280', fontWeight: 500 }}>
                                Configure Agent Intelligence
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose} 
                        className="hover-btn"
                        style={{ 
                            background: 'white', border: 'none', color: '#9ca3af', 
                            cursor: 'pointer', padding: '8px', borderRadius: '12px',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            transition: 'all 0.2s'
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content - Scrollable */}
                <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }} className="custom-scrollbar">
                    
                    {/* Provider Toggle */}
                    <div style={{ display: 'flex', background: 'rgba(255,255,255,0.5)', padding: '5px', borderRadius: '16px', marginBottom: '24px', border: '1px solid rgba(255,255,255,0.6)' }}>
                        {[
                            { id: 'free', icon: Wand2, label: 'Free (Magic)' },
                            { id: 'custom', icon: Cpu, label: 'Custom (Pro)' }
                        ].map(type => (
                            <button
                                key={type.id}
                                onClick={() => setProviderType(type.id as any)}
                                style={{
                                    flex: 1, padding: '10px', borderRadius: '12px',
                                    background: providerType === type.id ? 'white' : 'transparent',
                                    boxShadow: providerType === type.id ? '0 4px 12px rgba(0,0,0,0.05)' : 'none',
                                    border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '13px',
                                    color: providerType === type.id ? primaryColor : '#9ca3af',
                                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)', 
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                                }}
                            >
                                <type.icon size={16} strokeWidth={2.5} /> {type.label}
                            </button>
                        ))}
                    </div>

                    {/* Form Content */}
                    <div style={{ animation: 'fadeIn 0.3s ease' }}>
                        {providerType === 'free' ? (
                            <div style={{ 
                                background: `linear-gradient(180deg, ${primaryColor}08 0%, ${secondaryColor}08 100%)`, 
                                padding: '20px', borderRadius: '20px', 
                                border: `1px solid ${primaryColor}20` 
                            }}>
                                <div style={{ fontSize: '14px', fontWeight: 700, color: primaryColor, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Sparkles size={16} /> Pollinations Magic
                                </div>
                                <div style={{ fontSize: '13px', color: '#4b5563', lineHeight: 1.6, marginBottom: '16px' }}>
                                    Privacy-focused proxy for OpenAI, Claude, and Llama. <br/>
                                    <strong>No API Key required. Unlimited usage.</strong>
                                </div>
                                
                                <label style={labelStyle}>Select Persona</label>
                                <select 
                                    style={inputStyle}
                                    value={modelName}
                                    onChange={(e) => setModelName(e.target.value)}
                                >
                                    <option value="gpt-4o-mini">Smart Assistant (GPT-4o Mini)</option>
                                    <option value="claude-3-haiku">Creative Muse (Claude 3 Haiku)</option>
                                    <option value="llama-3-70b">Logician (Llama 3 70B)</option>
                                    <option value="midijourney">Bard (Musical/Midijourney)</option>
                                    <option value="searchgpt">Navigator (Web Connected)</option>
                                </select>
                            </div>
                        ) : (
                            // Custom
                            <>
                                <div>
                                    <label style={labelStyle}>Provider Platform</label>
                                    <div style={{ position: 'relative' }}>
                                        <select 
                                            style={{ ...inputStyle, appearance: 'none' }}
                                            value={selectedPlatform}
                                            onChange={(e) => {
                                                const plat = e.target.value;
                                                setSelectedPlatform(plat);
                                                if (plat !== 'custom') {
                                                    const preset = PRESET_PROVIDERS[plat];
                                                    setBaseUrl(preset.baseUrl);
                                                    if (plat === 'deepseek') {
                                                        setModelName(thinkingEnabled ? 'deepseek-reasoner' : 'deepseek-chat');
                                                    } else {
                                                        setModelName(preset.defaultModel);
                                                    }
                                                }
                                            }}
                                        >
                                            <option value="deepseek">🐋 DeepSeek (Recommended)</option>
                                            <option value="openai">🤖 OpenAI</option>
                                            <option value="google">🌟 Google Gemini</option>
                                            <option value="anthropic">🧠 Anthropic Claude</option>
                                            <option value="siliconflow">⚡ SiliconFlow</option>
                                            <option value="custom">🛠️ Custom / Local</option>
                                        </select>
                                        <div style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: primaryColor }}>
                                            <Zap size={16} />
                                        </div>
                                    </div>
                                </div>

                                {selectedPlatform === 'custom' && (
                                    <div style={{ animation: 'slideDown 0.2s' }}>
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
                                    <label style={labelStyle}>Secret Key</label>
                                    <input 
                                        type="password"
                                        style={inputStyle} 
                                        value={apiKey} 
                                        onChange={e => setApiKey(e.target.value)}
                                        placeholder="sk-..."
                                    />
                                </div>

                                {selectedPlatform === 'deepseek' ? (
                                    <div style={{ marginTop: '20px', padding: '16px', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <div style={{ fontSize: '14px', fontWeight: 700, color: '#334155' }}>
                                                    {thinkingEnabled ? 'DeepSeek R1 (Reasoner)' : 'DeepSeek V3 (Chat)'}
                                                </div>
                                                <div style={{ fontSize: '12px', color: '#64748b', marginTop:'4px' }}>
                                                    {thinkingEnabled ? 'Uses CoT reasoning. Slower but smarter.' : 'Standard ultra-fast chat model.'}
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
                                    <div>
                                        <label style={labelStyle}>Model ID</label>
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

                        {/* Sliders Section */}
                        <div style={{ marginTop: '32px' }}>
                            <div style={sectionTitleStyle}>
                                <Brain size={14} /> Cognitive Parameters
                            </div>
                            
                            {/* Temperature */}
                            <div style={{ background: 'rgba(255,255,255,0.5)', padding: '16px', borderRadius: '16px', marginBottom: '16px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>Creativity (Temperature)</span>
                                    <span style={{ fontSize: '13px', fontWeight: 700, color: primaryColor }}>{temperature}</span>
                                </div>
                                <input 
                                    type="range" min="0" max="2" step="0.1" value={temperature}
                                    onChange={e => setTemperature(parseFloat(e.target.value))}
                                    className="gal-range"
                                />
                                
                                {/* Advanced Cognitive Params - Restored */}
                                <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px dashed #e5e7eb', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                                    <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>Top P</span>
                                            <span style={{ fontSize: '12px', color: secondaryColor, fontWeight: 700 }}>{topP}</span>
                                        </div>
                                        <input 
                                            type="range" min="0" max="1" step="0.05" value={topP}
                                            onChange={e => setTopP(parseFloat(e.target.value))}
                                            className="gal-range violet"
                                        />
                                    </div>
                                    <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>Frequency Pen</span>
                                            <span style={{ fontSize: '12px', color: secondaryColor, fontWeight: 700 }}>{frequencyPenalty}</span>
                                        </div>
                                        <input 
                                            type="range" min="0" max="2" step="0.1" value={frequencyPenalty}
                                            onChange={e => setFrequencyPenalty(parseFloat(e.target.value))}
                                            className="gal-range violet"
                                        />
                                    </div>
                                    <div style={{ gridColumn: 'span 2' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>Presence Penalty (Topic Freshness)</span>
                                            <span style={{ fontSize: '12px', color: secondaryColor, fontWeight: 700 }}>{presencePenalty}</span>
                                        </div>
                                        <input 
                                            type="range" min="0" max="2" step="0.1" value={presencePenalty}
                                            onChange={e => setPresencePenalty(parseFloat(e.target.value))}
                                            className="gal-range violet"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Context & Overflow - Key Change Here */}
                            <div style={sectionTitleStyle}>
                                <MessageSquare size={14} /> Memory Management
                            </div>
                            
                            <div style={{ background: 'white', padding: '20px', borderRadius: '20px', border: '1px solid rgba(0,0,0,0.05)', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
                                <div style={{ marginBottom: '20px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>Context Window</span>
                                        <span style={{ fontSize: '13px', fontWeight: 700, color: secondaryColor }}>{historyLimit} turns</span>
                                    </div>
                                    <input 
                                        type="range" min="5" max="50" step="1" value={historyLimit}
                                        onChange={e => setHistoryLimit(parseInt(e.target.value))}
                                        className="gal-range violet"
                                    />
                                    {providerType === 'free' && historyLimit > 5 && (
                                        <div style={{ fontSize: '11px', color: '#f59e0b', marginTop: '6px', fontWeight: 500 }}>
                                            ⚠️ Free Tier auto-caps at 5 turns.
                                        </div>
                                    )}
                                </div>

                                <div style={{ borderTop: '1px dashed #e5e7eb', paddingTop: '16px' }}>
                                    <label style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563', display: 'block', marginBottom: '12px' }}>
                                        Overflow Strategy
                                    </label>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                        <button
                                             onClick={() => setOverflowStrategy('slide')}
                                             style={{
                                                 padding: '12px', borderRadius: '12px',
                                                 // IMPROVED VISIBILITY: Solid background for active state
                                                 background: overflowStrategy === 'slide' ? primaryColor : '#f9fafb', 
                                                 border: overflowStrategy === 'slide' ? `2px solid ${primaryColor}` : '2px solid transparent',
                                                 cursor: 'pointer', textAlign: 'left',
                                                 transition: 'all 0.2s', position: 'relative', overflow: 'hidden'
                                             }}
                                        >
                                            <div style={{ fontSize: '13px', fontWeight: 700, color: overflowStrategy === 'slide' ? 'white' : '#6b7280' }}>Slide</div>
                                            <div style={{ fontSize: '10px', color: overflowStrategy === 'slide' ? 'rgba(255,255,255,0.9)' : '#9ca3af', marginTop: '2px' }}>Rolling Window</div>
                                            {overflowStrategy === 'slide' && <Sparkles size={60} color="white" style={{ position: 'absolute', right: -20, bottom: -20, opacity: 0.2 }} />}
                                        </button>

                                        <button
                                             onClick={() => setOverflowStrategy('reset')}
                                             style={{
                                                 padding: '12px', borderRadius: '12px',
                                                 // IMPROVED VISIBILITY: Solid background for active state
                                                 background: overflowStrategy === 'reset' ? secondaryColor : '#f9fafb',
                                                 border: overflowStrategy === 'reset' ? `2px solid ${secondaryColor}` : '2px solid transparent',
                                                 cursor: 'pointer', textAlign: 'left',
                                                 transition: 'all 0.2s', position: 'relative', overflow: 'hidden'
                                             }}
                                        >
                                            <div style={{ fontSize: '13px', fontWeight: 700, color: overflowStrategy === 'reset' ? 'white' : '#6b7280' }}>Reset</div>
                                            <div style={{ fontSize: '10px', color: overflowStrategy === 'reset' ? 'rgba(255,255,255,0.9)' : '#9ca3af', marginTop: '2px' }}>Clear & Cache+</div>
                                            {overflowStrategy === 'reset' && <Zap size={60} color="white" style={{ position: 'absolute', right: -20, bottom: -20, opacity: 0.2 }} />}
                                        </button>
                                    </div>
                                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '12px', background: '#f3f4f6', padding: '8px 12px', borderRadius: '8px' }}>
                                        {overflowStrategy === 'slide' 
                                            ? 'ℹ️ Seamless conversation. Oldest context slides out.' 
                                            : 'ℹ️ Optimized for speed & cost. Clears memory when full.'}
                                    </div>
                                    </div>
                                    
                                    {/* Reset Context Button */}
                                    <button 
                                        onClick={async () => {
                                            if(confirm('Clear short-term memory (Context) for this session?')) {
                                                try {
                                                    await fetch(`${API_CONFIG.BASE_URL}/memory/context/clear`, {
                                                        method: 'POST',
                                                        headers: {'Content-Type': 'application/json'},
                                                        body: JSON.stringify({ character_id: activeCharacterId })
                                                    });
                                                    alert('Session Context Cleared!');
                                                } catch(e) { alert('Failed to clear context'); }
                                            }
                                        }}
                                        className="w-full mt-4 py-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded hover:bg-red-100 flex justify-center items-center gap-2"
                                        style={{ marginTop: '16px', padding: '10px', borderRadius: '12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontWeight: 600, cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
                                    >
                                        <Brain size={16} /> Reset Session Context
                                    </button>
                                </div>

                        </div>
                    </div>
                </div>

                {/* Footer - Fixed */}
                <div style={{ 
                    padding: '20px 24px', 
                    background: 'rgba(255,255,255,0.8)', 
                    borderTop: '1px solid rgba(0,0,0,0.05)',
                    display: 'flex', justifyContent: 'flex-end', gap: '12px',
                    backdropFilter: 'blur(10px)',
                    flexShrink: 0
                }}>
                    <button 
                        onClick={onClose}
                        style={{ 
                            padding: '10px 20px', borderRadius: '12px', 
                            border: 'none', background: 'transparent', 
                            color: '#6b7280', fontWeight: 600, cursor: 'pointer',
                            fontSize: '14px'
                        }}
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={handleSave}
                        style={{ 
                            padding: '10px 24px', borderRadius: '12px', 
                            border: 'none', 
                            background: `linear-gradient(135deg, ${primaryColor} 0%, ${secondaryColor} 100%)`, 
                            color: 'white', fontWeight: 700, cursor: 'pointer', 
                            boxShadow: '0 4px 12px rgba(236, 72, 153, 0.3)',
                            fontSize: '14px',
                            display: 'flex', alignItems: 'center', gap: '8px'
                        }}
                    >
                        <SettingsIcon size={16} /> Save System
                    </button>
                </div>
            </div>
            
            <style>{`
                @keyframes slideIn {
                    from { transform: scale(0.95) translateY(20px); opacity: 0; }
                    to { transform: scale(1) translateY(0); opacity: 1; }
                }
                .hover-btn:hover { background: #f3f4f6 !important; }
                
                .gal-range {
                    -webkit-appearance: none; width: 100%; height: 6px; background: #e5e7eb; border-radius: 4px; outline: none;
                }
                .gal-range::-webkit-slider-thumb {
                    -webkit-appearance: none; appearance: none;
                    width: 20px; height: 20px; border-radius: 50%; 
                    background: ${primaryColor}; 
                    cursor: pointer; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                    transition: transform 0.1s;
                }
                .gal-range::-webkit-slider-thumb:hover { transform: scale(1.1); }
                .gal-range.violet::-webkit-slider-thumb { background: ${secondaryColor}; }

                .switch { position: relative; display: inline-block; width: 48px; height: 26px; }
                .switch input { opacity: 0; width: 0; height: 0; }
                .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #e5e7eb; transition: .4s; borderRadius: 24px; }
                .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: white; transition: .4s; borderRadius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                input:checked + .slider { background-color: ${primaryColor}; }
                input:checked + .slider:before { transform: translateX(22px); }
                
                .custom-scrollbar::-webkit-scrollbar { width: 6px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 3px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }
            `}</style>
        </div>
    );
};

export default LLMConfigModal;
