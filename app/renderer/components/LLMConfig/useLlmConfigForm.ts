import { useEffect, useState } from "react";
import {
    getDefaultModelForProvider,
    getProviderTypeFromBaseUrl,
    identifyPresetProvider,
    normalizeBaseUrlForSave,
    normalizeModelForSave,
    normalizeOverflowStrategy,
    PRESET_PROVIDERS,
} from "./providerPresets";
import {
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
    providerType: "free",
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

        const providerType =
            currentLlmSettings.providerType ??
            getProviderTypeFromBaseUrl(currentLlmSettings.apiBaseUrl);

        setForm({
            providerType,
            selectedPlatform:
                providerType === "free"
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
        const finalBaseUrl = normalizeBaseUrlForSave(
            form.providerType,
            form.baseUrl,
        );
        const finalModel = normalizeModelForSave(
            form.providerType,
            form.modelName,
        );

        onSettingsChange(
            form.apiKey,
            finalBaseUrl,
            finalModel,
            form.temperature,
            form.thinkingEnabled,
            form.historyLimit,
            form.overflowStrategy,
            form.topP,
            form.presencePenalty,
            form.frequencyPenalty,
            form.providerType,
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
