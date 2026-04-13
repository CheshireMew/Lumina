import React, { useCallback, useEffect, useMemo, useState } from "react";

import "./PluginStoreModal.css";

import PluginCard from "./PluginCard";
import PluginConfigModal from "./PluginConfigModal";
import PluginPermissionModal from "./PluginPermissionModal";
import { usePluginManager, type PluginStatus } from "../../hooks/usePluginManager";
import {
    groupPluginsByTag,
    shouldShowPluginInTab,
    type PluginStoreTab,
} from "./pluginStoreUtils";
import { usePluginUpload } from "./usePluginUpload";

interface PluginStoreModalProps {
    isOpen: boolean;
    onClose: () => void;
    onOpenLLMSettings?: () => void;
}

const PluginCardSkeleton = () => (
    <div className="plugin-card skeleton-card">
        <div className="card-header">
            <div className="skeleton skeleton-icon"></div>
            <div className="header-text">
                <div className="skeleton skeleton-title"></div>
                <div className="skeleton skeleton-desc"></div>
                <div className="skeleton skeleton-desc-short"></div>
            </div>
            <div className="skeleton skeleton-toggle"></div>
        </div>
    </div>
);

const PluginStoreModal: React.FC<PluginStoreModalProps> = ({
    isOpen,
    onClose,
    onOpenLLMSettings,
}) => {
    const [activeTab, setActiveTab] = useState<PluginStoreTab>("skill");
    const [configPlugin, setConfigPlugin] = useState<PluginStatus | null>(null);
    const [pendingPlugin, setPendingPlugin] = useState<PluginStatus | null>(
        null,
    );
    const [dragActive, setDragActive] = useState(false);

    const {
        plugins,
        isLoading,
        transitStates,
        refreshPlugins,
        togglePlugin,
        updateConfig,
    } = usePluginManager();
    const { uploadStatus, uploadPlugin } = usePluginUpload(refreshPlugins);

    useEffect(() => {
        if (isOpen) {
            void refreshPlugins();
        }
    }, [isOpen, refreshPlugins]);

    const filteredPlugins = useMemo(
        () => plugins.filter((plugin) => shouldShowPluginInTab(plugin, activeTab)),
        [activeTab, plugins],
    );

    const groupedPlugins = useMemo(
        () => groupPluginsByTag(filteredPlugins),
        [filteredPlugins],
    );

    const handleDrag = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.stopPropagation();

        if (event.type === "dragenter" || event.type === "dragover") {
            setDragActive(true);
            return;
        }

        if (event.type === "dragleave") {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();
            event.stopPropagation();
            setDragActive(false);

            const file = event.dataTransfer.files?.[0];
            if (file) {
                void uploadPlugin(file);
            }
        },
        [uploadPlugin],
    );

    const executeToggle = useCallback(
        async (plugin: PluginStatus, newState: boolean) => {
            console.log(
                `[PluginStore] Executing Toggle ${plugin.id} to ${newState}`,
            );
            await togglePlugin(plugin, newState);
        },
        [togglePlugin],
    );

    const handleToggle = useCallback(
        (plugin: PluginStatus, newState: boolean) => {
            if (newState && plugin.permissions && plugin.permissions.length > 0) {
                setPendingPlugin(plugin);
                return;
            }

            void executeToggle(plugin, newState);
        },
        [executeToggle],
    );

    const handleConfirmPermission = useCallback(() => {
        if (!pendingPlugin) {
            return;
        }

        void executeToggle(pendingPlugin, true);
        setPendingPlugin(null);
    }, [executeToggle, pendingPlugin]);

    const handleSaveConfig = useCallback(
        async (key: string, value: string) => {
            if (!configPlugin) {
                return;
            }

            await updateConfig(configPlugin, key, value);
        },
        [configPlugin, updateConfig],
    );

    const handleOpenConfig = useCallback((plugin: PluginStatus) => {
        setConfigPlugin(plugin);
    }, []);

    if (!isOpen) {
        return null;
    }

    return (
        <div className="plugin-modal-overlay">
            <div className="plugin-modal-container glass-panel">
                <div className="plugin-header">
                    <h2>🧩 Plugin Store</h2>
                    <button className="close-btn" onClick={onClose}>
                        ×
                    </button>
                </div>

                <div className="plugin-tabs">
                    <button
                        className={activeTab === "skill" ? "active" : ""}
                        onClick={() => setActiveTab("skill")}
                    >
                        Skills
                    </button>
                    <button
                        className={activeTab === "tts" ? "active" : ""}
                        onClick={() => setActiveTab("tts")}
                    >
                        Voice Output
                    </button>
                    <button
                        className={activeTab === "stt" ? "active" : ""}
                        onClick={() => setActiveTab("stt")}
                    >
                        Voice Input
                    </button>
                    <button
                        className={activeTab === "system" ? "active" : ""}
                        onClick={() => setActiveTab("system")}
                    >
                        System
                    </button>
                    <button
                        className={activeTab === "other" ? "active" : ""}
                        onClick={() => setActiveTab("other")}
                    >
                        Other
                    </button>
                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center" }}>
                        <label
                            className="import-btn"
                            style={{ cursor: "pointer", fontSize: "0.9em", opacity: 0.8 }}
                        >
                            {uploadStatus === "uploading"
                                ? "📥 Uploading..."
                                : "📥 Install .zip"}
                            <input
                                type="file"
                                accept=".zip"
                                style={{ display: "none" }}
                                onChange={(event) => {
                                    const file = event.target.files?.[0];
                                    if (file) {
                                        void uploadPlugin(file);
                                    }
                                }}
                            />
                        </label>
                    </div>
                </div>

                <div
                    className={`plugin-content ${dragActive ? "drag-active" : ""}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    style={{ position: "relative" }}
                >
                    {dragActive && (
                        <div
                            className="drag-overlay"
                            style={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                right: 0,
                                bottom: 0,
                                background: "rgba(0,0,0,0.7)",
                                zIndex: 100,
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                justifyContent: "center",
                                backdropFilter: "blur(4px)",
                                borderRadius: "12px",
                                border: "2px dashed #a29bfe",
                            }}
                        >
                            <div style={{ fontSize: "3em" }}>📦</div>
                            <h3>Drop Plugin Zip Here</h3>
                        </div>
                    )}

                    {isLoading ? (
                        <div className="plugin-grid" style={{ marginTop: "20px" }}>
                            {[1, 2, 3, 4, 5, 6].map((index) => (
                                <PluginCardSkeleton key={index} />
                            ))}
                        </div>
                    ) : (
                        <>
                            {Object.entries(groupedPlugins).map(([tag, tagPlugins]) => (
                                <div key={tag} className="plugin-group">
                                    <h4 className="group-header">{tag}</h4>
                                    <div className="plugin-grid">
                                        {tagPlugins.map((plugin) => (
                                            <PluginCard
                                                key={plugin.id}
                                                plugin={plugin}
                                                transitStatus={transitStates[plugin.id]}
                                                onOpenConfig={handleOpenConfig}
                                                onToggle={handleToggle}
                                                onOpenLLMSettings={onOpenLLMSettings}
                                            />
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </>
                    )}
                </div>
            </div>

            {configPlugin && (
                <PluginConfigModal
                    plugin={configPlugin}
                    onClose={() => setConfigPlugin(null)}
                    onSave={handleSaveConfig}
                />
            )}

            {pendingPlugin && (
                <PluginPermissionModal
                    plugin={pendingPlugin}
                    onCancel={() => setPendingPlugin(null)}
                    onConfirm={handleConfirmPermission}
                />
            )}
        </div>
    );
};

export default PluginStoreModal;

