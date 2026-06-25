export const parseJsonResponse = async (response: Response): Promise<any> => {
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

export const requestJson = async <T>(
    url: string,
    options?: RequestInit,
): Promise<T> => {
    const response = await fetch(url, options);
    const data = await parseJsonResponse(response);

    if (!response.ok) {
        throw new Error(data.detail || data.message || response.statusText || "Request failed");
    }

    return data as T;
};

export const requestVoid = async (
    url: string,
    options?: RequestInit,
): Promise<void> => {
    await requestJson(url, options);
};

export const jsonRequestOptions = (
    method: "POST" | "PUT" | "PATCH" | "DELETE",
    body?: unknown,
): RequestInit => ({
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
});
