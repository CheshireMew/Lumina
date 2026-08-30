import { useEffect, useMemo, useState } from "react";
import {
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
    const [isSaving, setIsSaving] = useState(false);
    const [saveError, setSaveError] = useState("");

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
            historyLimit: providerId === FREE_LLM_PROVIDER_ID
                ? 5
                : currentLlmSettings.historyLimit ?? 20,
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
                modelName: PRESET_PROVIDERS[platform]?.model ?? current.modelName,
            };
        });
    };

    const selectProviderMode = (providerId: LlmConfigFormState["providerId"]) => {
        setSaveError("");
        setForm((current) => providerId === FREE_LLM_PROVIDER_ID
            ? {
                ...current,
                providerId,
                selectedPlatform: "custom",
                apiKey: current.providerId === FREE_LLM_PROVIDER_ID ? current.apiKey : "",
                baseUrl: "",
                modelName: "openai",
                historyLimit: 5,
                thinkingEnabled: false,
            }
            : {
                ...current,
                providerId,
                selectedPlatform: "deepseek",
                apiKey: "",
                baseUrl: PRESET_PROVIDERS.deepseek.baseUrl,
                modelName: PRESET_PROVIDERS.deepseek.model,
                historyLimit: Math.max(current.historyLimit, 5),
            });
    };

    const setDeepSeekThinking = (thinkingEnabled: boolean) => {
        setForm((current) => ({
            ...current,
            thinkingEnabled,
            modelName: thinkingEnabled ? "deepseek-reasoner" : "deepseek-chat",
        }));
    };

    const validationError = useMemo(() => {
        if (!form.modelName.trim()) return "请选择或填写一个模型。";
        if (form.providerId === FREE_LLM_PROVIDER_ID) {
            return form.apiKey.trim() ? "" : "Pollinations 需要填写 API 密钥。";
        }
        let url: URL;
        try {
            url = new URL(form.baseUrl);
        } catch {
            return "API 地址必须是有效的 HTTP 或 HTTPS 地址。";
        }
        if (!["http:", "https:"].includes(url.protocol)) {
            return "API 地址必须使用 HTTP 或 HTTPS。";
        }
        const isLocal = ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
        if (!isLocal && !form.apiKey.trim()) return "远程自定义服务需要填写 API 密钥。";
        return "";
    }, [form.apiKey, form.baseUrl, form.modelName, form.providerId]);

    const save = async () => {
        if (validationError) {
            setSaveError(validationError);
            return;
        }
        const finalModel = normalizeModelForSave(
            form.providerId,
            form.modelName,
        );

        setIsSaving(true);
        setSaveError("");
        try {
            await onSettingsChange(
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
        } catch (error) {
            console.error("[LLMConfig] Failed to save settings", error);
            setSaveError(error instanceof Error ? error.message : "模型设置保存失败。 ");
        } finally {
            setIsSaving(false);
        }
    };

    return {
        form,
        isSaving,
        saveError,
        validationError,
        updateField,
        selectPlatform,
        selectProviderMode,
        setDeepSeekThinking,
        save,
    };
};
