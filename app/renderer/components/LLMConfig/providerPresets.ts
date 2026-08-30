import { FREE_LLM_PROVIDER_ID, LlmProviderId } from "./types";

export interface ProviderPreset {
    baseUrl: string;
    model: string;
}

export const PRESET_PROVIDERS: Record<string, ProviderPreset> = {
    deepseek: {
        baseUrl: "https://api.deepseek.com/v1",
        model: "deepseek-chat",
    },
    openai: {
        baseUrl: "https://api.openai.com/v1",
        model: "gpt-4o-mini",
    },
    anthropic: {
        baseUrl: "https://api.anthropic.com/v1",
        model: "claude-3-5-sonnet-latest",
    },
    google: {
        baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
        model: "gemini-2.0-flash",
    },
    siliconflow: {
        baseUrl: "https://api.siliconflow.cn/v1",
        model: "deepseek-ai/DeepSeek-V3",
    },
    custom: {
        baseUrl: "",
        model: "",
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

export const normalizeModelForSave = (
    providerId: LlmProviderId,
    modelName: string,
) => {
    return modelName;
};

export const normalizeOverflowStrategy = (strategy: unknown) =>
    strategy === "slide" || strategy === "reset" ? strategy : "reset";
