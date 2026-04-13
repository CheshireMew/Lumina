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
import { LlmSettings, LlmSettingsChangeHandler } from "./types";

interface LLMConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentLlmSettings: LlmSettings;
    onSettingsChange: LlmSettingsChangeHandler;
    activeCharacterId?: string;
}

const LLMConfigModal: FC<LLMConfigModalProps> = ({
    isOpen,
    onClose,
    currentLlmSettings,
    onSettingsChange,
    activeCharacterId = "default",
}) => {
    const { form, updateField, selectPlatform, setDeepSeekThinking, save } =
        useLlmConfigForm({
            isOpen,
            currentLlmSettings,
            onSettingsChange,
            onClose,
        });

    const { availableModels, isLoadingModels } = useAvailableLlmModels(
        isOpen,
        form.providerType,
    );

    const handleResetContext = async () => {
        if (!confirm("Clear short-term memory (Context) for this session?")) {
            return;
        }

        try {
            await clearLlmSessionContext(activeCharacterId);
            alert("Session Context Cleared!");
        } catch {
            alert("Failed to clear context");
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <ModalFrame onClose={onClose} onSave={save}>
            <ProviderModeToggle
                providerType={form.providerType}
                onChange={(providerType) =>
                    updateField("providerType", providerType)
                }
            />

            <div style={modalStyles.formBody}>
                {form.providerType === "free" ? (
                    <FreeProviderSection
                        modelName={form.modelName}
                        availableModels={availableModels}
                        isLoadingModels={isLoadingModels}
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
                        providerType={form.providerType}
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
