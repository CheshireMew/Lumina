import React, { useState, useEffect } from 'react';
import GalgameSelect from './GalgameSelect';
import GalgameToggle from './GalgameToggle';

interface PluginConfigModalProps {
    plugin: any;
    onClose: () => void;
    onSave: (key: string, value: any) => Promise<void>;
    existingGroups: string[]; // [NEW] For dropdown suggestions
}

import { Trash2, FolderOpen, Mic, ToggleLeft, ToggleRight } from 'lucide-react';

const VoiceprintConfigPanel = ({ threshold, onThresholdChange }: { threshold: number, onThresholdChange: (val: number) => void }) => {
    const [profiles, setProfiles] = useState<any[]>([]);
    const [name, setName] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState("");
    const [localThreshold, setLocalThreshold] = useState(threshold);

    // Sync external threshold
    useEffect(() => {
        setLocalThreshold(threshold);
    }, [threshold]);

    const categories = ["Skill", "STT", "TTS", "System", "Game", "Other"];

    const fetchProfiles = async () => {
        try {
            const res = await fetch("http://localhost:8010/plugins/voiceprint/list");
            const data = await res.json();
            if (data.profiles) setProfiles(data.profiles);
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchProfiles();
    }, []);

    const handleRegister = async () => {
        if (!file || !name) return;
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append("file", file);
            
            const res = await fetch(`http://localhost:8010/plugins/voiceprint/upload?name=${encodeURIComponent(name)}`, {
                method: "POST",
                body: formData
            });
            
            if (res.ok) {
                setMsg("✅ Registered successfully!");
                setFile(null);
                setName("");
                fetchProfiles();
            } else {
                setMsg("❌ Registration failed.");
            }
        } catch (e) {
            setMsg("❌ Error: " + e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (pName: string) => {
        if (!confirm(`Delete voiceprint '${pName}'?`)) return;
        try {
            await fetch(`http://localhost:8010/plugins/voiceprint/${pName}`, { method: "DELETE" });
            fetchProfiles();
        } catch (e) {
            console.error(e);
        }
    };

    const handleToggle = async (pName: string, currentEnabled: boolean) => {
        try {
            const res = await fetch(`http://localhost:8010/plugins/voiceprint/toggle/${pName}?enabled=${!currentEnabled}`, { method: "POST" });
            if (res.ok) {
                fetchProfiles();
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = parseFloat(e.target.value);
        setLocalThreshold(val);
    };

    const handleSliderCommit = () => {
        onThresholdChange(localThreshold);
    };

    return (
        <div style={{marginTop: 10}}>
             <div style={{background: 'rgba(255,255,255,0.05)', padding: '15px', borderRadius: '8px', marginBottom: '20px'}}>
                <label style={{display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontWeight: 'bold', color: '#ccc'}}>
                    <span>Similarity Threshold</span>
                    <span style={{color: '#fff'}}>{localThreshold}</span>
                </label>
                <input 
                    type="range" 
                    min="0.1" 
                    max="0.9" 
                    step="0.05" 
                    value={localThreshold} 
                    onChange={handleSliderChange}
                    onMouseUp={handleSliderCommit}
                    onTouchEnd={handleSliderCommit}
                    style={{width: '100%', cursor: 'pointer', accentColor: '#7928ca'}}
                />
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75em', color: '#888', marginTop: '5px'}}>
                    <span>Low (Permissive)</span>
                    <span>High (Strict)</span>
                </div>
            </div>

            <h4 style={{margin: "0 0 10px 0", color: "#ddd", display:'flex', alignItems:'center', gap:8}}>
                <Mic size={16} /> Active Voiceprints
            </h4>
            <div style={{maxHeight: 150, overflowY: "auto", background: "rgba(0,0,0,0.2)", borderRadius: 6, padding: 5, marginBottom: 15}}>
                {profiles.length === 0 ? <div style={{padding:10, color:"#888", textAlign:"center", fontSize: "0.9em"}}>No voiceprints yet</div> : 
                profiles.map(p => (
                    <div key={p.name} style={{display:"flex", justifyContent:"space-between", alignItems:"center", padding: "6px 10px", borderBottom: "1px solid rgba(255,255,255,0.05)"}}>
                        <div style={{opacity: p.enabled ? 1 : 0.5, transition: 'opacity 0.2s'}}>
                            <span style={{fontWeight:"bold", color:"#fff", marginRight: 8}}>{p.name}</span>
                            <span style={{fontSize:"0.75em", color:"#aaa"}}>{new Date(p.created_at).toLocaleDateString()}</span>
                        </div>
                        <div style={{display:'flex', gap: 10, alignItems:'center'}}>
                            <button 
                                onClick={() => handleToggle(p.name, p.enabled)} 
                                title={p.enabled ? "Disable" : "Enable"}
                                style={{
                                    background:"transparent", 
                                    border:"none", 
                                    color: p.enabled ? "#4caf50" : "#666", 
                                    cursor:"pointer", 
                                    display:'flex', 
                                    alignItems:'center'
                                }}
                            >
                                {p.enabled ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                            </button>
                            <button 
                                onClick={() => handleDelete(p.name)} 
                                title="Delete"
                                style={{background:"transparent", border:"none", color:"#ff4444", cursor:"pointer", display:'flex'}}
                            >
                                {loading && name === p.name ? "..." : <Trash2 size={16} />}
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <h4 style={{margin: "0 0 10px 0", color: "#ddd", fontSize:'0.9em'}}>Register New Voice</h4>
            {/* ... Rest of Registration UI ... */}
            <div style={{display:"flex", gap: 10, flexDirection: "column"}}>
                <input 
                    type="text" 
                    placeholder="User Name (e.g. Master)" 
                    className="galgame-input"
                    value={name}
                    onChange={e => setName(e.target.value)}
                />
                <div style={{display:"flex", gap: 10}}>
                    <label style={{flex:1, cursor:"pointer", background:"rgba(255,255,255,0.1)", padding: "8px", borderRadius: 6, textAlign:"center", border: "1px dashed #666", display:'flex', alignItems:'center', justifyContent:'center', gap:6, fontSize:'0.9em', color:'#ccc'}}>
                        <FolderOpen size={14} />
                        {file ? file.name : "Select WAV File..."}
                        <input type="file" accept=".wav" style={{display:"none"}} onChange={e => e.target.files && setFile(e.target.files[0])} />
                    </label>
                    <button 
                        className="galgame-btn primary" 
                        disabled={!file || !name || loading}
                        onClick={handleRegister}
                        style={{flex:1, opacity: (!file||!name) ? 0.5 : 1}}
                    >
                        {loading ? "Processing..." : "Register"}
                    </button>
                </div>
                {msg && <div style={{marginTop: 5, color: msg.startsWith("✅") ? "#4caf50" : "#ff4444", fontSize: "0.9em"}}>{msg}</div>}
            </div>
        </div>
    );
};

const PluginConfigModal: React.FC<PluginConfigModalProps> = ({ plugin, onClose, onSave, existingGroups }) => {
    console.log("[PluginConfigModal] Existing groups:", existingGroups, "Current Plugin Group:", plugin.group_id);
    const [values, setValues] = useState<{[key: string]: any}>({});
    const [saving, setSaving] = useState(false);
    
    // ⚡ LLM State
    const [llmRoutes, setLlmRoutes] = useState<any[]>([]);
    const [llmProviders, setLlmProviders] = useState<any[]>([]);
    const [expandedRoutes, setExpandedRoutes] = useState<Set<string>>(new Set());

    useEffect(() => {
        const initVal: any = {};
        if (plugin?.config_schema) {
            initVal[plugin.config_schema.key] = plugin.current_value || "";
        }
        initVal['__group_id'] = plugin?.group_id || "";
        initVal['__category'] = plugin?.category || "";
        initVal['__group_behavior'] = plugin?.group_exclusive === false ? 'independent' : 'exclusive';

        setValues(initVal);

        // ⚡ Fetch LLM Data if plugin has routes
        if (plugin?.llm_routes?.length > 0) {
            fetchLlmData();
        }
    }, [plugin]);

    const fetchLlmData = async () => {
        try {
            // Hardcoded base URL or import API_CONFIG (assuming localhost:8010 based on existing code)
            const BASE_URL = "http://localhost:8010"; 
            const routesRes = await fetch(`${BASE_URL}/llm-mgmt/routes`);
            const provRes = await fetch(`${BASE_URL}/llm-mgmt/providers`);
            
            if (routesRes.ok && provRes.ok) {
                const rData = await routesRes.json();
                const pData = await provRes.json();
                setLlmRoutes(rData.routes || []);
                setLlmProviders(pData.providers || []);
            }
        } catch (e) {
            console.error("Failed to fetch LLM data", e);
        }
    };

    const handleRouteUpdate = async (feature: string, providerId: string, model: string, temp?: number, topP?: number, presPenalty?: number, freqPenalty?: number) => {
        try {
             // Optimistic Update
            setLlmRoutes(prev => prev.map(r => 
                r.feature === feature 
                ? { ...r, provider_id: providerId, model, temperature: temp, top_p: topP, presence_penalty: presPenalty, frequency_penalty: freqPenalty } 
                : r
            ));

            await fetch(`http://localhost:8010/llm-mgmt/routes/${feature}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    provider_id: providerId, 
                    model: model, 
                    temperature: temp,
                    top_p: topP,
                    presence_penalty: presPenalty,
                    frequency_penalty: freqPenalty
                })
            });
        } catch (e) {
            console.error("Failed to update route", e);
            fetchLlmData(); // Revert on fail
        }
    };

    if (!plugin) return null;

    const schema = plugin.config_schema;
    const currentVal = schema ? (values[schema.key] !== undefined ? values[schema.key] : (plugin.current_value ?? "")) : "";

    const handleSave = async () => {
        setSaving(true);
        try {
            if (schema) {
                if (schema.fields) {
                    for (const field of schema.fields) {
                        const val = values[field.key] !== undefined ? values[field.key] : (plugin.config?.[field.key] ?? field.default ?? "");
                        await onSave(field.key, val);
                    }
                } else {
                    await onSave(schema.key, currentVal);
                }
            }
            onClose();
        } catch (e) {
            console.error(e);
        } finally {
            setSaving(false);
        }
    };

    // Filter routes relevant to this plugin
    const pluginRoutes = llmRoutes.filter(r => plugin.llm_routes?.includes(r.feature));
    const hasLLM = pluginRoutes.length > 0;

    return (
        <div className="plugin-modal-overlay">
            <div className="plugin-config-modal glass-panel">
                <div className="modal-header">
                    <h3>⚙️ Configure {plugin.name}</h3>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>
                
                <div className="modal-body">
                    <p className="config-desc">{plugin.description}</p>
                    
                    {/* 🧠 LLM Configuration Section */}
                    {hasLLM && (
                        <div style={{ marginBottom: '25px', background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                            <h4 style={{ margin: '0 0 12px 0', color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95em' }}>
                                🧠 Neural Configuration
                            </h4>
                            {pluginRoutes.map(route => {
                                const isExpanded = expandedRoutes.has(route.feature);
                                const currentProv = llmProviders.find(p => p.id === route.provider_id);
                                
                                const toggleExpand = () => {
                                    const next = new Set(expandedRoutes);
                                    if (next.has(route.feature)) next.delete(route.feature);
                                    else next.add(route.feature);
                                    setExpandedRoutes(next);
                                };

                                const update = (changes: any) => {
                                    handleRouteUpdate(
                                        route.feature, 
                                        changes.provider_id ?? route.provider_id, 
                                        changes.model ?? route.model,
                                        changes.temperature ?? route.temperature ?? 0.7,
                                        changes.top_p ?? route.top_p ?? 1.0,
                                        changes.presence_penalty ?? route.presence_penalty ?? 0.0,
                                        changes.frequency_penalty ?? route.frequency_penalty ?? 0.0
                                    );
                                };

                                return (
                                    <div key={route.feature} style={{ marginBottom: '10px', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', marginBottom: isExpanded ? '10px' : '0' }}>
                                            <div style={{ flex: 1, fontWeight: 600, color: '#e0e0e0', textTransform: 'capitalize' }}>
                                                {route.feature}
                                            </div>
                                            
                                            {/* Compact Provider/Model Selects */}
                                            <select 
                                                className="galgame-input"
                                                style={{ width: '100px', padding: '4px', height: '28px', fontSize: '12px' }}
                                                value={route.provider_id} 
                                                onChange={(e) => update({ provider_id: e.target.value })}
                                            >
                                                {llmProviders.map(p => <option key={p.id} value={p.id}>{p.id}</option>)}
                                            </select>
                                            <select 
                                                className="galgame-input"
                                                style={{ width: '140px', padding: '4px', height: '28px', fontSize: '12px' }}
                                                value={route.model}
                                                onChange={(e) => update({ model: e.target.value })}
                                            >
                                                {currentProv?.models?.map((m: string) => <option key={m} value={m}>{m}</option>)}
                                                {!currentProv?.models?.includes(route.model) && <option value={route.model}>{route.model}</option>}
                                            </select>
                                            
                                            <button 
                                                onClick={toggleExpand}
                                                style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#a78bfa', padding: '4px' }}
                                                title="Advanced Params"
                                            >
                                                ⚙️
                                            </button>
                                        </div>

                                        {/* Expanded Sliders */}
                                        {isExpanded && (
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                                                {[
                                                    { label: "Temp", key: "temperature", min: 0, max: 2, step: 0.1, val: route.temperature },
                                                    { label: "Top P", key: "top_p", min: 0, max: 1, step: 0.05, val: route.top_p },
                                                    { label: "Pres. Penalty", key: "presence_penalty", min: 0, max: 2, step: 0.1, val: route.presence_penalty },
                                                    { label: "Freq. Penalty", key: "frequency_penalty", min: 0, max: 2, step: 0.1, val: route.frequency_penalty },
                                                ].map(param => (
                                                     <div key={param.key}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                                            <label style={{ fontSize: '11px', color: '#aaa' }}>{param.label}</label>
                                                            <span style={{ fontSize: '11px', color: '#a78bfa' }}>{param.val ?? 0}</span>
                                                        </div>
                                                        <input 
                                                            type="range" 
                                                            min={param.min} max={param.max} step={param.step} 
                                                            value={param.val ?? (param.key === 'top_p' ? 1.0 : (param.key === 'temperature' ? 0.7 : 0.0))} 
                                                            onChange={(e) => update({ [param.key]: parseFloat(e.target.value) })}
                                                            style={{ width: '100%', accentColor: '#a78bfa', height: '4px', cursor: 'pointer' }} 
                                                        />
                                                     </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}


                    {plugin.id === 'system.voiceprint' ? (
                        <VoiceprintConfigPanel 
                            threshold={Number(currentVal) || 0.6}
                            onThresholdChange={(v) => {
                                if (plugin.config_schema?.key) {
                                    setValues(prev => ({ ...prev, [plugin.config_schema.key]: v }));
                                }
                            }}
                        />
                    ) : ( 
                        <>
                        {/* Standard Config Form */}
                        {schema ? (
                            <>
                            {schema.fields ? (
                                /* Multi-field Schema (New V2) */
                                schema.fields.map((field: any) => {
                                    const fieldVal = values[field.key] !== undefined ? values[field.key] : (plugin.config?.[field.key] ?? field.default ?? "");
                                    return (
                                        <div key={field.key} className="form-group">
                                            <label>{field.label}</label>
                                            {field.type === 'select' ? (
                                                 <GalgameSelect
                                                    value={fieldVal}
                                                    options={field.options}
                                                    onChange={(val) => setValues(prev => ({ ...prev, [field.key]: val }))}
                                                />
                                            ) : (
                                                <input 
                                                    type={field.type === 'number' ? 'number' : 'text'}
                                                    className="galgame-input"
                                                    value={fieldVal}
                                                    onChange={(e) => setValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                                                />
                                            )}
                                        </div>
                                    );
                                })
                            ) : (
                                /* Single-field Schema (Legacy V1) */
                                <div className="form-group">
                                    <label>{schema.label}</label>
                                    
                                    {schema.type === 'select' && schema.options ? (
                                        <GalgameSelect
                                            value={currentVal}
                                            options={schema.options}
                                            onChange={(val) => setValues({ ...values, [schema.key]: val })}
                                        />
                                    ) : (
                                        <input 
                                            type={schema.type === 'number' ? 'number' : 'text'}
                                            className="galgame-input"
                                            value={currentVal}
                                            onChange={(e) => setValues({ ...values, [schema.key]: e.target.value })}
                                            step={schema.type === 'number' ? '0.1' : undefined}
                                        />
                                    )}
                                </div>
                            )}
                            </>
                        ) : (
                            !hasLLM && ( // Only show "No config" if also no LLM config
                                <div className="no-config-message" style={{marginBottom: '20px', fontStyle: 'italic', color: '#888'}}>
                                    No standard configuration available for this plugin.
                                </div>
                            )
                        )}
                        </>

                    )}


                </div>

                <div className="modal-footer">
                    <button className="galgame-btn secondary" onClick={onClose}>Cancel</button>
                    <button className="galgame-btn primary" onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
            
            <style>{`
                .plugin-config-modal {
                    width: 500px;
                    background: rgba(20, 20, 25, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 20px;
                    color: white;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                    max-height: 85vh;
                    display: flex;
                    flex-direction: column;
                }
                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    padding-bottom: 10px;
                    flex-shrink: 0;
                }
                .modal-body {
                    flex: 1;
                    overflow-y: auto;
                    overflow-x: hidden;
                    padding-right: 5px; /* Spacing for scrollbar */
                }
                .config-desc {
                    color: #aaa;
                    font-size: 0.9em;
                    margin-bottom: 20px;
                    line-height: 1.4;
                }
                .form-group {
                    margin-bottom: 25px;
                }
                .form-group label {
                    display: block;
                    margin-bottom: 8px;
                    font-weight: 500;
                    color: #e0e0e0;
                }
                .galgame-input {
                    width: 100%;
                    padding: 8px 12px;
                    background: rgba(0,0,0,0.3);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 6px;
                    color: white;
                    box-sizing: border-box; /* Fix horizontal overflow */
                }
                .modal-footer {
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                    margin-top: 20px;
                    padding-top: 15px;
                    border-top: 1px solid rgba(255,255,255,0.05); /* Visual separation */
                    flex-shrink: 0;
                }
                .galgame-btn {
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    border: none;
                    font-weight: 500;
                    transition: all 0.2s;
                }
                .galgame-btn.primary {
                    background: linear-gradient(135deg, #ff0080, #7928ca);
                    color: white;
                }
                .galgame-btn.secondary {
                    background: rgba(255,255,255,0.1);
                    color: white;
                }
                .galgame-btn:hover {
                    opacity: 0.9;
                    transform: translateY(-1px);
                }
                /* Custom Scrollbar */
                .modal-body::-webkit-scrollbar {
                    width: 6px;
                }
                .modal-body::-webkit-scrollbar-thumb {
                    background: rgba(255,255,255,0.1);
                    border-radius: 3px;
                }
                .modal-body::-webkit-scrollbar-thumb:hover {
                    background: rgba(255,255,255,0.2);
                }
            `}</style>
        </div>
    );
};

export default PluginConfigModal;
