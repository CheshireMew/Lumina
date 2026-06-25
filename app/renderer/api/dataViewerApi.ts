import { jsonRequestOptions, requestJson } from "./client";

export interface QueryResult {
    status: string;
    result?: any[];
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

    const data = await requestJson<{ data?: any[] }>(url, { signal });
    return data.data || [];
};

export const executeQuery = async (
    apiBaseUrl: string,
    query: string,
): Promise<QueryResult> => {
    const data = await requestJson<{ result?: any[]; detail?: string }>(
        `${apiBaseUrl}/memory/inspection/query`,
        jsonRequestOptions("POST", { query }),
    );

    return {
        status: "success",
        result: data.result || [],
    };
};

export const deleteRecord = async (
    apiBaseUrl: string,
    tableName: string,
    recordId: string,
) => {
    return requestJson<{ status?: string; detail?: string }>(
        `${apiBaseUrl}/memory/inspection/record/${tableName}/${encodeURIComponent(recordId)}`,
        jsonRequestOptions("DELETE"),
    );
};

export const updateRecord = async (
    apiBaseUrl: string,
    tableName: string,
    recordId: string,
    data: Record<string, any>,
) => {
    return requestJson<{ status?: string; detail?: string }>(
        `${apiBaseUrl}/memory/inspection/record/${tableName}/${encodeURIComponent(recordId)}`,
        jsonRequestOptions("PUT", { data }),
    );
};

export const createRecord = async (
    apiBaseUrl: string,
    tableName: string,
    data: Record<string, any>,
) => {
    return requestJson<{ status?: string; detail?: string }>(
        `${apiBaseUrl}/memory/inspection/record/${tableName}/new`,
        jsonRequestOptions("POST", { data }),
    );
};

export const normalizeRecordId = (value: any): string => {
    if (value && typeof value === "object" && value.id) {
        return normalizeRecordId(value.id);
    }

    const text = String(value);
    return text.includes(":") ? text.split(":")[1] : text;
};
