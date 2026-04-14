import { useEffect, useState } from "react";

export type CapabilityPackageState =
    | "ready"
    | "installing"
    | "starting"
    | "unavailable"
    | "failed";

export interface CapabilityPackageSnapshot {
    id: string;
    displayName: string;
    type: "runtime" | "asset";
    state: CapabilityPackageState;
    optional: boolean;
    autoStart: boolean;
    reason?: string | null;
    resourceUrls?: Record<string, string>;
}

export const useCapabilityPackages = (enabled: boolean, baseUrl: string) => {
    const [packages, setPackages] = useState<Record<string, CapabilityPackageSnapshot>>({});

    useEffect(() => {
        if (!enabled) {
            setPackages({});
            return;
        }

        const abortController = new AbortController();

        void fetch(`${baseUrl}/runtime/packages`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((payload) => {
                if (abortController.signal.aborted || !Array.isArray(payload.packages)) {
                    return;
                }

                const next = payload.packages.reduce(
                    (acc: Record<string, CapabilityPackageSnapshot>, item: CapabilityPackageSnapshot) => {
                        acc[item.id] = item;
                        return acc;
                    },
                    {},
                );
                setPackages(next);
            })
            .catch((error) => {
                if (abortController.signal.aborted) {
                    return;
                }
                console.error("[useCapabilityPackages] Failed to fetch runtime packages:", error);
            });

        return () => {
            abortController.abort();
        };
    }, [enabled, baseUrl]);

    return packages;
};
