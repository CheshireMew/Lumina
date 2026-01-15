import { useState, useCallback } from "react";
import { API_CONFIG } from "../config";

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
    description: string;
    category: string;
    enabled: boolean;
    config_schema?: PluginConfigSchema;
    current_value?: any;
    config?: any; // Full config object
    group_id?: string;
    group_exclusive?: boolean;
    func_tag?: string;
}

export const usePluginManager = () => {
    const [plugins, setPlugins] = useState<PluginStatus[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const refreshPlugins = useCallback(async () => {
        setIsLoading(true);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/list`);
            if (res.ok) {
                const data = await res.json();
                setPlugins(data);
            }
        } catch (e) {
            console.error("[usePluginManager] Failed to fetch plugins", e);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const togglePlugin = async (id: string) => {
        try {
            const res = await fetch(
                `${API_CONFIG.BASE_URL}/plugins/toggle/system`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provider_id: id }),
                }
            );
            if (res.ok) {
                await refreshPlugins();
                return true;
            }
        } catch (e) {
            console.error(`[usePluginManager] Failed to toggle ${id}`, e);
        }
        return false;
    };

    const updateConfig = async (pluginId: string, key: string, value: any) => {
        try {
            // Construct key based on plugin ID
            // The backend expects "plugin_id:key" format for system plugins
            const payloadKey = `${pluginId}:${key}`;

            const res = await fetch(
                `${API_CONFIG.BASE_URL}/plugins/config/system`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ key: payloadKey, value }),
                }
            );

            if (res.ok) {
                // Optimistic update or refresh? Refresh is safer for complex logic
                await refreshPlugins();
                return true;
            }
        } catch (e) {
            console.error(
                `[usePluginManager] Failed to update config for ${pluginId}`,
                e
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
