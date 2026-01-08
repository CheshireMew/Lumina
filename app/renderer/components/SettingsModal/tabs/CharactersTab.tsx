/**
 * Characters Tab - 角色管理
 */
import React from 'react';
import { CharacterProfile } from '@core/llm/types';
import { inputStyle, labelStyle, buttonStyle } from '../styles';
import { AVAILABLE_MODELS, VoiceInfo } from '../types';

interface CharactersTabProps {
    characters: CharacterProfile[];
    activeCharacterId: string;
    editingCharId: string | null;
    setEditingCharId: (id: string | null) => void;
    edgeVoices: VoiceInfo[];
    gptVoices: VoiceInfo[];
    
    // Handlers
    onAddCharacter: () => void;
    onDeleteCharacter: (id: string, e: React.MouseEvent) => void;
    onUpdateCharacter: (id: string, updates: Partial<CharacterProfile>) => void;
    onVoiceConfigChange: (id: string, key: string, value: any) => void;
    onActivateCharacter: (id: string) => void;
}

export const CharactersTab: React.FC<CharactersTabProps> = ({
    characters, activeCharacterId, editingCharId, setEditingCharId,
    edgeVoices, gptVoices,
    onAddCharacter, onDeleteCharacter, onUpdateCharacter, onVoiceConfigChange, onActivateCharacter
}) => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#374151' }}>
                    Character Profiles ({characters.length})
                </h3>
                <button 
                    onClick={onAddCharacter} 
                    style={{ ...buttonStyle, padding: '4px 10px', fontSize: '12px' }}
                >
                    + Add New
                </button>
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
                        <CharacterCard
                            key={char.id}
                            character={char}
                            isActive={isActive}
                            isExpanded={isExpanded}
                            edgeVoices={edgeVoices}
                            gptVoices={gptVoices}
                            onToggleExpand={() => setEditingCharId(isExpanded ? null : char.id)}
                            onActivate={() => onActivateCharacter(char.id)}
                            onDelete={(e) => onDeleteCharacter(char.id, e)}
                            onUpdate={(updates) => onUpdateCharacter(char.id, updates)}
                            onVoiceConfigChange={(key, value) => onVoiceConfigChange(char.id, key, value)}
                        />
                    );
                })}
            </div>
        </div>
    );
};

// 单个角色卡片组件
interface CharacterCardProps {
    character: CharacterProfile;
    isActive: boolean;
    isExpanded: boolean;
    edgeVoices: VoiceInfo[];
    gptVoices: VoiceInfo[];
    onToggleExpand: () => void;
    onActivate: () => void;
    onDelete: (e: React.MouseEvent) => void;
    onUpdate: (updates: Partial<CharacterProfile>) => void;
    onVoiceConfigChange: (key: string, value: any) => void;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
    character: char, isActive, isExpanded, edgeVoices, gptVoices,
    onToggleExpand, onActivate, onDelete, onUpdate, onVoiceConfigChange
}) => {
    return (
        <div style={{
            backgroundColor: 'white', borderRadius: '8px',
            border: isActive ? '2px solid #6366f1' : '1px solid #e5e7eb',
            overflow: 'hidden', transition: 'all 0.2s',
            boxShadow: isActive ? '0 4px 6px -1px rgba(99, 102, 241, 0.1)' : 'none'
        }}>
            {/* Card Header */}
            <div
                onClick={onActivate}
                style={{
                    padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    cursor: 'pointer', backgroundColor: isActive ? '#f5f7ff' : 'white'
                }}
                title="点击切换到此角色"
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
                    <div style={{
                        width: '32px', height: '32px', borderRadius: '50%', 
                        backgroundColor: isActive ? '#c7d2fe' : '#e0e7ff',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px'
                    }}>
                        {char.id.startsWith('new_') ? '🆕' : '👤'}
                    </div>
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '14px', color: '#1f2937' }}>
                            {char.name}
                            {isActive && (
                                <span style={{ 
                                    fontSize: '11px', color: '#ffffff', backgroundColor: '#6366f1', 
                                    padding: '2px 8px', borderRadius: '10px', marginLeft: '8px' 
                                }}>Active</span>
                            )}
                        </div>
                        <div style={{ fontSize: '12px', color: '#6b7280' }}>{char.description}</div>
                    </div>
                </div>
                
                {/* Edit Toggle Button */}
                <div 
                    onClick={(e) => { e.stopPropagation(); onToggleExpand(); }}
                    style={{ 
                        padding: '8px', borderRadius: '4px', color: '#9ca3af', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: '30px'
                    }}
                    title={isExpanded ? "收起编辑" : "编辑详情"}
                >
                    {isExpanded ? '▲' : '⚙️'}
                </div>
            </div>

            {/* Expanded Edit Form */}
            {isExpanded && (
                <div style={{ padding: '15px', borderTop: '1px solid #f3f4f6', backgroundColor: '#fff' }} 
                     onClick={(e) => e.stopPropagation()}>
                    
                    {/* ID Display */}
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
                                ...inputStyle, backgroundColor: '#f9fafb', 
                                color: char.id.startsWith('new_') ? '#4f46e5' : '#6b7280',
                                fontFamily: 'monospace'
                            }}
                        />
                    </div>

                    {/* Name & Description */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                        <div>
                            <label style={labelStyle}>Name</label>
                            <input
                                value={char.name}
                                onChange={(e) => onUpdate({ name: e.target.value })}
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label style={labelStyle}>Brief Description</label>
                            <input
                                value={char.description}
                                onChange={(e) => onUpdate({ description: e.target.value })}
                                style={inputStyle}
                            />
                        </div>
                    </div>

                    {/* System Prompt */}
                    <div style={{ marginBottom: '10px' }}>
                        <label style={labelStyle}>System Prompt (AI Identity)</label>
                        <textarea
                            value={char.systemPrompt || ''}
                            onChange={(e) => onUpdate({ systemPrompt: e.target.value })}
                            style={{ ...inputStyle, minHeight: '100px', fontFamily: 'inherit', fontSize: '13px' }}
                            placeholder="你是一个18岁的活泼可爱的女孩子..."
                        />
                    </div>

                    {/* Live2D Model */}
                    <div style={{ marginBottom: '15px' }}>
                        <label style={labelStyle}>Live2D Model</label>
                        <select
                            value={char.modelPath || '/live2d/Hiyori/Hiyori.model3.json'}
                            onChange={(e) => onUpdate({ modelPath: e.target.value })}
                            style={inputStyle}
                        >
                            {AVAILABLE_MODELS.map(m => (
                                <option key={m.path} value={m.path}>{m.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Voice Configuration */}
                    <div style={{ marginBottom: '15px' }}>
                        <label style={labelStyle}>Voice Configuration</label>
                        <div style={{ marginBottom: '8px' }}>
                            <select
                                value={char.voiceConfig?.service || 'edge-tts'}
                                onChange={(e) => onVoiceConfigChange('service', e.target.value)}
                                style={{ ...inputStyle, marginBottom: '5px' }}
                            >
                                <option value="edge-tts">Edge TTS (Cloud)</option>
                                <option value="gpt-sovits">GPT-SoVITS (Local)</option>
                            </select>
                        </div>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <select
                                value={char.voiceConfig?.voiceId}
                                onChange={(e) => onVoiceConfigChange('voiceId', e.target.value)}
                                style={{ ...inputStyle, flex: 2 }}
                            >
                                {char.voiceConfig?.service === 'gpt-sovits' ? (
                                    gptVoices.length > 0 
                                        ? gptVoices.map(v => <option key={v.name} value={v.name}>{v.name}</option>)
                                        : <option disabled>No local voices</option>
                                ) : (
                                    edgeVoices.length > 0 
                                        ? edgeVoices.map(v => (
                                            <option key={v.name} value={v.name}>
                                                {v.name.replace(/zh-CN-|en-US-|Neural/g, '')} ({v.gender})
                                            </option>
                                        ))
                                        : <option>Loading voices...</option>
                                )}
                            </select>
                            {char.voiceConfig?.service !== 'gpt-sovits' && (
                                <input
                                    value={char.voiceConfig?.rate || '+0%'}
                                    onChange={(e) => onVoiceConfigChange('rate', e.target.value)}
                                    style={{ ...inputStyle, flex: 1 }}
                                    placeholder="+0%"
                                    title="Speed"
                                />
                            )}
                        </div>
                    </div>

                    {/* Heartbeat Settings */}
                    <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px dashed #eee' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563', marginBottom: '10px' }}>
                            💗 Interaction Settings
                        </h4>
                        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <input
                                    type="checkbox"
                                    checked={char.heartbeatEnabled !== false}
                                    onChange={(e) => onUpdate({ heartbeatEnabled: e.target.checked })}
                                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                                />
                                <span style={{ fontSize: '13px' }}>Custom Silence Duration</span>
                            </div>
                            {(char.heartbeatEnabled !== false) && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <label style={{ fontSize: '13px', color: '#6b7280' }}>Silence (mins):</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="120"
                                        value={char.proactiveThresholdMinutes || 15}
                                        onChange={(e) => onUpdate({ proactiveThresholdMinutes: Number(e.target.value) })}
                                        style={{ ...inputStyle, width: '60px', padding: '4px 8px' }}
                                    />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '10px', borderTop: '1px solid #f3f4f6' }}>
                        <button
                            onClick={onDelete}
                            style={{ ...buttonStyle, backgroundColor: '#fee2e2', color: '#b91c1c', padding: '6px 12px', fontSize: '12px' }}
                        >
                            Delete
                        </button>
                        {!isActive && (
                            <button
                                onClick={onActivate}
                                style={{ ...buttonStyle, backgroundColor: '#e0e7ff', color: '#4338ca', padding: '6px 12px', fontSize: '12px' }}
                            >
                                Set as Active
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CharactersTab;
