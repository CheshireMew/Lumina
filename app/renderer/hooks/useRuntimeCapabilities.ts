import { useEffect, useState } from "react";
import { fetchRuntimeCapabilities } from "../api/runtimeApi";

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

        const refreshCapabilities = () => {
            void fetchRuntimeCapabilities(baseUrl, abortController.signal)
                .then((payload) => {
                    if (abortController.signal.aborted || !Array.isArray(payload.capabilities)) {
                        return;
                    }

                    const next = payload.capabilities.reduce(
                        (acc: Record<string, RuntimeCapabilitySnapshot>, item) => {
                            acc[item.capability] = item as RuntimeCapabilitySnapshot;
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
        };

        refreshCapabilities();
        const interval = window.setInterval(refreshCapabilities, 3000);

        return () => {
            window.clearInterval(interval);
            abortController.abort();
        };
    }, [enabled, baseUrl]);

    return capabilities;
};
