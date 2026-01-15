
import React, { useState } from "react";
import { useLlmManager, LlmProvider, LlmRoute } from "../../hooks/useLlmManager";
import { Loader2, Plus, Trash2, Edit2, Check, X } from "lucide-react";

const ProviderFormRow: React.FC<{ 
    provider?: Partial<LlmProvider>, 
    isNew?: boolean,
    onSave: (p: any) => void,
    onCancel: () => void 
}> = ({ provider, isNew, onSave, onCancel }) => {
    const [data, setData] = useState({
        id: provider?.id || "",
        type: provider?.type || "openai",
        base_url: provider?.base_url || "",
        api_key: provider?.api_key || "",
        models: provider?.models?.join(",") || ""
    });

    const handleSave = () => {
        onSave({ ...data, models: data.models.split(",").map(s => s.trim()) });
    };

    return (
        <tr className="bg-cyan-500/10 border-b border-cyan-500/20">
            <td className="p-2 align-top">
                <input 
                    className="w-full bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-cyan-100 mb-1"
                    placeholder="ID (e.g. deepseek)"
                    value={data.id}
                    onChange={e => setData({...data, id: e.target.value})}
                    disabled={!isNew} // ID immutable if editing
                />
                <select 
                    className="w-full bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-cyan-100"
                    value={data.type}
                    onChange={e => setData({...data, type: e.target.value})}
                >
                    <option value="openai">OpenAI Compatible</option>
                    <option value="deepseek">DeepSeek (Native)</option>
                    <option value="pollinations">Pollinations (Free)</option>
                </select>
            </td>
            <td className="p-2 align-top text-xs">
                <input 
                    className="w-full bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-cyan-100 mb-1"
                    placeholder="Base URL (e.g. https://api...)"
                    value={data.base_url}
                    onChange={e => setData({...data, base_url: e.target.value})}
                />
                <input 
                    type="password"
                    className="w-full bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-cyan-100"
                    placeholder="API Key (or ${ENV_VAR})"
                    value={data.api_key}
                    onChange={e => setData({...data, api_key: e.target.value})}
                />
            </td>
            <td className="p-2 align-top">
                <textarea 
                    className="w-full h-16 bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-cyan-100 font-mono"
                    placeholder="Models (comma separated)"
                    value={data.models}
                    onChange={e => setData({...data, models: e.target.value})}
                />
            </td>
            <td className="p-2 align-middle text-center">
                <div className="flex flex-col gap-2 justify-center">
                    <button onClick={handleSave} className="p-1 hover:bg-green-500/20 rounded text-green-400">
                        <Check size={14} />
                    </button>
                    <button onClick={onCancel} className="p-1 hover:bg-red-500/20 rounded text-red-400">
                        <X size={14} />
                    </button>
                </div>
            </td>
        </tr>
    );
};

export const LLMEngineConfig: React.FC = () => {
    const { 
        llmProviders, llmRoutes, 
        refreshData, addProvider, updateProvider, updateRoute, isLoading 
    } = useLlmManager();
    
    const [editingProvider, setEditingProvider] = useState<string | null>(null);
    const [isAdding, setIsAdding] = useState(false);

    React.useEffect(() => {
        refreshData();
    }, [refreshData]);

    // Derived: Available Models Map
    const getModelsForProvider = (pid: string) => {
        const p = llmProviders.find(x => x.id === pid);
        return p ? p.models : [];
    };

    return (
        <div className="flex flex-col gap-6 h-full overflow-y-auto pr-2 custom-scrollbar">
            
            {/* === PROVIDERS SECTION === */}
            <section>
                <div className="flex items-center justify-between mb-3 border-b border-white/10 pb-2">
                    <h3 className="text-sm font-semibold text-cyan-400">LLM Providers</h3>
                    <button 
                        onClick={() => setIsAdding(true)}
                        className="text-xs flex items-center gap-1 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 px-2 py-1 rounded transition-colors"
                    >
                        <Plus size={12} /> Add Provider
                    </button>
                </div>

                <div className="bg-black/20 rounded border border-white/5 overflow-hidden">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-white/5 text-xs text-gray-400 uppercase">
                            <tr>
                                <th className="p-2 font-medium w-1/4">Provider</th>
                                <th className="p-2 font-medium w-1/3">Endpoint / Key</th>
                                <th className="p-2 font-medium">Models</th>
                                <th className="p-2 font-medium w-16 text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-sm text-gray-300">
                            {isAdding && (
                                <ProviderFormRow 
                                    isNew 
                                    onSave={async (data) => {
                                        await addProvider(data);
                                        setIsAdding(false);
                                    }} 
                                    onCancel={() => setIsAdding(false)} 
                                />
                            )}
                            
                            {llmProviders.map(p => (
                                editingProvider === p.id ? (
                                    <ProviderFormRow 
                                        key={p.id} 
                                        provider={p} 
                                        onSave={async (data) => {
                                            await updateProvider(p.id, data);
                                            setEditingProvider(null);
                                        }}
                                        onCancel={() => setEditingProvider(null)} 
                                    />
                                ) : (
                                    <tr key={p.id} className="hover:bg-white/5 transition-colors">
                                        <td className="p-2">
                                            <div className="font-medium text-cyan-200">{p.id}</div>
                                            <div className="text-[10px] text-gray-500">{p.type}</div>
                                        </td>
                                        <td className="p-2 font-mono text-xs text-gray-500 break-all">
                                            {p.base_url || "(Default)"}
                                            <div className="text-[10px] opacity-50">
                                                {p.api_key ? (p.api_key.includes("${") ? p.api_key : "************") : "No Key"}
                                            </div>
                                        </td>
                                        <td className="p-2 text-xs text-gray-400">
                                            {p.models.slice(0, 3).join(", ")}
                                            {p.models.length > 3 && ` +${p.models.length - 3}`}
                                        </td>
                                        <td className="p-2 text-center">
                                            <button 
                                                onClick={() => setEditingProvider(p.id)}
                                                className="p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white"
                                            >
                                                <Edit2 size={12} />
                                            </button>
                                        </td>
                                    </tr>
                                )
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* === ROUTES SECTION === */}
            <section>
                 <div className="flex items-center justify-between mb-3 border-b border-white/10 pb-2">
                    <h3 className="text-sm font-semibold text-purple-400">Feature Routing</h3>
                    {isLoading && <Loader2 size={14} className="animate-spin text-purple-500" />}
                </div>

                <div className="bg-black/20 rounded border border-white/5 overflow-hidden">
                    {llmRoutes.map(route => {
                        const models = getModelsForProvider(route.provider_id);
                        return (
                            <div key={route.feature} className="p-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${route.feature === 'chat' ? 'bg-green-500' : 'bg-purple-500'}`} />
                                        <span className="text-sm font-medium text-gray-200 capitalize">{route.feature}</span>
                                    </div>
                                    <div className="flex gap-2">
                                        {/* Provider Selector */}
                                        <select 
                                            className="bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-cyan-100 focus:outline-none focus:border-cyan-500/50"
                                            value={route.provider_id}
                                            onChange={(e) => updateRoute(route.feature, { provider_id: e.target.value })}
                                        >
                                            {llmProviders.map(p => (
                                                <option key={p.id} value={p.id}>{p.id}</option>
                                            ))}
                                        </select>
                                        {/* Model Selector */}
                                        <select 
                                            className="bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-purple-100 focus:outline-none focus:border-purple-500/50 w-32"
                                            value={route.model}
                                            onChange={(e) => updateRoute(route.feature, { model: e.target.value })}
                                        >
                                            {models.map(m => (
                                                <option key={m} value={m}>{m}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                
                                {/* Sliders */}
                                <div className="grid grid-cols-2 gap-4 pl-4 mt-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] text-gray-500 w-16">Temperature</span>
                                        <input 
                                            type="range" min="0" max="2" step="0.1" 
                                            className="flex-1 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer"
                                            value={route.temperature ?? 0.7}
                                            onMouseUp={(e) => updateRoute(route.feature, { temperature: parseFloat((e.target as any).value) })}
                                            onChange={() => {}} // Supress warnings, update on MouseUp
                                        />
                                        <span className="text-[10px] text-gray-400 w-6 text-right">{route.temperature}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] text-gray-500 w-16">Topic Fresh</span>
                                        <input 
                                            type="range" min="-2" max="2" step="0.1" 
                                            className="flex-1 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer"
                                            value={route.presence_penalty ?? 0}
                                            onMouseUp={(e) => updateRoute(route.feature, { presence_penalty: parseFloat((e.target as any).value) })}
                                            onChange={() => {}}
                                        />
                                        <span className="text-[10px] text-gray-400 w-6 text-right">{route.presence_penalty}</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </section>
        </div>
    );
};
