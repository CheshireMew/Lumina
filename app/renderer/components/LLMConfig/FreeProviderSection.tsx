import { Sparkles } from "lucide-react";
import type { FC } from "react";
import {
    inputStyle,
    labelStyle,
    providerSectionStyles,
} from "./styles";

interface FreeProviderSectionProps {
    apiKey: string;
    modelName: string;
    availableModels: string[];
    isLoadingModels: boolean;
    modelLoadError: string | null;
    onApiKeyChange: (apiKey: string) => void;
    onModelNameChange: (modelName: string) => void;
}

const FreeProviderSection: FC<FreeProviderSectionProps> = ({
    apiKey,
    modelName,
    availableModels,
    isLoadingModels,
    modelLoadError,
    onApiKeyChange,
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
                Pollinations 当前要求 API 密钥。密钥只保存在这台电脑上。
            </div>

            <label htmlFor="llm-pollinations-key" style={labelStyle}>API 密钥</label>
            <input
                id="llm-pollinations-key"
                type="password"
                autoComplete="off"
                style={inputStyle}
                value={apiKey}
                onChange={(event) => onApiKeyChange(event.target.value)}
                placeholder="在 Pollinations 账户中创建密钥"
            />
            <button
                type="button"
                onClick={() => void window.app.openExternal("https://enter.pollinations.ai/")}
                style={{
                    margin: "8px 0 14px",
                    padding: 0,
                    border: 0,
                    color: "#a5b4fc",
                    background: "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                    fontSize: 12,
                }}
            >
                打开 Pollinations 获取密钥
            </button>

            <label htmlFor="llm-free-model" style={labelStyle}>模型</label>
            <select
                id="llm-free-model"
                style={inputStyle}
                value={modelName}
                onChange={(event) => onModelNameChange(event.target.value)}
                disabled={isLoadingModels || models.length === 0}
            >
                {isLoadingModels ? (
                    <option>正在读取可用模型…</option>
                ) : models.length > 0 ? (
                    models.map((model) => (
                        <option key={model} value={model}>
                            {model}
                        </option>
                    ))
                ) : (
                    <option value="">运行服务未返回可用模型</option>
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
