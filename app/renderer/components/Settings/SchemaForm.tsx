
import React from 'react';
import GalgameSelect from '../PluginStore/GalgameSelect';

export interface SchemaField {
    key: string;
    label: string;
    type: 'text' | 'number' | 'select' | 'slider';
    options?: { label: string; value: any }[];
    min?: number;
    max?: number;
    step?: number;
    default?: any;
    // ⚡ Extension for dynamic lists
    optionSource?: 'edgeVoices' | 'gptVoices'; 
}

export interface ConfigSchema {
    key: string; // Legacy single-field key
    fields?: SchemaField[]; // Multi-field Support
    label?: string; // Legacy
    type?: string; // Legacy
    options?: any[]; // Legacy
}

interface SchemaFormProps {
    schema: ConfigSchema;
    values: { [key: string]: any };
    onChange: (key: string, value: any) => void;
    // ⚡ Inject dynamic data sources
    dataSources?: {
        edgeVoices?: any[];
        gptVoices?: any[];
    };
}

export const SchemaForm: React.FC<SchemaFormProps> = ({ schema, values, onChange, dataSources }) => {
    
    // Resolve Fields (V2 vs V1)
    const fields = schema.fields || [{
        key: schema.key, // Fallback for single-field schema
        label: schema.label || "Value",
        type: (schema.type as any) || 'text',
        options: schema.options,
        default: undefined
    }];

    return (
        <div className="schema-form">
            {fields.map((field) => {
                const val = values[field.key] !== undefined ? values[field.key] : (field.default ?? "");
                
                // ⚡ Dynamic Options Resolution
                let options = field.options;
                if (field.optionSource && dataSources) {
                    if (field.optionSource === 'edgeVoices' && dataSources.edgeVoices) {
                        options = dataSources.edgeVoices.map(v => ({
                            label: `${v.name.replace('zh-CN-', '').replace('Neural', '')} (${v.gender})`,
                            value: v.name
                        }));
                    } else if (field.optionSource === 'gptVoices' && dataSources.gptVoices) {
                        options = dataSources.gptVoices.map(v => ({
                             label: v.name,
                             value: v.name
                        }));
                    }
                }

                return (
                    <div key={field.key} style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#e0e0e0' }}>
                            {field.label}
                        </label>
                        
                        {field.type === 'select' ? (
                            <GalgameSelect
                                value={val}
                                options={options || []}
                                onChange={(v) => onChange(field.key, v)}
                            />
                        ) : field.type === 'slider' ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <input
                                    type="range"
                                    min={field.min ?? 0}
                                    max={field.max ?? 100}
                                    step={field.step ?? 1}
                                    value={parseFloat(val) || 0}
                                    onChange={(e) => onChange(field.key, e.target.value)}
                                    style={{ flex: 1, accentColor: '#a78bfa', cursor: 'pointer' }}
                                />
                                <span style={{ width: '40px', fontSize: '12px', color: '#ccc', textAlign: 'right' }}>
                                    {val}
                                </span>
                            </div>
                        ) : (
                            <input
                                type={field.type === 'number' ? 'number' : 'text'}
                                value={val}
                                onChange={(e) => onChange(field.key, e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '8px 12px',
                                    background: 'rgba(0,0,0,0.3)',
                                    border: '1px solid rgba(255,255,255,0.2)',
                                    borderRadius: '6px',
                                    color: 'white',
                                    boxSizing: 'border-box'
                                }}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
};
