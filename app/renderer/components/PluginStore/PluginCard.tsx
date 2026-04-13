import React from "react";

import GalgameToggle from "./GalgameToggle";
import {
    getPluginIcon,
    getPluginTransitLabel,
    isMvpCorePlugin,
    isPluginSelected,
} from "./pluginStoreUtils";
import type { PluginStatus } from "../../hooks/usePluginManager";

interface PluginCardProps {
    plugin: PluginStatus;
    transitStatus?: string;
    onOpenConfig: (plugin: PluginStatus) => void;
    onToggle: (plugin: PluginStatus, nextState: boolean) => void;
    onOpenLLMSettings?: () => void;
}

const PluginCard: React.FC<PluginCardProps> = ({
    plugin,
    transitStatus,
    onOpenConfig,
    onToggle,
    onOpenLLMSettings,
}) => {
    const isSelected = isPluginSelected(plugin);
    const isMvpCore = isMvpCorePlugin(plugin);
    const isGrouped = !!plugin.group_id;
    const transitLabel = getPluginTransitLabel(transitStatus);

    const handleOpenConfig = () => {
        if (!isSelected && !plugin.config_schema) {
            return;
        }

        if (plugin.name === "LLM Intelligence" || plugin.name === "LLM Core") {
            onOpenLLMSettings?.();
            return;
        }

        if (plugin.name === "Emotion Broker") {
            return;
        }

        onOpenConfig(plugin);
    };

    return (
        <div
            className={`plugin-card ${isSelected ? "active-card" : ""} ${
                isMvpCore ? "mvp-core-card" : ""
            } clickable`}
            onClick={(event) => {
                event.stopPropagation();
                handleOpenConfig();
            }}
        >
            <div className="card-top-row">
                <div className="header-left">
                    <span className="plugin-icon">{getPluginIcon(plugin)}</span>
                    <h3 className="plugin-title-inline">{plugin.name}</h3>
                </div>

                <div onClick={(event) => event.stopPropagation()}>
                    {transitLabel ? (
                        <div className="plugin-transit-state">
                            <span className="spinner-small"></span>
                            <span className="transit-label">{transitLabel}...</span>
                        </div>
                    ) : (
                        <GalgameToggle
                            checked={isSelected}
                            onChange={(nextState) => onToggle(plugin, nextState)}
                            labelOn={isGrouped ? "USE" : "ON"}
                            labelOff="OFF"
                        />
                    )}
                </div>
            </div>

            <div className="card-mid-row">
                <div className="badge-row">
                    {isMvpCore && <span className="core-badge">MVP KERNEL</span>}
                    {plugin.permissions && plugin.permissions.length > 0 && (
                        <span className="perm-badge" title="Requires Permissions">
                            {" "}
                            🛡️
                        </span>
                    )}
                </div>
            </div>

            <p className="description">{plugin.description}</p>
        </div>
    );
};

export default PluginCard;

