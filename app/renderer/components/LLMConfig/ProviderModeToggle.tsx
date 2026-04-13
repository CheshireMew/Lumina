import { Cpu, Wand2 } from "lucide-react";
import type { FC } from "react";
import { providerToggleStyles } from "./styles";
import { ProviderType } from "./types";

interface ProviderModeToggleProps {
    providerType: ProviderType;
    onChange: (providerType: ProviderType) => void;
}

const providerModes: Array<{
    id: ProviderType;
    icon: typeof Wand2;
    label: string;
}> = [
    { id: "free", icon: Wand2, label: "Free (Magic)" },
    { id: "custom", icon: Cpu, label: "Custom (Pro)" },
];

const ProviderModeToggle: FC<ProviderModeToggleProps> = ({
    providerType,
    onChange,
}) => (
    <div style={providerToggleStyles.container}>
        {providerModes.map((type) => {
            const Icon = type.icon;

            return (
                <button
                    key={type.id}
                    onClick={() => onChange(type.id)}
                    style={providerToggleStyles.button(providerType === type.id)}
                >
                    <Icon size={16} strokeWidth={2.5} /> {type.label}
                </button>
            );
        })}
    </div>
);

export default ProviderModeToggle;
