import type { PluginStatus } from "../../hooks/usePluginManager";

export type PluginStoreTab = "skill" | "tts" | "stt" | "system" | "other";

const skillFallbackCategories = new Set(["search", "tool", "memory"]);
const mvpCoreNames = new Set(["LLM Intelligence", "LLM Core", "Emotion Broker"]);

export const shouldShowPluginInTab = (
    plugin: PluginStatus,
    tab: PluginStoreTab,
): boolean => {
    if (plugin.category === tab || plugin.group_id === tab) {
        return true;
    }

    if ((!plugin.category || plugin.category === "") && tab === "other") {
        return true;
    }

    return tab === "skill" && skillFallbackCategories.has(plugin.category);
};

export const isPluginSelected = (plugin: PluginStatus): boolean => {
    const isExclusive =
        plugin.group_policy === "exclusive" || plugin.group_exclusive;
    return isExclusive
        ? (plugin.active_in_group ?? plugin.enabled ?? false)
        : (plugin.enabled ?? false);
};

export const isMvpCorePlugin = (plugin: PluginStatus): boolean => {
    return plugin.tags?.includes("mvp_kernel") || mvpCoreNames.has(plugin.name);
};

export const getPluginIcon = (plugin: PluginStatus): string => {
    if (plugin.category === "skill") {
        return "📦";
    }

    if (plugin.category === "system") {
        return "⏰";
    }

    if (plugin.category === "tts") {
        return "🗣️";
    }

    if (plugin.category === "stt") {
        return "🎙️";
    }

    return "🎛️";
};

export const groupPluginsByTag = (plugins: PluginStatus[]) => {
    return plugins.reduce<Record<string, PluginStatus[]>>((groups, plugin) => {
        const tag = plugin.func_tag || "General";
        if (!groups[tag]) {
            groups[tag] = [];
        }
        groups[tag].push(plugin);
        return groups;
    }, {});
};

export const getPluginTransitLabel = (status?: string): string | null => {
    if (!status) {
        return null;
    }
    return status.toUpperCase();
};

