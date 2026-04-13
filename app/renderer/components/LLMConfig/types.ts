export type ProviderType = "free" | "custom";

export type OverflowStrategy = "slide" | "reset";

export interface LlmSettings {
    providerType?: ProviderType;
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
    providerType?: ProviderType,
) => void;

export interface LlmConfigFormState {
    providerType: ProviderType;
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
