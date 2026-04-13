import { useEffect, useState } from "react";
import {
    BackendState,
    loadBootstrapState,
    onBackendStateChange,
} from "../platform/electron";

const DEFAULT_BACKEND_STATE: BackendState = {
    status: "starting",
    ports: {},
};

export const useBackendState = () => {
    const [backendState, setBackendState] =
        useState<BackendState>(DEFAULT_BACKEND_STATE);

    useEffect(() => {
        let disposed = false;

        void loadBootstrapState()
            .then((snapshot) => snapshot.backend)
            .then((state) => {
                if (!disposed) {
                    setBackendState(state);
                }
            })
            .catch((error) => {
                console.error("[useBackendState] Failed to read backend state:", error);
            });

        const unsubscribe = onBackendStateChange((state) => {
            if (!disposed) {
                setBackendState(state);
            }
        });

        return () => {
            disposed = true;
            unsubscribe();
        };
    }, []);

    return backendState;
};
