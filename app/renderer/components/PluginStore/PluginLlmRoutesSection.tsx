import React from "react";

interface PluginLlmRoutesSectionProps {
    pluginRoutes: any[];
    llmProviders: any[];
    expandedRoutes: Set<string>;
    setExpandedRoutes: React.Dispatch<React.SetStateAction<Set<string>>>;
    onRouteUpdate: (
        feature: string,
        providerId: string,
        model: string,
        temperature?: number,
        topP?: number,
        presencePenalty?: number,
        frequencyPenalty?: number,
    ) => Promise<void>;
}

export const PluginLlmRoutesSection: React.FC<PluginLlmRoutesSectionProps> = ({
    pluginRoutes,
    llmProviders,
    expandedRoutes,
    setExpandedRoutes,
    onRouteUpdate,
}) => {
    if (pluginRoutes.length === 0) {
        return null;
    }

    return (
        <div
            style={{
                marginBottom: "25px",
                background: "rgba(255,255,255,0.03)",
                padding: "15px",
                borderRadius: "8px",
                border: "1px solid rgba(255,255,255,0.1)",
            }}
        >
            <h4
                style={{
                    margin: "0 0 12px 0",
                    color: "#a78bfa",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "0.95em",
                }}
            >
                Neural Configuration
            </h4>
            {pluginRoutes.map((route) => {
                const isExpanded = expandedRoutes.has(route.feature);
                const currentProvider = llmProviders.find(
                    (provider) => provider.id === route.provider_id,
                );

                const toggleExpand = () => {
                    const next = new Set(expandedRoutes);
                    if (next.has(route.feature)) {
                        next.delete(route.feature);
                    } else {
                        next.add(route.feature);
                    }
                    setExpandedRoutes(next);
                };

                const update = (changes: any) =>
                    onRouteUpdate(
                        route.feature,
                        changes.provider_id ?? route.provider_id,
                        changes.model ?? route.model,
                        changes.temperature ?? route.temperature ?? 0.7,
                        changes.top_p ?? route.top_p ?? 1.0,
                        changes.presence_penalty ?? route.presence_penalty ?? 0.0,
                        changes.frequency_penalty ?? route.frequency_penalty ?? 0.0,
                    );

                return (
                    <div
                        key={route.feature}
                        style={{
                            marginBottom: "10px",
                            background: "rgba(0,0,0,0.2)",
                            padding: "10px",
                            borderRadius: "6px",
                        }}
                    >
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                fontSize: "13px",
                                marginBottom: isExpanded ? "10px" : "0",
                            }}
                        >
                            <div
                                style={{
                                    flex: 1,
                                    fontWeight: 600,
                                    color: "#e0e0e0",
                                    textTransform: "capitalize",
                                }}
                            >
                                {route.feature}
                            </div>

                            <select
                                className="galgame-input"
                                style={{
                                    width: "100px",
                                    padding: "4px",
                                    height: "28px",
                                    fontSize: "12px",
                                }}
                                value={route.provider_id}
                                onChange={(event) =>
                                    void update({ provider_id: event.target.value })
                                }
                            >
                                {llmProviders.map((provider) => (
                                    <option key={provider.id} value={provider.id}>
                                        {provider.id}
                                    </option>
                                ))}
                            </select>
                            <select
                                className="galgame-input"
                                style={{
                                    width: "140px",
                                    padding: "4px",
                                    height: "28px",
                                    fontSize: "12px",
                                }}
                                value={route.model}
                                onChange={(event) =>
                                    void update({ model: event.target.value })
                                }
                            >
                                {currentProvider?.models?.map((model: string) => (
                                    <option key={model} value={model}>
                                        {model}
                                    </option>
                                ))}
                                {!currentProvider?.models?.includes(route.model) && (
                                    <option value={route.model}>{route.model}</option>
                                )}
                            </select>

                            <button
                                onClick={toggleExpand}
                                style={{
                                    border: "none",
                                    background: "none",
                                    cursor: "pointer",
                                    color: "#a78bfa",
                                    padding: "4px",
                                }}
                                title="Advanced Params"
                            >
                                {"{}"}
                            </button>
                        </div>

                        {isExpanded && (
                            <div
                                style={{
                                    display: "grid",
                                    gridTemplateColumns: "1fr 1fr",
                                    gap: "15px",
                                    paddingTop: "10px",
                                    borderTop: "1px solid rgba(255,255,255,0.1)",
                                }}
                            >
                                {[
                                    {
                                        label: "Temp",
                                        key: "temperature",
                                        min: 0,
                                        max: 2,
                                        step: 0.1,
                                        val: route.temperature,
                                    },
                                    {
                                        label: "Top P",
                                        key: "top_p",
                                        min: 0,
                                        max: 1,
                                        step: 0.05,
                                        val: route.top_p,
                                    },
                                    {
                                        label: "Pres. Penalty",
                                        key: "presence_penalty",
                                        min: 0,
                                        max: 2,
                                        step: 0.1,
                                        val: route.presence_penalty,
                                    },
                                    {
                                        label: "Freq. Penalty",
                                        key: "frequency_penalty",
                                        min: 0,
                                        max: 2,
                                        step: 0.1,
                                        val: route.frequency_penalty,
                                    },
                                ].map((parameter) => (
                                    <div key={parameter.key}>
                                        <div
                                            style={{
                                                display: "flex",
                                                justifyContent: "space-between",
                                                marginBottom: "4px",
                                            }}
                                        >
                                            <label
                                                style={{ fontSize: "11px", color: "#aaa" }}
                                            >
                                                {parameter.label}
                                            </label>
                                            <span
                                                style={{
                                                    fontSize: "11px",
                                                    color: "#a78bfa",
                                                }}
                                            >
                                                {parameter.val ?? 0}
                                            </span>
                                        </div>
                                        <input
                                            type="range"
                                            min={parameter.min}
                                            max={parameter.max}
                                            step={parameter.step}
                                            value={
                                                parameter.val ??
                                                (parameter.key === "top_p"
                                                    ? 1.0
                                                    : parameter.key === "temperature"
                                                      ? 0.7
                                                      : 0.0)
                                            }
                                            onChange={(event) =>
                                                void update({
                                                    [parameter.key]: parseFloat(
                                                        event.target.value,
                                                    ),
                                                })
                                            }
                                            style={{
                                                width: "100%",
                                                accentColor: "#a78bfa",
                                                height: "4px",
                                                cursor: "pointer",
                                            }}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};
