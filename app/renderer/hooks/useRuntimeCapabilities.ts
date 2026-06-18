import { useEffect, useState } from "react";

export type RuntimeCapabilityState = "ready" | "offline" | "unavailable" | "failed";

export interface RuntimeCapabilitySnapshot {
    capability: string;
    status: RuntimeCapabilityState;
    worker_online?: boolean;
    selected_provider?: string | null;
    current_provider?: string | null;
    last_error?: string | null;
}

export const useRuntimeCapabilities = (enabled: boolean, baseUrl: string) => {
    const [capabilities, setCapabilities] = useState<Record<string, RuntimeCapabilitySnapshot>>({});

    useEffect(() => {
        if (!enabled) {
            setCapabilities({});
            return;
        }

        const abortController = new AbortController();

        void fetch(`${baseUrl}/runtime/capabilities`, {
            signal: abortController.signal,
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((payload) => {
                if (abortController.signal.aborted || !Array.isArray(payload.capabilities)) {
                    return;
                }

                const next = payload.capabilities.reduce(
                    (acc: Record<string, RuntimeCapabilitySnapshot>, item: RuntimeCapabilitySnapshot) => {
                        acc[item.capability] = item;
                        return acc;
                    },
                    {},
                );
                setCapabilities(next);
            })
            .catch((error) => {
                if (abortController.signal.aborted) {
                    return;
                }
                console.error("[useRuntimeCapabilities] Failed to fetch runtime capabilities:", error);
            });

        return () => {
            abortController.abort();
        };
    }, [enabled, baseUrl]);

    return capabilities;
};
