import React, { useState, useEffect } from 'react';
import { X, User, Box, Layers, Image as ImageIcon, Plus, Trash2, Edit2, Check } from 'lucide-react';
import { CharacterProfile } from '@core/llm/types';
import { SchemaForm } from './Settings/SchemaForm';
import { API_CONFIG } from '../config';

// Reusing styles from Settings/styles for consistency
const inputStyle = {
    width: '100%', padding: '8px 12px', border: '1px solid #d1d5db',
    borderRadius: '6px', fontSize: '14px', outline: 'none', transition: 'border-color 0.15s'
};
const labelStyle = {
    display: 'block', fontSize: '12px', fontWeight: 600,
    color: '#4b5563', marginBottom: '4px', textTransform: 'uppercase' as const, letterSpacing: '0.02em'
};
const buttonStyle = {
    cursor: 'pointer', border: 'none', borderRadius: '6px',
    backgroundColor: '#6366f1', color: 'white', fontWeight: 500,
    transition: 'all 0.15s'
};

export interface AvatarModel {
    name: string;
    path: string;
    type?: 'live2d' | 'vrm' | 'sprite';
    thumbnail?: string;
}

interface AvatarSelectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    
    // Character Management Props
    activeCharacterId: string;
    activeCharacter?: CharacterProfile; // Optional, can derive from list if needed, but passed for convenience
    characters: CharacterProfile[];
    setCharacters: (chars: CharacterProfile[]) => void;
    onActivateCharacter: (id: string) => void;
    onDeleteCharacter: (id: string) => void;
    onSaveCharacters: (chars: CharacterProfile[], deletedIds: string[]) => Promise<void>; // New prop to trigger save

    // Assets & Config
    availableModels?: AvatarModel[];
    edgeVoices: any[];
    gptVoices: any[];
    activeTtsEngines: string[];
    ttsPlugins: any[];
}

const AvatarSelectorModal: React.FC<AvatarSelectorModalProps> = ({
    isOpen, onClose,
    activeCharacterId, characters, setCharacters,
    onActivateCharacter, onDeleteCharacter, onSaveCharacters,
    availableModels = [],
    edgeVoices, gptVoices, activeTtsEngines, ttsPlugins
}) => {
    // View State: 'list' (Character List) | 'edit' (Edit specific Char) | 'picker' (Pick model for acting char)
    // Actually, CharactersTab uses an expanded accordion style. Let's keep that for familiarity,
    // but we need a specific 'picker' view when selecting a model for a character.
    
    // We can use a stack or simple view state
    const [view, setView] = useState<'main' | 'picker'>('main');
    
    // State for Character Management
    const [editingCharId, setEditingCharId] = useState<string | null>(null);
    const [deletedIds, setDeletedIds] = useState<string[]>([]);
    
    // State for Picker Context
    const [pickerTargetCharId, setPickerTargetCharId] = useState<string | null>(null);
    const [customPath, setCustomPath] = useState('');
    
    // Internal Models State (fetched if not provided)
    const [models, setModels] = useState<AvatarModel[]>(availableModels || []);

    useEffect(() => {
        if (isOpen) {
             fetch(`${API_CONFIG.BASE_URL}/characters/models`)
                .then(res => res.json())
                .then(data => {
                    if (data.models) {
                        setModels(data.models.map((m: any) => ({
                            name: m.name,
                            path: m.path,
                            type: m.type,
                            thumbnail: m.thumbnail
                        })));
                    }
                })
                .catch(err => console.error("Failed to fetch models", err));
        }
    }, [isOpen]);

    if (!isOpen) return null;

    // --- Actions ---

    const handleAddCharacter = () => {
        const timestamp = Date.now();
        const tempId = `new_${timestamp}`;
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

    const handleUpdateCharacter = (id: string, updates: Partial<CharacterProfile>) => {
        setCharacters(characters.map(c => {
            if (c.id === id) {
                const updatedChar = { ...c, ...updates };
                // Intelligent ID generation for new characters
                if (id.startsWith('new_') && updates.name) {
                    const safeId = updates.name.trim().toLowerCase()
                        .replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_').replace(/_+/g, '_');
                    if (safeId.length > 0) updatedChar.id = safeId;
                }
                return updatedChar;
            }
            return c;
        }));
        
        // Sync editing/picker ID if it changed due to rename
        if (id.startsWith('new_') && updates.name && editingCharId === id) {
             const safeId = updates.name.trim().toLowerCase().replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '_').replace(/_+/g, '_');
             if (safeId.length > 0) {
                 setEditingCharId(safeId);
                 if (pickerTargetCharId === id) setPickerTargetCharId(safeId);
             }
        }
    };

    const handleVoiceConfigChange = (id: string, key: string, value: any) => {
         setCharacters(characters.map(c => (c.id === id ? { ...c, voiceConfig: { ...c.voiceConfig, [key]: value } } : c)));
    };

    const handleModelPick = (path: string) => {
        if (pickerTargetCharId) {
            handleUpdateCharacter(pickerTargetCharId, { modelPath: path });
            setView('main');
            setPickerTargetCharId(null);
        }
    };

    const handleDeleteClick = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm('Delete this character? This action is pending save.')) {
            setDeletedIds([...deletedIds, id]);
            // Optimistic update
            onDeleteCharacter(id); // Using parent's prop which might just filter the list
        }
    };

    const handleSaveAndClose = async () => {
        await onSaveCharacters(characters, deletedIds);
        onClose();
    };


    // --- Renders ---

    const renderPicker = () => (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <button onClick={() => setView('main')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#666' }}>
                    ← Back
                </button>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Select Avatar Model</h3>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', paddingRight: 5 }}>
                 <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 15 }}>
                    {models.map((model, idx) => {
                        const targetChar = characters.find(c => c.id === pickerTargetCharId);
                        const isSelected = targetChar?.modelPath === model.path;
                        return (
                            <div 
                                key={idx}
                                onClick={() => handleModelPick(model.path)}
                                style={{
                                    border: isSelected ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                                    borderRadius: 12, padding: 10, cursor: 'pointer', textAlign: 'center',
                                    backgroundColor: isSelected ? '#eff6ff' : 'white',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <div style={{ 
                                    width: 48, height: 48, borderRadius: '50%', backgroundColor: '#e5e7eb', 
                                    margin: '0 auto 10px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden'
                                }}>
                                    {model.thumbnail ? <img src={model.thumbnail} alt="" style={{width:'100%', height:'100%', objectFit:'cover'}} /> : 
                                     (model.type === 'vrm' ? <Box size={24} /> : 
                                      model.type === 'sprite' ? <ImageIcon size={24} /> :
                                      <Layers size={24} />)}
                                </div>
                                <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{model.name}</div>
                                <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: 4 }}>{(model.type || 'unknown').toUpperCase()}</div>
                            </div>
                        );
                    })}
                </div>

                <div style={{ marginTop: 20, paddingTop: 20, borderTop: '1px solid #eee' }}>
                    <h4 style={{ fontSize: '0.9rem', marginBottom: 10 }}>Custom Path</h4>
                    <div style={{ display: 'flex', gap: 10 }}>
                        <input 
                            type="text" placeholder="/models/my_avatar.vrm" 
                            value={customPath} onChange={e => setCustomPath(e.target.value)}
                            style={{ flex: 1, padding: '8px', borderRadius: 6, border: '1px solid #ddd' }}
                        />
                        <button 
                            onClick={() => handleModelPick(customPath)}
                            disabled={!customPath}
                            style={{ ...buttonStyle, padding: '0 15px', opacity: customPath ? 1 : 0.5 }}
                        >
                            Use Path
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );

    const renderMain = () => (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
                <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>Character Management</h3>
                <button onClick={handleAddCharacter} style={{ ...buttonStyle, padding: '6px 12px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Plus size={16} /> New Character
                </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', paddingRight: 5, paddingBottom: 20 }}>
                 {characters.length === 0 && <div style={{textAlign: 'center', color: '#999', padding: 20}}>No characters found.</div>}
                 
                 {[...characters].sort((a, b) => (a.id === activeCharacterId ? -1 : b.id === activeCharacterId ? 1 : 0))
                    .map(char => {
                        const isExpanded = editingCharId === char.id;
                        const isActive = activeCharacterId === char.id;
                        
                        return (
                            <div key={char.id} style={{
                                marginBottom: 10, borderRadius: 8,
                                border: isActive ? '2px solid #818cf8' : '1px solid #e5e7eb',
                                backgroundColor: 'white', overflow: 'hidden'
                            }}>
                                {/* Header */}
                                <div 
                                    onClick={() => onActivateCharacter(char.id)}
                                    style={{
                                        padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                        cursor: 'pointer', backgroundColor: isActive ? '#f5f7ff' : 'white'
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{
                                            width: 36, height: 36, borderRadius: '50%', backgroundColor: isActive ? '#c7d2fe' : '#f3f4f6',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                                        }}>
                                            {isActive ? <Check size={18} color="#4f46e5" /> : <User size={18} color="#9ca3af" />}
                                        </div>
                                        <div>
                                            <div style={{ fontWeight: 600, color: '#1f2937' }}>{char.name} {isActive && <span style={{fontSize:'10px', background:'#4f46e5', color:'white', padding:'2px 6px', borderRadius:10, marginLeft:5}}>ACTIVE</span>}</div>
                                            <div style={{ fontSize: '12px', color: '#6b7280', maxWidth: 300, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                                                {char.description || 'No description'}
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div style={{ display: 'flex', gap: 5 }}>
                                         <button
                                            onClick={(e) => { e.stopPropagation(); setEditingCharId(isExpanded ? null : char.id); }}
                                            style={{ padding: 6, borderRadius: 4, background: isExpanded ? '#e5e7eb' : 'transparent', border:'none', cursor:'pointer' }}
                                        >
                                            <Edit2 size={16} color="#4b5563" />
                                        </button>
                                    </div>
                                </div>

                                {/* Body */}
                                {isExpanded && (
                                    <div style={{ padding: 15, borderTop: '1px solid #f3f4f6', backgroundColor: '#fafafa' }} onClick={e => e.stopPropagation()}>
                                        {/* ID */}
                                        <div style={{ marginBottom: 10 }}>
                                            <label style={labelStyle}>Folder Name / ID <span style={{fontWeight:400, textTransform:'none', color:'#999'}}>({char.id.startsWith('new_') ? 'Auto-generated' : 'Fixed'})</span></label>
                                            <input value={char.id} readOnly style={{ ...inputStyle, background: '#f3f4f6', color: '#666', fontFamily: 'monospace' }} />
                                        </div>

                                        {/* Name & Desc */}
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
                                            <div>
                                                <label style={labelStyle}>Name</label>
                                                <input value={char.name} onChange={e => handleUpdateCharacter(char.id, { name: e.target.value })} style={inputStyle} />
                                            </div>
                                            <div>
                                                <label style={labelStyle}>Description</label>
                                                <input value={char.description} onChange={e => handleUpdateCharacter(char.id, { description: e.target.value })} style={inputStyle} />
                                            </div>
                                        </div>

                                        {/* System Prompt */}
                                        <div style={{ marginBottom: 15 }}>
                                            <label style={labelStyle}>System Prompt</label>
                                            <textarea 
                                                value={char.systemPrompt || ''} 
                                                onChange={e => handleUpdateCharacter(char.id, { systemPrompt: e.target.value })}
                                                style={{ ...inputStyle, minHeight: 80, fontFamily: 'inherit' }}
                                            />
                                        </div>

                                        {/* Model Selector */}
                                        <div style={{ marginBottom: 15 }}>
                                            <label style={labelStyle}>Avatar Model</label>
                                            <div style={{ display: 'flex', gap: 10 }}>
                                                <input 
                                                    value={char.modelPath || ''} readOnly 
                                                    style={{ ...inputStyle, background: '#f9fafb', cursor: 'pointer' }}
                                                    onClick={() => { setPickerTargetCharId(char.id); setView('picker'); }}
                                                    placeholder="Select a model..."
                                                />
                                                <button 
                                                    onClick={() => { setPickerTargetCharId(char.id); setView('picker'); }}
                                                    style={{ ...buttonStyle, padding: '0 15px', backgroundColor: '#3b82f6' }}
                                                >
                                                    Select
                                                </button>
                                            </div>
                                        </div>

                                        {/* Voice Config */}
                                        <div style={{ marginBottom: 15, padding: 10, border: '1px solid #e5e7eb', borderRadius: 8, backgroundColor: 'white' }}>
                                            <label style={{ ...labelStyle, marginBottom: 10 }}>Voice Configuration</label>
                                            <select 
                                                value={char.voiceConfig.service || 'edge-tts'}
                                                onChange={e => handleVoiceConfigChange(char.id, 'service', e.target.value)}
                                                style={{ ...inputStyle, marginBottom: 10 }}
                                            >
                                                {ttsPlugins.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} {activeTtsEngines.includes(p.id) ? '✅' : '⚠️'}
                                                    </option>
                                                ))}
                                                {ttsPlugins.length === 0 && <option value="edge-tts">Edge TTS</option>}
                                            </select>
                                            
                                            {/* Schema Form */}
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
                                                }
                                                return <div style={{fontSize:12, color:'#999'}}>No schema available</div>;
                                            })()}
                                        </div>

                                        {/* Actions */}
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10 }}>
                                            <button 
                                                onClick={(e) => handleDeleteClick(char.id, e)}
                                                style={{ ...buttonStyle, backgroundColor: '#fee2e2', color: '#dc2626', padding: '6px 12px' }}
                                            >
                                                <Trash2 size={16} /> Delete
                                            </button>
                                            
                                            {char.id !== activeCharacterId && (
                                                <button 
                                                    onClick={() => onActivateCharacter(char.id)}
                                                    style={{ ...buttonStyle, backgroundColor: '#e0e7ff', color: '#4f46e5', padding: '6px 12px' }}
                                                >
                                                    Set Active
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

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 3000
        }}>
            <div style={{
                backgroundColor: 'white', borderRadius: '16px',
                width: '650px', height: '80vh',
                display: 'flex', flexDirection: 'column',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)', overflow: 'hidden'
            }}>
                {/* Modal View Content */}
                <div style={{ flex: 1, padding: 25, overflow: 'hidden' }}>
                    {view === 'main' ? renderMain() : renderPicker()}
                </div>

                {/* Sticky Footer */}
                {view === 'main' && (
                    <div style={{ padding: '15px 25px', borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end', gap: 10, background: '#f9fafb' }}>
                        <button onClick={onClose} style={{ ...buttonStyle, backgroundColor: 'white', color: '#374151', border: '1px solid #d1d5db', padding: '8px 16px' }}>Cancel</button>
                        <button onClick={handleSaveAndClose} style={{ ...buttonStyle, padding: '8px 24px' }}>Save Changes</button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AvatarSelectorModal;
