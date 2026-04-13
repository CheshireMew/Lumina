import { API_CONFIG } from "../config";

export interface RuntimeLlmSettingsDto {
    providerType: "free" | "custom";
    apiKey: string;
    baseUrl: string;
    model: string;
    temperature: number;
    topP?: number;
    presencePenalty?: number;
    frequencyPenalty?: number;
    historyLimit: number;
    overflowStrategy: "slide" | "reset";
}

export const fetchRuntimeLlmSettings = async (): Promise<RuntimeLlmSettingsDto> => {
    const response = await fetch(`${API_CONFIG.BASE_URL}/config/llm`);
    if (!response.ok) {
        throw new Error(`Failed to fetch LLM settings: ${response.status}`);
    }
    return response.json();
};

export const updateRuntimeLlmSettings = async (
    payload: RuntimeLlmSettingsDto,
): Promise<RuntimeLlmSettingsDto> => {
    const response = await fetch(`${API_CONFIG.BASE_URL}/config/llm`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error(`Failed to update LLM settings: ${response.status}`);
    }

    return response.json();
};
