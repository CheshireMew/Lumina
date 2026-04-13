import { useState, useCallback, useEffect, useRef } from "react";
import { API_CONFIG } from "../config";
import { subscribeRuntimeEvent } from "../runtime/events";

// ... (Keep Interfaces) ...
export interface PluginConfigSchema {
    key: string;
    type?: string;
    label?: string;
    default?: any;
    description?: string;
    // For selects
    options?: { label: string; value: any }[];
    optionSource?: string; // "edgeVoices", etc.
    // For nested fields
    fields?: PluginConfigSchema[];
}

export interface PluginStatus {
    id: string;
    name: string;
    version?: string;
    description: string;
    category: string;
    enabled: boolean;
    active: boolean; // Real-time running state
    active_in_group: boolean;
    group_id?: string;
    group_policy: "exclusive" | "independent";
    capabilities: string[];
    runtime_target: string;
    config_schema?: any;
    current_config?: any;
    config?: any;
    current_value?: any;
    ui_slots?: any[];
    permissions?: string[];
    func_tag?: string;
    group_exclusive?: boolean;
    tags?: string[];
    // [Scheme C] Added for Frontend Mesh
    computed_status?: string;
}

export const usePluginManager = () => {
    const [plugins, setPlugins] = useState<PluginStatus[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [transitStates, setTransitStates] = useState<Record<string, string>>(
        {},
    );
    const transitTimeoutsRef = useRef<Record<string, number>>({});

    const refreshPlugins = useCallback(async () => {
        try {
            setIsLoading(true);
            const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/list`);
            if (!res.ok) throw new Error("Failed to fetch plugins");
            const data = await res.json();
            setPlugins(data.items || []);
        } catch (e) {
            console.error("[usePluginManager] Failed to refresh plugins:", e);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const clearTransitState = useCallback((pluginId: string) => {
        const timeoutId = transitTimeoutsRef.current[pluginId];
        if (timeoutId !== undefined) {
            window.clearTimeout(timeoutId);
            delete transitTimeoutsRef.current[pluginId];
        }

        setTransitStates((previous) => {
            if (!(pluginId in previous)) {
                return previous;
            }

            const next = { ...previous };
            delete next[pluginId];
            return next;
        });
    }, []);

    const setTransitState = useCallback(
        (pluginId: string, status: string, autoClearMs?: number) => {
            const timeoutId = transitTimeoutsRef.current[pluginId];
            if (timeoutId !== undefined) {
                window.clearTimeout(timeoutId);
                delete transitTimeoutsRef.current[pluginId];
            }

            setTransitStates((previous) => ({
                ...previous,
                [pluginId]: status,
            }));

            if (autoClearMs && autoClearMs > 0) {
                transitTimeoutsRef.current[pluginId] = window.setTimeout(() => {
                    clearTransitState(pluginId);
                }, autoClearMs);
            }
        },
        [clearTransitState],
    );

    useEffect(() => {
        void refreshPlugins();

        const unsubscribe = subscribeRuntimeEvent("pluginStatus", ({ plugin_id, status }) => {
            setTransitStates((previous) => ({
                ...previous,
                [plugin_id]: status,
            }));

            if (status === "enabled" || status === "disabled") {
                const timeoutId = transitTimeoutsRef.current[plugin_id];
                if (timeoutId !== undefined) {
                    window.clearTimeout(timeoutId);
                }

                transitTimeoutsRef.current[plugin_id] = window.setTimeout(
                    () => {
                        clearTransitState(plugin_id);
                    },
                    500,
                );
            }

            void refreshPlugins();
        });

        return () => {
            unsubscribe();
            Object.values(transitTimeoutsRef.current).forEach((timeoutId) => {
                window.clearTimeout(timeoutId);
            });
            transitTimeoutsRef.current = {};
        };
    }, [clearTransitState, refreshPlugins]);

    // ... (Keep Toggle/Config Logic via HTTP for now, or move to DB?) ...
    // [Scheme C] Toggles still go via Main Backend (Dispatcher) to orchestrate processes
    // until we fully implement the "Intent" pattern in DB triggers.

    // [Architecture 5.0] Unified Toggle
    const togglePlugin = async (plugin: PluginStatus, enabled: boolean) => {
        try {
            setTransitState(
                plugin.id,
                enabled ? "enabling" : "disabling",
                15000,
            );

            const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/toggle`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    id: plugin.id,
                    enabled: enabled,
                }),
            });
            if (!res.ok) {
                clearTransitState(plugin.id);
            }
            return res.ok;
        } catch (e) {
            console.error(
                `[usePluginManager] Failed to toggle ${plugin.id}`,
                e,
            );
            clearTransitState(plugin.id);
        }
        return false;
    };

    // [Architecture 5.0] Unified Config
    const updateConfig = async (
        plugin: PluginStatus,
        key: string,
        value: any,
    ) => {
        try {
            const BASE_URL = API_CONFIG.BASE_URL;
            const res = await fetch(`${BASE_URL}/plugins/config/plugin`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    id: plugin.id,
                    key: key,
                    value: value,
                }),
            });
            return res.ok;
        } catch (e) {
            console.error(
                `[usePluginManager] Failed to update config for ${plugin.id}`,
                e,
            );
        }
        return false;
    };

    return {
        plugins,
        isLoading,
        transitStates,
        refreshPlugins,
        togglePlugin,
        updateConfig,
    };
};
