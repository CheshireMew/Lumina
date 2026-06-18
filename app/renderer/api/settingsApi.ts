export interface RuntimeLlmSettingsDto {
    providerId: string;
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

export const fetchRuntimeLlmSettings = async (
    baseUrl: string,
): Promise<RuntimeLlmSettingsDto> => {
    const response = await fetch(`${baseUrl}/settings/llm/runtime`);
    if (!response.ok) {
        throw new Error(`Failed to fetch LLM settings: ${response.status}`);
    }
    return response.json();
};

export const updateRuntimeLlmSettings = async (
    baseUrl: string,
    payload: RuntimeLlmSettingsDto,
): Promise<RuntimeLlmSettingsDto> => {
    const response = await fetch(`${baseUrl}/settings/llm/runtime`, {
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
