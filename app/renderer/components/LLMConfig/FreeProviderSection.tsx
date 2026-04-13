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
}) => (
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
        >
            {isLoadingModels ? (
                <option>Loading available models...</option>
            ) : availableModels.length > 0 ? (
                availableModels.map((model) => (
                    <option key={model} value={model}>
                        {model.toUpperCase()}
                    </option>
                ))
            ) : (
                <option value="gpt-4o-mini">Default (GPT-4o Mini)</option>
            )}
        </select>
    </div>
);

export default FreeProviderSection;
