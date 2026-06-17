import { useEffect, useState } from "react";
import {
    getDefaultModelForProvider,
    identifyPresetProvider,
    normalizeModelForSave,
    normalizeOverflowStrategy,
    PRESET_PROVIDERS,
} from "./providerPresets";
import {
    FREE_LLM_PROVIDER_ID,
    LlmConfigFormState,
    LlmSettings,
    LlmSettingsChangeHandler,
} from "./types";

interface UseLlmConfigFormArgs {
    isOpen: boolean;
    currentLlmSettings: LlmSettings;
    onSettingsChange: LlmSettingsChangeHandler;
    onClose: () => void;
}

const initialFormState: LlmConfigFormState = {
    providerId: FREE_LLM_PROVIDER_ID,
    selectedPlatform: "custom",
    apiKey: "",
    baseUrl: "",
    modelName: "",
    temperature: 0.7,
    topP: 1.0,
    presencePenalty: 0.0,
    frequencyPenalty: 0.0,
    thinkingEnabled: false,
    historyLimit: 20,
    overflowStrategy: "reset",
};

export const useLlmConfigForm = ({
    isOpen,
    currentLlmSettings,
    onSettingsChange,
    onClose,
}: UseLlmConfigFormArgs) => {
    const [form, setForm] = useState<LlmConfigFormState>(initialFormState);

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        const providerId = currentLlmSettings.providerId ?? FREE_LLM_PROVIDER_ID;

        setForm({
            providerId,
            selectedPlatform:
                providerId === FREE_LLM_PROVIDER_ID
                    ? "custom"
                    : identifyPresetProvider(currentLlmSettings.apiBaseUrl),
            apiKey: currentLlmSettings.apiKey,
            baseUrl: currentLlmSettings.apiBaseUrl,
            modelName: currentLlmSettings.modelName,
            temperature: currentLlmSettings.temperature,
            topP: currentLlmSettings.topP ?? 1.0,
            presencePenalty: currentLlmSettings.presencePenalty ?? 0.0,
            frequencyPenalty: currentLlmSettings.frequencyPenalty ?? 0.0,
            thinkingEnabled: currentLlmSettings.thinkingEnabled,
            historyLimit: currentLlmSettings.historyLimit ?? 20,
            overflowStrategy: normalizeOverflowStrategy(
                currentLlmSettings.overflowStrategy,
            ),
        });
    }, [isOpen, currentLlmSettings]);

    const updateField = <K extends keyof LlmConfigFormState>(
        key: K,
        value: LlmConfigFormState[K],
    ) => {
        setForm((current) => ({
            ...current,
            [key]: value,
        }));
    };

    const selectPlatform = (platform: string) => {
        setForm((current) => {
            if (platform === "custom") {
                return {
                    ...current,
                    selectedPlatform: platform,
                };
            }

            return {
                ...current,
                selectedPlatform: platform,
                baseUrl: PRESET_PROVIDERS[platform]?.baseUrl ?? "",
                modelName: getDefaultModelForProvider(
                    platform,
                    current.thinkingEnabled,
                ),
            };
        });
    };

    const setDeepSeekThinking = (thinkingEnabled: boolean) => {
        setForm((current) => ({
            ...current,
            thinkingEnabled,
            modelName:
                current.selectedPlatform === "deepseek"
                    ? getDefaultModelForProvider("deepseek", thinkingEnabled)
                    : current.modelName,
        }));
    };

    const save = () => {
        const finalModel = normalizeModelForSave(
            form.providerId,
            form.modelName,
        );

        onSettingsChange(
            form.apiKey,
            form.baseUrl,
            finalModel,
            form.temperature,
            form.thinkingEnabled,
            form.historyLimit,
            form.overflowStrategy,
            form.topP,
            form.presencePenalty,
            form.frequencyPenalty,
            form.providerId,
        );
        onClose();
    };

    return {
        form,
        updateField,
        selectPlatform,
        setDeepSeekThinking,
        save,
    };
};
