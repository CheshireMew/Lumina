import { useEffect, useState } from "react";
import { listAvailableLlmModels } from "../../api/llmConfigApi";
import { FREE_LLM_PROVIDER_ID, LlmProviderId } from "./types";

export const useAvailableLlmModels = (
    isOpen: boolean,
    providerId: LlmProviderId,
    apiBaseUrl: string,
) => {
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);
    const [modelLoadError, setModelLoadError] = useState<string | null>(null);

    useEffect(() => {
        if (!isOpen || providerId !== FREE_LLM_PROVIDER_ID) {
            setModelLoadError(null);
            return;
        }

        let isMounted = true;
        setIsLoadingModels(true);
        setModelLoadError(null);

        listAvailableLlmModels(apiBaseUrl, providerId)
            .then((models) => {
                if (isMounted) {
                    setAvailableModels(models);
                }
            })
            .catch((error) => {
                console.warn("Failed to fetch models:", error);
                if (isMounted) {
                    setAvailableModels([]);
                    setModelLoadError(
                        error instanceof Error
                            ? error.message
                            : "Failed to fetch models",
                    );
                }
            })
            .finally(() => {
                if (isMounted) {
                    setIsLoadingModels(false);
                }
            });

        return () => {
            isMounted = false;
        };
    }, [apiBaseUrl, isOpen, providerId]);

    return {
        availableModels,
        isLoadingModels,
        modelLoadError,
    };
};
