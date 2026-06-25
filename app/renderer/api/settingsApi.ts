import { jsonRequestOptions, requestJson } from "./client";

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
    return requestJson<RuntimeLlmSettingsDto>(`${baseUrl}/settings/llm/runtime`);
};

export const updateRuntimeLlmSettings = async (
    baseUrl: string,
    payload: RuntimeLlmSettingsDto,
): Promise<RuntimeLlmSettingsDto> => {
    return requestJson<RuntimeLlmSettingsDto>(
        `${baseUrl}/settings/llm/runtime`,
        jsonRequestOptions("PUT", payload),
    );
};
