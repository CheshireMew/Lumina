import React, { useState } from 'react';
import { CharacterProfile } from '@core/llm/types';
import { SchemaForm } from './SchemaForm';
import { inputStyle, labelStyle, buttonStyle } from './styles';



interface CharactersTabProps {
    characters: CharacterProfile[];
    setCharacters: (chars: CharacterProfile[]) => void;
    activeCharacterId: string;
    onActivateCharacter: (id: string) => void;
    onDeleteCharacter: (id: string) => void;
    
    // Voice Data
    edgeVoices: any[];
    gptVoices: any[];
    activeTtsEngines: string[];

    // Assets
    availableModels: { name: string; path: string }[];
    ttsPlugins: any[]; // ⚡ Decoupled Plugins
}

export const CharactersTab: React.FC<CharactersTabProps> = ({
    characters,
    setCharacters,
    activeCharacterId,
    onActivateCharacter,
    onDeleteCharacter,
    edgeVoices,
    gptVoices,
    activeTtsEngines,
    availableModels,
    ttsPlugins
}) => {
    const [editingCharId, setEditingCharId] = useState<string | null>(null);

    const handleAddCharacter = () => {
        const timestamp = Date.now();
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

    const handleUpdateCharacter = (id: string, updates: Partial<CharacterProfile>) => {
        setCharacters(characters.map(c => {
            if (c.id === id) {
                const updatedChar = { ...c, ...updates };
                
                // ⚡ 智能 ID 生成逻辑
                if (id.startsWith('new_') && updates.name) {
                    const safeId = updates.name
                        .trim()
                        .toLowerCase()
                        .replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_')
                        .replace(/_+/g, '_');
                    
                    if (safeId.length > 0) {
                        updatedChar.id = safeId;
                        // Side effect: update editing state if id changes
                        // Note: ID change in map loop is tricky but React handles key changes if we are careful.
                    }
                }
                return updatedChar;
            }
            return c;
        }));
        
        // Sync editing ID if it changed
        if (id.startsWith('new_') && updates.name && editingCharId === id) {
             const safeId = updates.name.trim().toLowerCase().replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_').replace(/_+/g, '_');
             if (safeId.length > 0) {
                 setEditingCharId(safeId);
             }
        }
    };

    const handleVoiceConfigChange = (id: string, key: string, value: any) => {
         setCharacters(characters.map(c => {
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

    const handleDeleteClick = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        onDeleteCharacter(id);
    };

    return (
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
                                onClick={() => onActivateCharacter(char.id)}
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
                                            <label style={labelStyle}>Brief Description</label>
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
                                        </label>
                                        <textarea
                                            value={char.systemPrompt || ''}
                                            onChange={(e) => handleUpdateCharacter(char.id, { systemPrompt: e.target.value })}
                                            style={{ ...inputStyle, minHeight: '100px', fontFamily: 'inherit', fontSize: '13px' }}
                                            placeholder="你是一个..."
                                        />
                                    </div>

                                    <div style={{ marginBottom: '15px' }}>
                                        <label style={labelStyle}>Live2D Model</label>
                                        <select
                                            value={char.modelPath || (availableModels[0] ? availableModels[0].path : '')}
                                            onChange={(e) => handleUpdateCharacter(char.id, { modelPath: e.target.value })}
                                            style={inputStyle}
                                        >
                                            {availableModels.length > 0 ? (
                                                availableModels.map(m => (
                                                    <option key={m.path} value={m.path}>{m.name}</option>
                                                ))
                                            ) : (
                                                <option value="">Loading Models...</option>
                                            )}
                                        </select>
                                    </div>

                                    <div style={{ marginBottom: '15px' }}>
                                        <label style={labelStyle}>Voice Configuration</label>

                                        {/* Service Selection (Dynamic) */}
                                        <div style={{ marginBottom: '8px' }}>
                                            <select
                                                value={char.voiceConfig.service || 'edge-tts'}
                                                onChange={(e) => handleVoiceConfigChange(char.id, 'service', e.target.value)}
                                                style={{ ...inputStyle, marginBottom: '5px' }}
                                            >
                                                {ttsPlugins.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} 
                                                        {/* Check availability logic? Using activeTtsEngines (IDs) */}
                                                        {activeTtsEngines.includes(p.id) ? ' ✅' : ' ⚠️'}
                                                    </option>
                                                ))}
                                                {/* Fallback if plugins not loaded */}
                                                {ttsPlugins.length === 0 && <option value="edge-tts">Edge TTS (Default)</option>}
                                            </select>
                                        </div>

                                        {/* Schema-Driven Config Form */}
                                        {(() => {
                                            const currentPlugin = ttsPlugins.find(p => p.id === (char.voiceConfig.service || 'edge-tts'));
                                            if (currentPlugin && currentPlugin.config_schema) {
                                                return (
                                                    <SchemaForm 
                                                        schema={currentPlugin.config_schema}
                                                        values={char.voiceConfig}
                                                        onChange={(k, v) => handleVoiceConfigChange(char.id, k, v)}
                                                        dataSources={{ edgeVoices, gptVoices }}
                                                    />
                                                );
                                            } else {
                                                // Fallback for plugins without schema (Legacy or Custom)
                                                return (
                                                    <div style={{fontSize: '12px', color: '#9ca3af', fontStyle:'italic'}}>
                                                        No configuration schema available for this engine.
                                                    </div>
                                                );
                                            }
                                        })()}
                                    </div>

                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '10px', borderTop: '1px solid #f3f4f6' }}>
                                        <button
                                            onClick={(e) => handleDeleteClick(char.id, e)}
                                            style={{ ...buttonStyle, backgroundColor: '#fee2e2', color: '#b91c1c', border: 'none', padding: '6px 12px', fontSize: '12px' }}
                                        >
                                            Delete
                                        </button>

                                        {activeCharacterId !== char.id && (
                                            <button
                                                onClick={() => onActivateCharacter(char.id)}
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
    );
};
