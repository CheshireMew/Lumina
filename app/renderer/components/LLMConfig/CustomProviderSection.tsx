import { Zap } from "lucide-react";
import type { CSSProperties, FC } from "react";
import {
    inputStyle,
    labelStyle,
    providerSectionStyles,
} from "./styles";

interface CustomProviderSectionProps {
    selectedPlatform: string;
    apiKey: string;
    baseUrl: string;
    modelName: string;
    thinkingEnabled: boolean;
    onPlatformChange: (platform: string) => void;
    onApiKeyChange: (apiKey: string) => void;
    onBaseUrlChange: (baseUrl: string) => void;
    onModelNameChange: (modelName: string) => void;
    onThinkingEnabledChange: (thinkingEnabled: boolean) => void;
}

const selectStyle: CSSProperties = {
    ...inputStyle,
    appearance: "none",
};

const CustomProviderSection: FC<CustomProviderSectionProps> = ({
    selectedPlatform,
    apiKey,
    baseUrl,
    modelName,
    thinkingEnabled,
    onPlatformChange,
    onApiKeyChange,
    onBaseUrlChange,
    onModelNameChange,
    onThinkingEnabledChange,
}) => (
    <>
        <div>
            <label style={labelStyle}>Provider Platform</label>
            <div style={providerSectionStyles.selectWrapper}>
                <select
                    style={selectStyle}
                    value={selectedPlatform}
                    onChange={(event) => onPlatformChange(event.target.value)}
                >
                    <option value="deepseek">🐋 DeepSeek (Recommended)</option>
                    <option value="openai">🤖 OpenAI</option>
                    <option value="google">🌟 Google Gemini</option>
                    <option value="anthropic">🧠 Anthropic Claude</option>
                    <option value="siliconflow">⚡ SiliconFlow</option>
                    <option value="custom">🛠️ Custom / Local</option>
                </select>
                <div style={providerSectionStyles.selectIcon}>
                    <Zap size={16} />
                </div>
            </div>
        </div>

        {selectedPlatform === "custom" && (
            <div style={providerSectionStyles.customEndpoint}>
                <label style={labelStyle}>API Endpoint</label>
                <input
                    style={inputStyle}
                    value={baseUrl}
                    onChange={(event) => onBaseUrlChange(event.target.value)}
                    placeholder="https://api.example.com/v1"
                />
            </div>
        )}

        <div>
            <label style={labelStyle}>Secret Key</label>
            <input
                type="password"
                style={inputStyle}
                value={apiKey}
                onChange={(event) => onApiKeyChange(event.target.value)}
                placeholder="sk-..."
            />
        </div>

        {selectedPlatform === "deepseek" ? (
            <div style={providerSectionStyles.deepSeekCard}>
                <div style={providerSectionStyles.deepSeekRow}>
                    <div>
                        <div style={providerSectionStyles.deepSeekTitle}>
                            {thinkingEnabled
                                ? "DeepSeek R1 (Reasoner)"
                                : "DeepSeek V3 (Chat)"}
                        </div>
                        <div style={providerSectionStyles.deepSeekHint}>
                            {thinkingEnabled
                                ? "Uses CoT reasoning. Slower but smarter."
                                : "Standard ultra-fast chat model."}
                        </div>
                    </div>
                    <label className="switch">
                        <input
                            type="checkbox"
                            checked={thinkingEnabled}
                            onChange={(event) =>
                                onThinkingEnabledChange(event.target.checked)
                            }
                        />
                        <span className="slider round"></span>
                    </label>
                </div>
            </div>
        ) : (
            <div>
                <label style={labelStyle}>Model ID</label>
                <input
                    style={inputStyle}
                    value={modelName}
                    onChange={(event) => onModelNameChange(event.target.value)}
                    placeholder="gpt-4o"
                />
            </div>
        )}
    </>
);

export default CustomProviderSection;
