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
    modelLoadError: string | null;
    onModelNameChange: (modelName: string) => void;
}

const FreeProviderSection: FC<FreeProviderSectionProps> = ({
    modelName,
    availableModels,
    isLoadingModels,
    modelLoadError,
    onModelNameChange,
}) => {
    const models = availableModels.includes(modelName) || !modelName
        ? availableModels
        : [modelName, ...availableModels];

    return (
        <div style={providerSectionStyles.freeCard}>
            <div style={providerSectionStyles.freeTitle}>
                <Sparkles size={16} /> Pollinations
            </div>
            <div style={providerSectionStyles.freeDescription}>
                Anonymous Pollinations text API. No API key required.
            </div>

            <label style={labelStyle}>Model</label>
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
                            {model}
                        </option>
                    ))
                ) : (
                    <option value="">No models reported by runtime</option>
                )}
            </select>
            {modelLoadError && (
                <div style={{ marginTop: 8, fontSize: 12, color: "#fca5a5" }}>
                    {modelLoadError}
                </div>
            )}
        </div>
    );
};

export default FreeProviderSection;
