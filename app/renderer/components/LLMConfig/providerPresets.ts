import { ProviderType } from "./types";

export interface ProviderPreset {
    baseUrl: string;
    defaultModel: string;
}

export const FREE_PROVIDER_DEFAULT_MODEL = "gpt-4o-mini";

export const PRESET_PROVIDERS: Record<string, ProviderPreset> = {
    deepseek: {
        baseUrl: "https://api.deepseek.com/v1",
        defaultModel: "deepseek-chat",
    },
    openai: {
        baseUrl: "https://api.openai.com/v1",
        defaultModel: "gpt-4o",
    },
    anthropic: {
        baseUrl: "https://api.anthropic.com/v1",
        defaultModel: "claude-3-5-sonnet-20240620",
    },
    google: {
        baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
        defaultModel: "gemini-1.5-flash",
    },
    siliconflow: {
        baseUrl: "https://api.siliconflow.cn/v1",
        defaultModel: "deepseek-ai/DeepSeek-V3",
    },
    custom: {
        baseUrl: "",
        defaultModel: "",
    },
};

const normalizeUrl = (url: string) => url.trim().replace(/\/+$/, "");

export const getFreeProviderBaseUrl = () => "";

export const isFreeProviderUrl = (baseUrl: string) => {
    const url = normalizeUrl(baseUrl);

    return (
        !url ||
        url.includes("localhost:8010") ||
        url.includes("127.0.0.1:8010")
    );
};

export const getProviderTypeFromBaseUrl = (baseUrl: string): ProviderType =>
    isFreeProviderUrl(baseUrl) ? "free" : "custom";

export const identifyPresetProvider = (baseUrl: string) => {
    const url = normalizeUrl(baseUrl);

    if (url.includes("deepseek")) {
        return "deepseek";
    }

    for (const [key, preset] of Object.entries(PRESET_PROVIDERS)) {
        const presetUrl = normalizeUrl(preset.baseUrl);
        if (presetUrl && url.includes(presetUrl)) {
            return key;
        }
    }

    return "custom";
};

export const getDefaultModelForProvider = (
    platform: string,
    thinkingEnabled: boolean,
) => {
    if (platform === "deepseek") {
        return thinkingEnabled ? "deepseek-reasoner" : "deepseek-chat";
    }

    return PRESET_PROVIDERS[platform]?.defaultModel ?? "";
};

export const normalizeModelForSave = (
    providerType: ProviderType,
    modelName: string,
) => {
    if (providerType === "free") {
        return modelName || FREE_PROVIDER_DEFAULT_MODEL;
    }

    return modelName;
};

export const normalizeBaseUrlForSave = (
    providerType: ProviderType,
    baseUrl: string,
) => {
    if (providerType === "free") {
        return getFreeProviderBaseUrl();
    }

    return baseUrl;
};

export const normalizeOverflowStrategy = (strategy: unknown) =>
    strategy === "slide" || strategy === "reset" ? strategy : "reset";
