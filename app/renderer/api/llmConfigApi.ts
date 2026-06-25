import { jsonRequestOptions, requestJson, requestVoid } from "./client";

export const listAvailableLlmModels = async (
    apiBaseUrl: string,
    providerId: string,
): Promise<string[]> => {
    const params = new URLSearchParams({ provider_id: providerId });
    const data: unknown = await requestJson<unknown>(
        `${apiBaseUrl}/settings/llm/models/list?${params.toString()}`,
    );

    if (Array.isArray(data)) {
        return data.filter((model): model is string => typeof model === "string");
    }

    if (
        data &&
        typeof data === "object" &&
        "models" in data &&
        Array.isArray(data.models)
    ) {
        return data.models.filter(
            (model): model is string => typeof model === "string",
        );
    }

    return [];
};

export const clearLlmSessionContext = async (
    apiBaseUrl: string,
    characterId?: string | null,
) => {
    await requestVoid(
        `${apiBaseUrl}/memory/context/clear`,
        jsonRequestOptions(
            "POST",
            characterId
                ? { character_id: characterId }
                : {},
        ),
    );
};
