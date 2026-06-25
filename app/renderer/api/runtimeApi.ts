import { requestJson } from "./client";

export const fetchRuntimeCapabilities = (
    baseUrl: string,
    signal?: AbortSignal,
) =>
    requestJson<{ capabilities?: Array<{ capability: string; status: string; [key: string]: any }> }>(
        `${baseUrl}/runtime/capabilities`,
        { signal },
    );
