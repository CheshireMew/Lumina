import { Sparkles } from "lucide-react";
import type { FC } from "react";
import {
    inputStyle,
    labelStyle,
    providerSectionStyles,
} from "./styles";

interface FreeProviderSectionProps {
    modelName: string;
    availableModels: string[];
    isLoadingModels: boolean;
    onModelNameChange: (modelName: string) => void;
}

const FreeProviderSection: FC<FreeProviderSectionProps> = ({
    modelName,
    availableModels,
    isLoadingModels,
    onModelNameChange,
}) => {
    const models = availableModels.includes(modelName) || !modelName
        ? availableModels
        : [modelName, ...availableModels];

    return (
        <div style={providerSectionStyles.freeCard}>
            <div style={providerSectionStyles.freeTitle}>
                <Sparkles size={16} /> Pollinations Magic
            </div>
            <div style={providerSectionStyles.freeDescription}>
                Privacy-focused proxy for OpenAI, Claude, and Llama. <br />
                <strong>No API Key required. Unlimited usage.</strong>
            </div>

            <label style={labelStyle}>Select Persona</label>
            <select
                style={inputStyle}
                value={modelName}
                onChange={(event) => onModelNameChange(event.target.value)}
                disabled={isLoadingModels || models.length === 0}
            >
                {isLoadingModels ? (
                    <option>Loading available models...</option>
                ) : models.length > 0 ? (
                    models.map((model) => (
                        <option key={model} value={model}>
                            {model.toUpperCase()}
                        </option>
                    ))
                ) : (
                    <option value="">No models reported by runtime</option>
                )}
            </select>
        </div>
    );
};

export default FreeProviderSection;
