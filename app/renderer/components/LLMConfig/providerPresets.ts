import { FREE_LLM_PROVIDER_ID, LlmProviderId } from "./types";

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

export const isFreeProvider = (providerId: string) =>
    providerId === FREE_LLM_PROVIDER_ID;

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
    providerId: LlmProviderId,
    modelName: string,
) => {
    if (isFreeProvider(providerId)) {
        return modelName || FREE_PROVIDER_DEFAULT_MODEL;
    }

    return modelName;
};

export const normalizeOverflowStrategy = (strategy: unknown) =>
    strategy === "slide" || strategy === "reset" ? strategy : "reset";
