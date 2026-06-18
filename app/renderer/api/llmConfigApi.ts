export const listAvailableLlmModels = async (
    apiBaseUrl: string,
): Promise<string[]> => {
    const response = await fetch(`${apiBaseUrl}/settings/llm/models/list`);

    if (!response.ok) {
        throw new Error(`Failed to fetch models: ${response.status}`);
    }

    const data: unknown = await response.json();

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
    const response = await fetch(`${apiBaseUrl}/memory/context/clear`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(
            characterId
                ? { character_id: characterId }
                : {},
        ),
    });

    if (!response.ok) {
        throw new Error(`Failed to clear context: ${response.status}`);
    }
};
