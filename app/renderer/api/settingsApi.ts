import { jsonRequestOptions, requestJson } from "./client";
import type { components } from "../types/api-schema";

type GeneratedRuntimeLlmSettings = components["schemas"]["RuntimeLlmSettings"];
export type RuntimeLlmSettingsDto = Omit<
    GeneratedRuntimeLlmSettings,
    "overflowStrategy"
> & {
    overflowStrategy: "slide" | "reset";
};

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
