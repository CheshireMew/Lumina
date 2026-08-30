import { useEffect, useRef, useState } from "react";
import { fetchRuntimeCapabilities } from "../api/runtimeApi";
import type { components } from "../types/api-schema";

export type RuntimeCapabilitySnapshot = components["schemas"]["RuntimeCapabilitySnapshot"];
export type RuntimeCapabilityState = RuntimeCapabilitySnapshot["status"];

export const runtimeCapabilityRefreshDelay = (
    capabilities: RuntimeCapabilitySnapshot[],
) => capabilities.some((item) => item.status === "starting") ? 3000 : 60000;

export const useRuntimeCapabilities = (enabled: boolean, baseUrl: string) => {
    const [capabilities, setCapabilities] = useState<Record<string, RuntimeCapabilitySnapshot>>({});
    const signatureRef = useRef("");

    useEffect(() => {
        if (!enabled) {
            signatureRef.current = "";
            setCapabilities({});
            return;
        }

        const abortController = new AbortController();

        let nextRefresh: number | null = null;
        let refreshInFlight = false;

        const scheduleRefresh = (delayMs: number) => {
            if (nextRefresh !== null) {
                window.clearTimeout(nextRefresh);
            }
            if (!abortController.signal.aborted && document.visibilityState === "visible") {
                nextRefresh = window.setTimeout(() => void refreshCapabilities(), delayMs);
            }
        };

        const refreshCapabilities = async () => {
            if (refreshInFlight || abortController.signal.aborted) {
                return;
            }
            refreshInFlight = true;
            try {
                const payload = await fetchRuntimeCapabilities(baseUrl, abortController.signal);
                if (abortController.signal.aborted) {
                    return;
                }

                const next = payload.capabilities.reduce(
                    (acc: Record<string, RuntimeCapabilitySnapshot>, item) => {
                        acc[item.capability] = item as RuntimeCapabilitySnapshot;
                        return acc;
                    },
                    {},
                );
                const signature = JSON.stringify(next);
                if (signature !== signatureRef.current) {
                    signatureRef.current = signature;
                    setCapabilities(next);
                }

                scheduleRefresh(runtimeCapabilityRefreshDelay(payload.capabilities));
            } catch (error) {
                if (!abortController.signal.aborted) {
                    console.error("[useRuntimeCapabilities] Failed to fetch runtime capabilities:", error);
                    scheduleRefresh(10000);
                }
            } finally {
                refreshInFlight = false;
            }
        };

        const refreshWhenVisible = () => {
            if (document.visibilityState === "visible") {
                void refreshCapabilities();
            } else if (nextRefresh !== null) {
                window.clearTimeout(nextRefresh);
                nextRefresh = null;
            }
        };

        void refreshCapabilities();
        window.addEventListener("focus", refreshWhenVisible);
        document.addEventListener("visibilitychange", refreshWhenVisible);

        return () => {
            if (nextRefresh !== null) {
                window.clearTimeout(nextRefresh);
            }
            window.removeEventListener("focus", refreshWhenVisible);
            document.removeEventListener("visibilitychange", refreshWhenVisible);
            abortController.abort();
        };
    }, [enabled, baseUrl]);

    return capabilities;
};
