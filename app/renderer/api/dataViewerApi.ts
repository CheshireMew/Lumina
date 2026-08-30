import { jsonRequestOptions, requestJson } from "./client";

export interface QueryResult {
    status: string;
    result?: Array<Record<string, unknown>>;
    error?: string;
}

export const loadTables = async (apiBaseUrl: string, signal?: AbortSignal) => {
    const data = await requestJson<{ tables?: Array<{ name: string; info: string }> }>(
        `${apiBaseUrl}/memory/inspection/tables`,
        { signal },
    );
    return data.tables || [];
};

export const loadTableRows = async (
    apiBaseUrl: string,
    tableName: string,
    activeCharacterId: string | null | undefined,
    signal?: AbortSignal,
) => {
    let url = `${apiBaseUrl}/memory/inspection/table/${tableName}?limit=50`;
    if (
        activeCharacterId &&
        (tableName === "conversation_turns" || tableName === "memory_items")
    ) {
        url += `&character_id=${activeCharacterId}`;
    }

    const data = await requestJson<{ data?: Array<Record<string, unknown>> }>(url, { signal });
    return data.data || [];
};

export const executeQuery = async (
    apiBaseUrl: string,
    query: string,
): Promise<QueryResult> => {
    const data = await requestJson<{ result?: Array<Record<string, unknown>>; detail?: string }>(
        `${apiBaseUrl}/memory/inspection/query`,
        jsonRequestOptions("POST", { query }),
    );

    return {
        status: "success",
        result: data.result || [],
    };
};
