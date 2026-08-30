export const parseJsonResponse = async (response: Response): Promise<unknown> => {
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

export class ApiRequestError extends Error {
    constructor(
        message: string,
        readonly code: string,
        readonly status?: number,
    ) {
        super(message);
        this.name = "ApiRequestError";
    }
}

const statusMessage = (status: number) => {
    if (status === 400) return "提交的内容有误，请检查后重试。";
    if (status === 404) return "请求的功能不存在或尚未安装。";
    if (status === 409) return "当前状态不允许执行这个操作。";
    if (status === 429) return "请求过于频繁，请稍后重试。";
    if (status >= 500) return "服务暂时不可用，请稍后重试。";
    return "操作失败，请重试。";
};

const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

const createRequestSignal = (
    externalSignal?: AbortSignal | null,
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
) => {
    const controller = new AbortController();
    const abortFromExternal = () => controller.abort(externalSignal?.reason);

    if (externalSignal?.aborted) {
        abortFromExternal();
    } else {
        externalSignal?.addEventListener("abort", abortFromExternal, { once: true });
    }

    const timeout = window.setTimeout(
        () => controller.abort(new DOMException("Request timed out", "TimeoutError")),
        timeoutMs,
    );

    return {
        signal: controller.signal,
        dispose: () => {
            window.clearTimeout(timeout);
            externalSignal?.removeEventListener("abort", abortFromExternal);
        },
    };
};

export const requestJson = async <T>(
    url: string,
    options?: RequestInit,
): Promise<T> => {
    const requestSignal = createRequestSignal(options?.signal);
    let response: Response;
    try {
        response = await fetch(url, {
            ...options,
            signal: requestSignal.signal,
        });
    } catch (error) {
        const isTimeout = error instanceof DOMException && error.name === "TimeoutError";
        throw new ApiRequestError(
            isTimeout ? "请求超时，请重试。" : "无法连接服务，请检查服务状态后重试。",
            isTimeout ? "request_timeout" : "service_unreachable",
        );
    } finally {
        requestSignal.dispose();
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        const payload = data && typeof data === "object"
            ? data as Record<string, unknown>
            : {};
        const detail = payload.detail ?? payload.message;
        const detailPayload = detail && typeof detail === "object"
            ? detail as Record<string, unknown>
            : {};
        const structuredMessage = typeof detailPayload.message === "string"
            ? detailPayload.message
            : "";
        const localizedStringDetail = typeof detail === "string"
            && /[\u3400-\u9fff]/.test(detail)
            && response.status < 500
            ? detail
            : "";
        const message = structuredMessage || localizedStringDetail || statusMessage(response.status);
        const code = typeof detailPayload.code === "string"
            ? detailPayload.code
            : `http_${response.status}`;
        throw new ApiRequestError(message, code, response.status);
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
