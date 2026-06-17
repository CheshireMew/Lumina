import { useEffect, useState } from "react";
import { listAvailableLlmModels } from "../../api/llmConfigApi";
import { FREE_LLM_PROVIDER_ID, LlmProviderId } from "./types";

export const useAvailableLlmModels = (
    isOpen: boolean,
    providerId: LlmProviderId,
) => {
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);

    useEffect(() => {
        if (!isOpen || providerId !== FREE_LLM_PROVIDER_ID) {
            return;
        }

        let isMounted = true;
        setIsLoadingModels(true);

        listAvailableLlmModels()
            .then((models) => {
                if (isMounted) {
                    setAvailableModels(models);
                }
            })
            .catch((err) => console.warn("Failed to fetch models:", err))
            .finally(() => {
                if (isMounted) {
                    setIsLoadingModels(false);
                }
            });

        return () => {
            isMounted = false;
        };
    }, [isOpen, providerId]);

    return {
        availableModels,
        isLoadingModels,
    };
};
