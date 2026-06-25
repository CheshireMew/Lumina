import { useState, useEffect, useCallback, useRef } from "react";
import {
    fetchRuntimeLlmSettings,
    updateRuntimeLlmSettings,
} from "../api/settingsApi";
import {
    CUSTOM_LLM_PROVIDER_ID,
    FREE_LLM_PROVIDER_ID,
    LlmProviderId,
} from "../components/LLMConfig/types";
import { electronSettings, loadBootstrapState } from "../platform/electron";

export interface LLMSettings {
    providerId: LlmProviderId;
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
    backgroundImage: string;
}

type LocalSettingKey =
    | "userName"
    | "contextWindow"
    | "live2dHighDpi"
    | "isTTSEnabled"
    | "backgroundImage";

export interface GeneralSettingsInput {
    userName: string;
    live2dHighDpi: boolean;
    backgroundImage: string;
}

export type GeneralSettingsPatch = Partial<GeneralSettingsInput>;

const DEFAULT_SETTINGS: AppSettings = {
    llm: {
        providerId: FREE_LLM_PROVIDER_ID,
        apiKey: "",
        baseUrl: "",
        model: "",
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
    backgroundImage: "",
};

const LOCAL_SETTING_STORE_KEYS: Record<LocalSettingKey, string> = {
    userName: "userName",
    contextWindow: "contextWindow",
    live2dHighDpi: "live2d_high_dpi",
    isTTSEnabled: "isTTSEnabled",
    backgroundImage: "backgroundImage",
};

/**
 * useSettings Hook
 *
 * Centralized settings management for the application.
 * Handles loading, saving, and synchronizing settings.
 *
 * Extracted from App.tsx to improve modularity.
 */
export function useSettings(backendReady: boolean, baseUrl: string) {
    const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
    const [isLoaded, setIsLoaded] = useState(false);

    // Track previous LLM settings for change detection
    const prevLLMRef = useRef<LLMSettings | null>(null);

    /**
     * Load settings from Electron store on mount.
     */
    useEffect(() => {
        const load = async () => {
            try {
                const { localSettings } = await loadBootstrapState();

                const loaded: AppSettings = {
                    llm: {
                        ...DEFAULT_SETTINGS.llm,
                        thinkingEnabled:
                            localSettings.thinkingEnabled ??
                            DEFAULT_SETTINGS.llm.thinkingEnabled,
                    },
                    userName: localSettings.userName || DEFAULT_SETTINGS.userName,
                    contextWindow:
                        localSettings.contextWindow ||
                        DEFAULT_SETTINGS.contextWindow,
                    live2dHighDpi: localSettings.live2dHighDpi ?? false,
                    isTTSEnabled:
                        localSettings.isTTSEnabled ??
                        DEFAULT_SETTINGS.isTTSEnabled,
                    backgroundImage: localSettings.backgroundImage || "",
                };

                prevLLMRef.current = loaded.llm;
                setSettings(loaded);

                console.log("[useSettings] Loaded");
            } catch (error) {
                console.error("[useSettings] Load failed:", error);
            } finally {
                setIsLoaded(true);
            }
        };

        load();
    }, []);

    const refreshRuntimeSettings = useCallback(async () => {
        if (!backendReady) {
            return;
        }

        try {
            const llm = await fetchRuntimeLlmSettings(baseUrl);
            setSettings((prev) => {
                const nextLlm: LLMSettings = {
                    apiKey: llm.apiKey ?? prev.llm.apiKey,
                    providerId: (llm.providerId as LlmProviderId) ?? prev.llm.providerId,
                    baseUrl: llm.baseUrl || prev.llm.baseUrl,
                    model: llm.model || prev.llm.model,
                    temperature: llm.temperature ?? prev.llm.temperature,
                    topP: llm.topP ?? prev.llm.topP,
                    presencePenalty:
                        llm.presencePenalty ?? prev.llm.presencePenalty,
                    frequencyPenalty:
                        llm.frequencyPenalty ?? prev.llm.frequencyPenalty,
                    thinkingEnabled: prev.llm.thinkingEnabled,
                    historyLimit: llm.historyLimit ?? prev.llm.historyLimit,
                    overflowStrategy:
                        llm.overflowStrategy ?? prev.llm.overflowStrategy,
                };

                prevLLMRef.current = nextLlm;

                return {
                    ...prev,
                    llm: nextLlm,
                };
            });
        } catch (error) {
            console.warn("[useSettings] Runtime settings refresh failed:", error);
        }
    }, [backendReady, baseUrl]);

    useEffect(() => {
        void refreshRuntimeSettings();
    }, [refreshRuntimeSettings]);

    const persistLocalSettings = useCallback(
        async (partial: Partial<Pick<AppSettings, LocalSettingKey>>) => {
            const entries = Object.entries(partial) as [
                LocalSettingKey,
                AppSettings[LocalSettingKey],
            ][];

            if (entries.length === 0) {
                return;
            }

            let previousValues: Partial<Pick<AppSettings, LocalSettingKey>> = {};
            setSettings((prev) => {
                previousValues = entries.reduce(
                    (acc, [key]) => ({
                        ...acc,
                        [key]: prev[key],
                    }),
                    {},
                );
                return {
                    ...prev,
                    ...partial,
                };
            });

            try {
                await Promise.all(
                    entries.map(([key, value]) =>
                        electronSettings.set(LOCAL_SETTING_STORE_KEYS[key], value),
                    ),
                );
            } catch (error) {
                setSettings((prev) => ({
                    ...prev,
                    ...previousValues,
                }));
                throw error;
            }
        },
        [],
    );

    /**
     * Update a specific setting.
     */
    const updateSetting = useCallback(
        <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
            setSettings((prev) => ({ ...prev, [key]: value }));
            if (key === "isTTSEnabled") {
                void persistLocalSettings({
                    isTTSEnabled: value as AppSettings["isTTSEnabled"],
                });
            }
        },
        [persistLocalSettings],
    );

    /**
     * Update LLM settings and sync runtime state.
     */
    const updateLLMSettings = useCallback(async (llm: LLMSettings) => {
        // Check if changed
        const prev = prevLLMRef.current;
        const changed =
            !prev ||
            prev.apiKey !== llm.apiKey ||
            prev.providerId !== llm.providerId ||
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

        await electronSettings.set("thinking_enabled", llm.thinkingEnabled);

        const persisted = await updateRuntimeLlmSettings(baseUrl, {
            apiKey: llm.apiKey,
            providerId: llm.providerId,
            baseUrl: llm.baseUrl,
            model: llm.model,
            temperature: llm.temperature,
            topP: llm.topP,
            presencePenalty: llm.presencePenalty,
            frequencyPenalty: llm.frequencyPenalty,
            historyLimit: llm.historyLimit,
            overflowStrategy: llm.overflowStrategy,
        });

        const next = {
            ...llm,
            providerId: persisted.providerId as LlmProviderId,
            apiKey: persisted.apiKey,
            baseUrl: persisted.baseUrl,
            model: persisted.model,
            temperature: persisted.temperature,
            topP: persisted.topP,
            presencePenalty: persisted.presencePenalty,
            frequencyPenalty: persisted.frequencyPenalty,
            historyLimit: persisted.historyLimit,
            overflowStrategy: persisted.overflowStrategy,
        };

        // Update local state
        setSettings((prev) => ({ ...prev, llm: next }));
        prevLLMRef.current = next;

        console.log("[useSettings] LLM settings updated");
    }, [baseUrl]);

    /**
     * Save a simple setting to the store.
     */
    const saveSetting = useCallback(
        async <K extends LocalSettingKey>(key: K, value: AppSettings[K]) => {
            await persistLocalSettings({ [key]: value } as Pick<
                AppSettings,
                K
            >);
        },
        [persistLocalSettings],
    );

    const saveGeneralSettings = useCallback(
        async (next: GeneralSettingsPatch) => {
            const partial: Partial<Pick<AppSettings, LocalSettingKey>> = {};
            if (next.userName !== undefined) {
                partial.userName = next.userName;
            }
            if (next.live2dHighDpi !== undefined) {
                partial.live2dHighDpi = next.live2dHighDpi;
            }
            if (next.backgroundImage !== undefined) {
                partial.backgroundImage = next.backgroundImage;
            }

            await persistLocalSettings(partial);
        },
        [persistLocalSettings],
    );

    return {
        settings,
        isLoaded,
        updateSetting,
        updateLLMSettings,
        saveSetting,
        saveGeneralSettings,
    };
}
