import React, { useState, useEffect } from 'react';
import { useLlmManager, LlmProvider } from '../../hooks/useLlmManager';
import { inputStyle, labelStyle, buttonStyle } from './styles';

export const ProvidersTab: React.FC = () => {
    const { llmProviders, addProvider, updateProvider, refreshData } = useLlmManager();
    
    // Local State
    const [showAdd, setShowAdd] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ base_url: '', api_key: '', models: '' });
    
    const [newProv, setNewProv] = useState({ 
        id: '', 
        type: 'openai_compatible', 
        base_url: '', 
        api_key: '', 
        models: '' 
    });

    useEffect(() => {
        refreshData();
    }, [refreshData]);

    const handleSaveNew = async () => {
        if (!newProv.id) return;
        const success = await addProvider({
            ...newProv,
            models: newProv.models.split(',').map(s => s.trim()).filter(Boolean)
        });
        if (success) {
            setNewProv({ id: '', type: 'openai_compatible', base_url: '', api_key: '', models: '' });
            setShowAdd(false);
        } else {
            alert("Failed to add provider");
        }
    };

    const handleStartEdit = (prov: LlmProvider) => {
        setEditingId(prov.id);
        setEditForm({
            base_url: prov.base_url,
            api_key: prov.api_key || '',
            models: Array.isArray(prov.models) ? prov.models.join(', ') : prov.models
        });
    };

    const handleUpdate = async () => {
        if (!editingId) return;
        const success = await updateProvider(editingId, {
            base_url: editForm.base_url,
            api_key: editForm.api_key,
            models: editForm.models.split(',').map(s => s.trim()).filter(Boolean)
        });
        if (success) {
            setEditingId(null);
        } else {
            alert("Failed to update provider");
        }
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <h3 style={{ margin: 0, color: '#374151', fontSize: '18px', fontWeight: 600 }}>LLM Providers</h3>
                <button 
                    onClick={() => setShowAdd(true)}
                    style={{ ...buttonStyle, background: 'linear-gradient(135deg, #22c55e, #16a34a)', color: 'white' }}
                >
                    + Add Provider
                </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Add Form */}
                {showAdd && (
                    <div style={{ background: '#f0fdf4', border: '1px solid #22c55e', borderRadius: '8px', padding: '15px' }}>
                        <h4 style={{ margin: '0 0 10px 0', color: '#15803d', fontSize: '14px' }}>New Provider</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                            <div>
                                <label style={labelStyle}>ID (e.g. 'deepseek')</label>
                                <input style={inputStyle} value={newProv.id} onChange={e => setNewProv({...newProv, id: e.target.value})} placeholder="unique_id" />
                            </div>
                            <div>
                                <label style={labelStyle}>Type</label>
                                <select style={inputStyle} value={newProv.type} onChange={e => setNewProv({...newProv, type: e.target.value})}>
                                    <option value="openai_compatible">OpenAI Compatible</option>
                                    <option value="pollinations">Pollinations (Free)</option>
                                    <option value="deepseek">DeepSeek (Native)</option>
                                </select>
                            </div>
                        </div>
                         <div style={{ marginBottom: '10px' }}>
                            <label style={labelStyle}>Base URL</label>
                            <input style={inputStyle} value={newProv.base_url} onChange={e => setNewProv({...newProv, base_url: e.target.value})} placeholder="https://api.openai.com/v1" />
                        </div>
                        <div style={{ marginBottom: '10px' }}>
                            <label style={labelStyle}>API Key</label>
                            <input style={inputStyle} type="password" value={newProv.api_key} onChange={e => setNewProv({...newProv, api_key: e.target.value})} placeholder="sk-..." />
                        </div>
                        <div style={{ marginBottom: '10px' }}>
                             <label style={labelStyle}>Models (comma separated)</label>
                             <input style={inputStyle} value={newProv.models} onChange={e => setNewProv({...newProv, models: e.target.value})} placeholder="gpt-4, llama3..." />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                            <button onClick={() => setShowAdd(false)} style={{ ...buttonStyle, background: '#e5e7eb', color: '#374151' }}>Cancel</button>
                            <button onClick={handleSaveNew} style={{ ...buttonStyle, background: '#22c55e', color: 'white' }}>Create Provider</button>
                        </div>
                    </div>
                )}

                {/* List */}
                {llmProviders.map(prov => {
                    const isEditing = editingId === prov.id;

                    return (
                        <div key={prov.id} style={{ background: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isEditing ? '15px' : '0' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: prov.enabled ? '#22c55e' : '#9ca3af' }}></div>
                                    <span style={{ fontWeight: 600, color: '#374151' }}>{prov.id}</span>
                                    <span style={{ fontSize: '11px', color: '#6b7280', background: '#f3f4f6', padding: '2px 6px', borderRadius: '4px' }}>{prov.type}</span>
                                </div>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    {!isEditing ? (
                                        <button 
                                            onClick={() => handleStartEdit(prov)} 
                                            style={{ ...buttonStyle, padding: '4px 8px', background: '#f3f4f6', color: '#4b5563', fontSize: '12px' }}
                                        >
                                            Edit
                                        </button>
                                    ) : (
                                        <>
                                            <button onClick={() => setEditingId(null)} style={{ ...buttonStyle, padding: '4px 8px', background: '#f3f4f6', color: '#4b5563', fontSize: '12px' }}>Cancel</button>
                                            <button onClick={handleUpdate} style={{ ...buttonStyle, padding: '4px 8px', background: '#4f46e5', color: 'white', fontSize: '12px' }}>Save</button>
                                        </>
                                    )}
                                </div>
                            </div>

                            {isEditing && (
                                <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px', padding: '10px', background: '#f9fafb', borderRadius: '6px' }}>
                                    <div>
                                        <label style={labelStyle}>Base URL</label>
                                        <input style={inputStyle} value={editForm.base_url} onChange={e => setEditForm({...editForm, base_url: e.target.value})} />
                                    </div>
                                    <div>
                                        <label style={labelStyle}>API Key</label>
                                        <input style={inputStyle} type="password" value={editForm.api_key} onChange={e => setEditForm({...editForm, api_key: e.target.value})} />
                                    </div>
                                    <div>
                                        <label style={labelStyle}>Models</label>
                                        <input 
                                            style={inputStyle} 
                                            value={editForm.models} 
                                            onChange={e => setEditForm({...editForm, models: e.target.value})}
                                        />
                                    </div>
                                </div>
                            )}
                            {!isEditing && (
                                <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px', marginLeft: '18px' }}>
                                   {prov.base_url}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
