import { Cpu, Wand2 } from "lucide-react";
import type { FC } from "react";
import { providerToggleStyles } from "./styles";
import {
    CUSTOM_LLM_PROVIDER_ID,
    FREE_LLM_PROVIDER_ID,
    LlmProviderId,
} from "./types";

interface ProviderModeToggleProps {
    providerId: LlmProviderId;
    onChange: (providerId: LlmProviderId) => void;
}

const providerModes: Array<{
    id: LlmProviderId;
    icon: typeof Wand2;
    label: string;
}> = [
    { id: FREE_LLM_PROVIDER_ID, icon: Wand2, label: "Free (Magic)" },
    { id: CUSTOM_LLM_PROVIDER_ID, icon: Cpu, label: "Custom (Pro)" },
];

const ProviderModeToggle: FC<ProviderModeToggleProps> = ({
    providerId,
    onChange,
}) => (
    <div style={providerToggleStyles.container}>
        {providerModes.map((type) => {
            const Icon = type.icon;

            return (
                <button
                    key={type.id}
                    onClick={() => onChange(type.id)}
                    style={providerToggleStyles.button(providerId === type.id)}
                >
                    <Icon size={16} strokeWidth={2.5} /> {type.label}
                </button>
            );
        })}
    </div>
);

export default ProviderModeToggle;
