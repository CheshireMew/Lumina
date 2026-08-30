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
            <label htmlFor="llm-platform" style={labelStyle}>服务平台</label>
            <div style={providerSectionStyles.selectWrapper}>
                <select
                    id="llm-platform"
                    style={selectStyle}
                    value={selectedPlatform}
                    onChange={(event) => onPlatformChange(event.target.value)}
                >
                    <option value="deepseek">🐋 DeepSeek（推荐）</option>
                    <option value="openai">🤖 OpenAI</option>
                    <option value="google">🌟 Google Gemini</option>
                    <option value="anthropic">🧠 Anthropic Claude</option>
                    <option value="siliconflow">⚡ SiliconFlow</option>
                    <option value="custom">🛠️ 自定义 / 本地服务</option>
                </select>
                <div style={providerSectionStyles.selectIcon}>
                    <Zap size={16} />
                </div>
            </div>
        </div>

        {selectedPlatform === "custom" && (
            <div style={providerSectionStyles.customEndpoint}>
                <label htmlFor="llm-base-url" style={labelStyle}>API 地址</label>
                <input
                    id="llm-base-url"
                    style={inputStyle}
                    value={baseUrl}
                    onChange={(event) => onBaseUrlChange(event.target.value)}
                    placeholder="https://api.example.com/v1"
                />
            </div>
        )}

        <div>
            <label htmlFor="llm-api-key" style={labelStyle}>API 密钥</label>
            <input
                id="llm-api-key"
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
                                ? "DeepSeek 推理模型"
                                : "DeepSeek 对话模型"}
                        </div>
                        <div style={providerSectionStyles.deepSeekHint}>
                            {thinkingEnabled
                                ? "启用更深入的推理，响应时间通常更长。"
                                : "使用标准对话模式，响应更快。"}
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
                <label htmlFor="llm-model-id" style={labelStyle}>模型 ID</label>
                <input
                    id="llm-model-id"
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
