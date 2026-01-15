
import React, { useState, useEffect } from "react";
import { PluginStatus, PluginConfigSchema } from "../../hooks/usePluginManager";
import { Loader2, Save } from "lucide-react";

interface PluginConfigRendererProps {
    plugin: PluginStatus;
    onUpdate: (key: string, value: any) => Promise<boolean>;
}

export const PluginConfigRenderer: React.FC<PluginConfigRendererProps> = ({ plugin, onUpdate }) => {
    const [localConfig, setLocalConfig] = useState<any>(plugin.current_value ?? plugin.config ?? {});
    const [isSaving, setIsSaving] = useState(false);

    // Sync when plugin changes
    useEffect(() => {
        setLocalConfig(plugin.current_value ?? plugin.config ?? {});
    }, [plugin]);

    const handleSave = async (key: string, val: any) => {
        setIsSaving(true);
        await onUpdate(key, val);
        setIsSaving(false);
    };

    const renderField = (schema: PluginConfigSchema, currentValue: any, prefix = "") => {
        const fieldKey = schema.key;
        const label = schema.label || fieldKey;
        const val = currentValue;

        if (schema.fields) {
            // Nested Schema (e.g. TTS)
            return (
                <div key={fieldKey} className="ml-4 mt-2 border-l-2 border-white/10 pl-4">
                    <h4 className="text-xs font-semibold text-gray-400 mb-2">{label}</h4>
                    {schema.fields.map(subField => renderField(subField, val?.[subField.key], fieldKey))}
                </div>
            );
        }

        // Single Field
        // Determine Input Type
        let inputEl = null;

        if (schema.type === "boolean" || typeof schema.default === "boolean") {
            inputEl = (
                 <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                        type="checkbox" 
                        className="sr-only peer"
                        checked={!!val}
                        onChange={(e) => handleSave(fieldKey, e.target.checked)}
                        disabled={isSaving}
                    />
                    <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
                </label>
            );
        } else if (schema.type === "select" || schema.options) {
             inputEl = (
                <select 
                    className="flex-1 bg-black/40 border border-white/10 rounded px-2 py-1 text-sm text-cyan-100 focus:outline-none focus:border-cyan-500/50"
                    value={val}
                    onChange={(e) => handleSave(fieldKey, e.target.value)}
                    disabled={isSaving}
                >
                    {schema.options?.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
             );
        } else if (schema.type === "number") {
             inputEl = (
                <input 
                    type="number"
                    className="flex-1 bg-black/40 border border-white/10 rounded px-2 py-1 text-sm text-cyan-100 focus:outline-none focus:border-cyan-500/50"
                    value={val || 0}
                    onChange={(e) => setLocalConfig({...localConfig, [fieldKey]: parseFloat(e.target.value)})}
                    onBlur={(e) => handleSave(fieldKey, parseFloat(e.target.value))}
                    disabled={isSaving}
                />
             );
        } else {
             // Text
             inputEl = (
                <input 
                    type="text"
                    className="flex-1 bg-black/40 border border-white/10 rounded px-2 py-1 text-sm text-cyan-100 focus:outline-none focus:border-cyan-500/50"
                    value={val || ""}
                    onChange={(e) => setLocalConfig({...localConfig, [fieldKey]: e.target.value})}
                    onBlur={(e) => handleSave(fieldKey, e.target.value)}
                    disabled={isSaving}
                />
             );
        }

        return (
            <div key={prefix + fieldKey} className="flex items-center justify-between mb-3 py-1">
                <div className="flex flex-col mr-4">
                    <span className="text-gray-300 text-sm">{label}</span>
                    {schema.description && <span className="text-[10px] text-gray-500">{schema.description}</span>}
                </div>
                <div className="flex items-center gap-2">
                     {isSaving && <Loader2 size={12} className="animate-spin text-cyan-500" />}
                     {inputEl}
                </div>
            </div>
        );
    };

    if (!plugin.config_schema) return null;

    return (
        <div className="bg-black/20 rounded p-4 border border-white/5 mb-2">
             {/* If root schema is single object */}
             {!plugin.config_schema.fields ? (
                 renderField(plugin.config_schema, localConfig[plugin.config_schema.key] ?? plugin.current_value)
             ) : (
                 // Root schema has multiple fields
                 plugin.config_schema.fields.map(f => renderField(f, localConfig?.[f.key]))
             )}
        </div>
    );
};
