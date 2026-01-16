import { useState, useEffect, useCallback, useRef } from "react";
import { API_CONFIG } from "../config";
import { ttsService } from "@core/voice/tts_service";
import { memoryService } from "@core/memory/memory_service";

export interface LLMSettings {
    apiKey: string;
    baseUrl: string;
    model: string;
    temperature: number;
    thinkingEnabled: boolean;
    historyLimit: number;
    overflowStrategy: "slide" | "reset";
    topP?: number;
    presencePenalty?: number;
    frequencyPenalty?: number;
}

export interface AppSettings {
    llm: LLMSettings;
    userName: string;
    contextWindow: number;
    live2dHighDpi: boolean;
    isTTSEnabled: boolean;
    backgroundImage: string; // Add this
    // isThinkingEnabled is now part of LLMSettings
}

const DEFAULT_SETTINGS: AppSettings = {
    llm: {
        apiKey: "",
        baseUrl: "https://api.deepseek.com/v1",
        model: "deepseek-chat",
        temperature: 0.7,
        topP: 1.0,
        presencePenalty: 0.0,
        frequencyPenalty: 0.0,
        thinkingEnabled: false,
        historyLimit: 20,
        overflowStrategy: "slide",
    },
    userName: "Master",
    contextWindow: 50,
    live2dHighDpi: false,
    isTTSEnabled: true,
    backgroundImage: "", // Add default
};

/**
 * useSettings Hook
 *
 * Centralized settings management for the application.
 * Handles loading, saving, and synchronizing settings.
 *
 * Extracted from App.tsx to improve modularity.
 */
export function useSettings() {
    const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
    const [isLoaded, setIsLoaded] = useState(false);

    // Track previous LLM settings for change detection
    const prevLLMRef = useRef<LLMSettings | null>(null);

    /**
     * Load settings from Electron store on mount.
     */
    useEffect(() => {
        const load = async () => {
            const store = window.settings;
            if (!store) {
                console.warn("[useSettings] No settings store available");
                setIsLoaded(true);
                return;
            }

            try {
                // Load dynamic ports if available (Electron packaged mode)
                if (window.app?.getPorts) {
                    try {
                        const ports = await window.app.getPorts();
                        if (ports?.memory && ports?.tts) {
                            console.log("[useSettings] Dynamic ports:", ports);
                            API_CONFIG.BASE_URL = `http://127.0.0.1:${ports.memory}`;
                            API_CONFIG.TTS_BASE_URL = `http://127.0.0.1:${ports.tts}`;
                            memoryService.setBaseUrl(API_CONFIG.BASE_URL);
                            ttsService.setBaseUrl(API_CONFIG.TTS_BASE_URL);
                        }
                    } catch (e) {
                        console.warn("[useSettings] Failed to load ports:", e);
                    }
                }

                // Load all settings
                const [
                    apiKey,
                    baseUrl,
                    model,
                    temperature,
                    thinkingEnabled,
                    userName,
                    highDpi,
                    historyLimit,
                    overflowStrategy,
                    contextWindow,
                    backgroundImage, // Load this
                ] = await Promise.all([
                    store.get("apiKey"),
                    store.get("apiBaseUrl"),
                    store.get("modelName"),
                    store.get("llm_temperature"),
                    store.get("thinking_enabled"),
                    store.get("userName"), // 5: userName
                    store.get("live2d_high_dpi"), // 6: highDpi
                    store.get("history_limit"), // 7: historyLimit
                    store.get("overflow_strategy"), // 8: overflowStrategy
                    store.get("contextWindow"), // 9: contextWindow
                    store.get("backgroundImage"), // Fetch this
                ]);

                const loaded: AppSettings = {
                    llm: {
                        apiKey: apiKey || "",
                        baseUrl: baseUrl || DEFAULT_SETTINGS.llm.baseUrl,
                        model: model || DEFAULT_SETTINGS.llm.model,
                        temperature:
                            temperature ?? DEFAULT_SETTINGS.llm.temperature,
                        thinkingEnabled:
                            thinkingEnabled ??
                            DEFAULT_SETTINGS.llm.thinkingEnabled,
                        historyLimit:
                            historyLimit ?? DEFAULT_SETTINGS.llm.historyLimit,
                        overflowStrategy:
                            overflowStrategy ??
                            DEFAULT_SETTINGS.llm.overflowStrategy,
                    },
                    userName: userName || DEFAULT_SETTINGS.userName,
                    contextWindow:
                        contextWindow || DEFAULT_SETTINGS.contextWindow,
                    live2dHighDpi: highDpi || false,
                    isTTSEnabled: DEFAULT_SETTINGS.isTTSEnabled,
                    backgroundImage: backgroundImage || "", // Assign
                };

                prevLLMRef.current = loaded.llm;
                setSettings(loaded);

                // Configure memory service if API key exists
                if (loaded.llm.apiKey) {
                    memoryService.configure(
                        loaded.llm.apiKey,
                        loaded.llm.baseUrl,
                        loaded.llm.model
                    );
                }

                console.log("[useSettings] Loaded");
            } catch (error) {
                console.error("[useSettings] Load failed:", error);
            } finally {
                setIsLoaded(true);
            }
        };

        load();
    }, []);

    /**
     * Update a specific setting.
     */
    const updateSetting = useCallback(
        <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
            setSettings((prev) => ({ ...prev, [key]: value }));
        },
        []
    );

    /**
     * Update LLM settings and reconfigure services.
     */
    const updateLLMSettings = useCallback(async (llm: LLMSettings) => {
        const store = window.settings;

        // Check if changed
        const prev = prevLLMRef.current;
        const changed =
            !prev ||
            prev.apiKey !== llm.apiKey ||
            prev.baseUrl !== llm.baseUrl ||
            prev.model !== llm.model ||
            prev.temperature !== llm.temperature ||
            prev.topP !== llm.topP ||
            prev.presencePenalty !== llm.presencePenalty ||
            prev.frequencyPenalty !== llm.frequencyPenalty ||
            prev.thinkingEnabled !== llm.thinkingEnabled ||
            prev.historyLimit !== llm.historyLimit ||
            prev.overflowStrategy !== llm.overflowStrategy;

        if (!changed) return;

        // Save to store
        if (store) {
            await store.set("apiKey", llm.apiKey);
            await store.set("apiBaseUrl", llm.baseUrl);
            await store.set("modelName", llm.model);
            await store.set("llm_temperature", llm.temperature);
            await store.set("llm_top_p", llm.topP);
            await store.set("llm_presence_penalty", llm.presencePenalty);
            await store.set("llm_frequency_penalty", llm.frequencyPenalty);
            await store.set("thinking_enabled", llm.thinkingEnabled);
            await store.set("history_limit", llm.historyLimit);
            await store.set("overflow_strategy", llm.overflowStrategy);
        }

        // Update local state
        setSettings((prev) => ({ ...prev, llm }));
        prevLLMRef.current = llm;

        // Reconfigure services
        memoryService.configure(llm.apiKey, llm.baseUrl, llm.model);

        console.log("[useSettings] LLM settings updated");
    }, []);

    /**
     * Save a simple setting to the store.
     */
    const saveSetting = useCallback(
        async <K extends keyof AppSettings>(
            key: K,
            storeKey: string,
            value: AppSettings[K]
        ) => {
            const store = window.settings;
            if (store) {
                await store.set(storeKey, value);
            }
            updateSetting(key, value);
        },
        [updateSetting]
    );

    return {
        settings,
        isLoaded,
        updateSetting,
        updateLLMSettings,
        saveSetting,
    };
}
