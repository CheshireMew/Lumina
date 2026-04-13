import React, { useEffect, useState } from "react";

import { API_CONFIG } from "../../config";
import { PluginConfigFormSection } from "./PluginConfigFormSection";
import { PluginLlmRoutesSection } from "./PluginLlmRoutesSection";
import { VoiceprintConfigPanel } from "./VoiceprintConfigPanel";

interface PluginConfigModalProps {
    plugin: any;
    onClose: () => void;
    onSave: (key: string, value: any) => Promise<void>;
}

const PluginConfigModal: React.FC<PluginConfigModalProps> = ({
    plugin,
    onClose,
    onSave,
}) => {
    const [values, setValues] = useState<Record<string, any>>({});
    const [saving, setSaving] = useState(false);
    const [llmRoutes, setLlmRoutes] = useState<any[]>([]);
    const [llmProviders, setLlmProviders] = useState<any[]>([]);
    const [expandedRoutes, setExpandedRoutes] = useState<Set<string>>(new Set());

    useEffect(() => {
        const initialValues: Record<string, any> = {};
        if (plugin?.config_schema) {
            initialValues[plugin.config_schema.key] =
                plugin.current_config?.[plugin.config_schema.key] ?? "";
        }

        initialValues.__group_id = plugin?.group_id || "";
        initialValues.__category = plugin?.category || "";
        initialValues.__group_behavior =
            plugin?.group_exclusive === false ? "independent" : "exclusive";

        setValues(initialValues);

        if (plugin?.llm_routes?.length > 0) {
            void fetchLlmData();
        }
    }, [plugin]);

    const fetchLlmData = async () => {
        try {
            const [routesResponse, providersResponse] = await Promise.all([
                fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/routes`),
                fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/providers`),
            ]);

            if (!routesResponse.ok || !providersResponse.ok) {
                return;
            }

            const routesData = await routesResponse.json();
            const providersData = await providersResponse.json();
            setLlmRoutes(routesData.routes || []);
            setLlmProviders(providersData.providers || []);
        } catch (error) {
            console.error("Failed to fetch LLM data", error);
        }
    };

    const handleRouteUpdate = async (
        feature: string,
        providerId: string,
        model: string,
        temperature?: number,
        topP?: number,
        presencePenalty?: number,
        frequencyPenalty?: number,
    ) => {
        try {
            setLlmRoutes((previous) =>
                previous.map((route) =>
                    route.feature === feature
                        ? {
                              ...route,
                              provider_id: providerId,
                              model,
                              temperature,
                              top_p: topP,
                              presence_penalty: presencePenalty,
                              frequency_penalty: frequencyPenalty,
                          }
                        : route,
                ),
            );

            await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/routes/${feature}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    provider_id: providerId,
                    model,
                    temperature,
                    top_p: topP,
                    presence_penalty: presencePenalty,
                    frequency_penalty: frequencyPenalty,
                }),
            });
        } catch (error) {
            console.error("Failed to update route", error);
            void fetchLlmData();
        }
    };

    if (!plugin) {
        return null;
    }

    const schema = plugin.config_schema;
    const currentValue = schema
        ? values[schema.key] !== undefined
            ? values[schema.key]
            : plugin.current_config?.[schema.key] ?? ""
        : "";
    const pluginRoutes = llmRoutes.filter((route) =>
        plugin.llm_routes?.includes(route.feature),
    );
    const hasLlmRoutes = pluginRoutes.length > 0;

    const handleSave = async () => {
        setSaving(true);
        try {
            if (schema) {
                if (schema.fields) {
                    for (const field of schema.fields) {
                                const value =
                                    values[field.key] !== undefined
                                        ? values[field.key]
                                        : plugin.current_config?.[field.key] ?? field.default ?? "";
                        await onSave(field.key, value);
                    }
                } else {
                    await onSave(schema.key, currentValue);
                }
            }
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="plugin-modal-overlay">
            <div className="plugin-config-modal glass-panel">
                <div className="modal-header">
                    <h3>Configure {plugin.name}</h3>
                    <button className="close-btn" onClick={onClose}>
                        x
                    </button>
                </div>

                <div className="modal-body">
                    <p className="config-desc">{plugin.description}</p>

                    <PluginLlmRoutesSection
                        pluginRoutes={pluginRoutes}
                        llmProviders={llmProviders}
                        expandedRoutes={expandedRoutes}
                        setExpandedRoutes={setExpandedRoutes}
                        onRouteUpdate={handleRouteUpdate}
                    />

                    {plugin.id === "system.voiceprint" ? (
                        <VoiceprintConfigPanel
                            threshold={Number(currentValue) || 0.6}
                            onThresholdChange={(value) => {
                                if (plugin.config_schema?.key) {
                                    setValues((previous) => ({
                                        ...previous,
                                        [plugin.config_schema.key]: value,
                                    }));
                                }
                            }}
                        />
                    ) : (
                        <PluginConfigFormSection
                            plugin={plugin}
                            hasLlmRoutes={hasLlmRoutes}
                            schema={schema}
                            values={values}
                            setValues={setValues}
                        />
                    )}
                </div>

                <div className="modal-footer">
                    <button className="galgame-btn secondary" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className="galgame-btn primary"
                        onClick={() => {
                            void handleSave();
                        }}
                        disabled={saving}
                    >
                        {saving ? "Saving..." : "Save Changes"}
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
                    padding-right: 5px;
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
                    box-sizing: border-box;
                }
                .modal-footer {
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                    margin-top: 20px;
                    padding-top: 15px;
                    border-top: 1px solid rgba(255,255,255,0.05);
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
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default PluginConfigModal;
