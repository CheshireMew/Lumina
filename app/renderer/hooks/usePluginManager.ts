import { useState, useCallback, useEffect } from "react";
import { API_CONFIG } from "../config";

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
    runtime_target: "main" | "stt_server" | "tts_server";
    config_schema?: any;
    current_config?: any;
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

    // [Architecture 6.0] Hybrid Fetch (HTTP + EventBus)
    // We fetch initial state via HTTP (Postgres SSOT) and listen for updates via WebSocket
    useEffect(() => {
        let mounted = true;

        const fetchPlugins = async () => {
            setIsLoading(true);
            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/list`);
                if (!res.ok) throw new Error("Failed to fetch plugins");
                const data = await res.json();

                if (mounted) {
                    setPlugins(data.items || data.value || data); // Handle various envelopes
                }
            } catch (e) {
                console.error("[usePluginManager] Failed to fetch plugins:", e);
            } finally {
                if (mounted) setIsLoading(false);
            }
        };

        fetchPlugins();

        // Optional: Poll every 5s if WebSocket isn't fully reliable yet for this
        const interval = setInterval(fetchPlugins, 5000);

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, []);

    // [Compat] Manual Refresh is No-Op in Live Mode
    const refreshPlugins = useCallback(async () => {}, []);

    // ... (Keep Toggle/Config Logic via HTTP for now, or move to DB?) ...
    // [Scheme C] Toggles still go via Main Backend (Dispatcher) to orchestrate processes
    // until we fully implement the "Intent" pattern in DB triggers.

    // [Architecture 5.0] Unified Toggle
    const togglePlugin = async (plugin: PluginStatus, enabled: boolean) => {
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/toggle`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    id: plugin.id,
                    enabled: enabled,
                }),
            });
            return res.ok;
        } catch (e) {
            console.error(
                `[usePluginManager] Failed to toggle ${plugin.id}`,
                e,
            );
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
        refreshPlugins,
        togglePlugin,
        updateConfig,
    };
};
