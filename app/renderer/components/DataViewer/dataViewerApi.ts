import { API_CONFIG } from "../../config";
import type { QueryResult } from "./types";

const parseJsonResponse = async (response: Response): Promise<any> => {
    const text = await response.text();
    if (!text) {
        return {};
    }

    try {
        return JSON.parse(text);
    } catch {
        return { detail: text || response.statusText };
    }
};

const requestJson = async <T>(
    url: string,
    options?: RequestInit,
): Promise<T> => {
    const response = await fetch(url, options);
    const data = await parseJsonResponse(response);

    if (!response.ok) {
        throw new Error(data.detail || response.statusText || "Request failed");
    }

    return data as T;
};

export const loadTables = async (signal?: AbortSignal) => {
    const data = await requestJson<{ tables?: Array<{ name: string; info: string }> }>(
        `${API_CONFIG.BASE_URL}/admin/tables`,
        { signal },
    );
    return data.tables || [];
};

export const loadTableRows = async (
    tableName: string,
    activeCharacterId: string | null | undefined,
    signal?: AbortSignal,
) => {
    let url = `${API_CONFIG.BASE_URL}/admin/table/${tableName}?limit=50`;
    if (
        activeCharacterId &&
        (tableName === "conversation_log" || tableName === "episodic_memory")
    ) {
        url += `&character_id=${activeCharacterId}`;
    }

    const data = await requestJson<{ data?: any[] }>(url, { signal });
    return data.data || [];
};

export const loadGraphData = async (
    activeCharacterId: string | null | undefined,
    signal?: AbortSignal,
) => {
    const data = await requestJson<{
        status?: string;
        graph?: { nodes: any[]; edges: any[] };
    }>(
        `${API_CONFIG.BASE_URL}/debug/brain_dump?character_id=${
            activeCharacterId || "hiyori"
        }`,
        { signal },
    );

    return data.status === "success" ? data.graph || null : null;
};

export const executeQuery = async (query: string): Promise<QueryResult> => {
    const data = await requestJson<{ result?: any[]; detail?: string }>(
        `${API_CONFIG.BASE_URL}/admin/query`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        },
    );

    return {
        status: "success",
        result: data.result || [],
    };
};

export const deleteRecord = async (tableName: string, recordId: string) => {
    return requestJson<{ status?: string; detail?: string }>(
        `${API_CONFIG.BASE_URL}/admin/record/${tableName}/${encodeURIComponent(recordId)}`,
        {
            method: "DELETE",
        },
    );
};

export const updateRecord = async (
    tableName: string,
    recordId: string,
    data: Record<string, any>,
) => {
    return requestJson<{ status?: string; detail?: string }>(
        `${API_CONFIG.BASE_URL}/admin/record/${tableName}/${encodeURIComponent(recordId)}`,
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data }),
        },
    );
};

export const createRecord = async (
    tableName: string,
    data: Record<string, any>,
) => {
    return requestJson<{ status?: string; detail?: string }>(
        `${API_CONFIG.BASE_URL}/admin/record/${tableName}/new`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data }),
        },
    );
};

export const normalizeRecordId = (value: any): string => {
    if (value && typeof value === "object" && value.id) {
        return normalizeRecordId(value.id);
    }

    const text = String(value);
    return text.includes(":") ? text.split(":")[1] : text;
};

