import React from "react";

import { usePluginManager } from "../../hooks/usePluginManager";
import { PluginConfigRenderer } from "./PluginConfigRenderer";

export const InteractionSettingsPanel: React.FC = () => {
    const { plugins, togglePlugin, updateConfig } = usePluginManager();

    const visiblePlugins = plugins.filter(
        (plugin) =>
            plugin.category === "game" ||
            plugin.category === "interaction" ||
            plugin.category === "skill",
    );

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div
                style={{
                    padding: "15px",
                    background: "#eff6ff",
                    borderRadius: "12px",
                    border: "1px solid #dbeafe",
                    color: "#1e40af",
                    fontSize: "14px",
                }}
            >
                Control system plugins and external tools.
            </div>

            <div>
                <h3
                    style={{
                        fontSize: "16px",
                        fontWeight: 600,
                        marginBottom: "15px",
                        color: "#374151",
                    }}
                >
                    Game Systems
                </h3>
                <div style={{ display: "grid", gap: "15px" }}>
                    {visiblePlugins.map((plugin) => (
                        <div
                            key={plugin.id}
                            style={{
                                background: "white",
                                padding: "20px",
                                borderRadius: "16px",
                                border: "1px solid rgba(0,0,0,0.05)",
                                boxShadow: "0 4px 6px rgba(0,0,0,0.02)",
                            }}
                        >
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    marginBottom: "15px",
                                }}
                            >
                                <div>
                                    <h4 style={{ fontWeight: 700, color: "#111827" }}>
                                        {plugin.name}
                                    </h4>
                                    <p
                                        style={{
                                            fontSize: "13px",
                                            color: "#6B7280",
                                            marginTop: "4px",
                                        }}
                                    >
                                        {plugin.description}
                                    </p>
                                </div>
                                <button
                                    onClick={() => {
                                        void togglePlugin(plugin, !plugin.enabled);
                                    }}
                                    style={{
                                        padding: "6px 12px",
                                        borderRadius: "20px",
                                        fontSize: "12px",
                                        fontWeight: 600,
                                        border: "none",
                                        cursor: "pointer",
                                        background: plugin.enabled ? "#dcfce7" : "#fee2e2",
                                        color: plugin.enabled ? "#166534" : "#991b1b",
                                    }}
                                >
                                    {plugin.enabled ? "Enabled" : "Disabled"}
                                </button>
                            </div>
                            {plugin.enabled && (
                                <div
                                    style={{
                                        borderTop: "1px solid #f3f4f6",
                                        paddingTop: "15px",
                                    }}
                                >
                                    <PluginConfigRenderer
                                        plugin={plugin}
                                        onUpdate={async (key, value) =>
                                            updateConfig(plugin, key, value)
                                        }
                                    />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
