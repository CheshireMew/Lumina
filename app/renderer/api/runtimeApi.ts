import { requestJson } from "./client";
import type { components } from "../types/api-schema";

export type RuntimeCapabilitiesResponse = components["schemas"]["RuntimeCapabilitiesResponse"];

export const fetchRuntimeCapabilities = (
    baseUrl: string,
    signal?: AbortSignal,
) =>
    requestJson<RuntimeCapabilitiesResponse>(
        `${baseUrl}/runtime/capabilities`,
        { signal },
    );
