import { useEffect } from "react";
import type { FC } from "react";
import { clearLlmSessionContext } from "../../api/llmConfigApi";
import ContextPolicySection from "./ContextPolicySection";
import CustomProviderSection from "./CustomProviderSection";
import FreeProviderSection from "./FreeProviderSection";
import GenerationParamsSection from "./GenerationParamsSection";
import ModalFrame from "./ModalFrame";
import ProviderModeToggle from "./ProviderModeToggle";
import { parameterStyles, modalStyles } from "./styles";
import { useAvailableLlmModels } from "./useAvailableLlmModels";
import { useLlmConfigForm } from "./useLlmConfigForm";
import {
    FREE_LLM_PROVIDER_ID,
    LlmSettings,
    LlmSettingsChangeHandler,
} from "./types";

interface LLMConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentLlmSettings: LlmSettings;
    onSettingsChange: LlmSettingsChangeHandler;
    activeCharacterId?: string | null;
    apiBaseUrl: string;
}

const LLMConfigModal: FC<LLMConfigModalProps> = ({
    isOpen,
    onClose,
    currentLlmSettings,
    onSettingsChange,
    activeCharacterId,
    apiBaseUrl,
}) => {
    const { form, isSaving, saveError, validationError, updateField, selectPlatform, selectProviderMode, setDeepSeekThinking, save } =
        useLlmConfigForm({
            isOpen,
            currentLlmSettings,
            onSettingsChange,
            onClose,
        });

    const { availableModels, isLoadingModels, modelLoadError } = useAvailableLlmModels(
        isOpen,
        form.providerId,
        apiBaseUrl,
    );

    useEffect(() => {
        if (form.providerId === FREE_LLM_PROVIDER_ID && !form.modelName && availableModels.length > 0) {
            updateField("modelName", availableModels[0]);
        }
    }, [availableModels, form.modelName, form.providerId, updateField]);

    const handleResetContext = async () => {
        if (!confirm("确定清除本次会话的短期上下文吗？")) {
            return;
        }

        try {
            await clearLlmSessionContext(apiBaseUrl, activeCharacterId);
            alert("本次会话的上下文已清除");
        } catch {
            alert("清除上下文失败");
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <ModalFrame onClose={onClose} onSave={save} isSaving={isSaving} saveError={saveError || validationError} saveDisabled={Boolean(validationError)}>
            <ProviderModeToggle
                providerId={form.providerId}
                onChange={selectProviderMode}
            />

            <div style={modalStyles.formBody}>
                {form.providerId === FREE_LLM_PROVIDER_ID ? (
                    <FreeProviderSection
                        apiKey={form.apiKey}
                        modelName={form.modelName}
                        availableModels={availableModels}
                        isLoadingModels={isLoadingModels}
                        modelLoadError={modelLoadError}
                        onApiKeyChange={(apiKey) => updateField("apiKey", apiKey)}
                        onModelNameChange={(modelName) =>
                            updateField("modelName", modelName)
                        }
                    />
                ) : (
                    <CustomProviderSection
                        selectedPlatform={form.selectedPlatform}
                        apiKey={form.apiKey}
                        baseUrl={form.baseUrl}
                        modelName={form.modelName}
                        thinkingEnabled={form.thinkingEnabled}
                        onPlatformChange={selectPlatform}
                        onApiKeyChange={(apiKey) =>
                            updateField("apiKey", apiKey)
                        }
                        onBaseUrlChange={(baseUrl) =>
                            updateField("baseUrl", baseUrl)
                        }
                        onModelNameChange={(modelName) =>
                            updateField("modelName", modelName)
                        }
                        onThinkingEnabledChange={setDeepSeekThinking}
                    />
                )}

                <div style={parameterStyles.section}>
                    <GenerationParamsSection
                        temperature={form.temperature}
                        topP={form.topP}
                        presencePenalty={form.presencePenalty}
                        frequencyPenalty={form.frequencyPenalty}
                        onTemperatureChange={(temperature) =>
                            updateField("temperature", temperature)
                        }
                        onTopPChange={(topP) => updateField("topP", topP)}
                        onPresencePenaltyChange={(presencePenalty) =>
                            updateField("presencePenalty", presencePenalty)
                        }
                        onFrequencyPenaltyChange={(frequencyPenalty) =>
                            updateField("frequencyPenalty", frequencyPenalty)
                        }
                    />

                    <ContextPolicySection
                        providerId={form.providerId}
                        historyLimit={form.historyLimit}
                        overflowStrategy={form.overflowStrategy}
                        onHistoryLimitChange={(historyLimit) =>
                            updateField("historyLimit", historyLimit)
                        }
                        onOverflowStrategyChange={(overflowStrategy) =>
                            updateField("overflowStrategy", overflowStrategy)
                        }
                        onResetContext={handleResetContext}
                    />
                </div>
            </div>
        </ModalFrame>
    );
};

export default LLMConfigModal;
