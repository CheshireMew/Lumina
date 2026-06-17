export const FREE_LLM_PROVIDER_ID = "free_tier";
export const CUSTOM_LLM_PROVIDER_ID = "custom_provider";
export type LlmProviderId = typeof FREE_LLM_PROVIDER_ID | typeof CUSTOM_LLM_PROVIDER_ID;

export type OverflowStrategy = "slide" | "reset";

export interface LlmSettings {
    providerId?: LlmProviderId;
    apiKey: string;
    apiBaseUrl: string;
    modelName: string;
    temperature: number;
    thinkingEnabled: boolean;
    historyLimit?: number;
    overflowStrategy?: OverflowStrategy;
    topP?: number;
    presencePenalty?: number;
    frequencyPenalty?: number;
}

export type LlmSettingsChangeHandler = (
    apiKey: string,
    baseUrl: string,
    model: string,
    temperature: number,
    thinkingEnabled: boolean,
    historyLimit: number,
    overflowStrategy: OverflowStrategy,
    topP?: number,
    presencePenalty?: number,
    frequencyPenalty?: number,
    providerId?: LlmProviderId,
) => void;

export interface LlmConfigFormState {
    providerId: LlmProviderId;
    selectedPlatform: string;
    apiKey: string;
    baseUrl: string;
    modelName: string;
    temperature: number;
    topP: number;
    presencePenalty: number;
    frequencyPenalty: number;
    thinkingEnabled: boolean;
    historyLimit: number;
    overflowStrategy: OverflowStrategy;
}
