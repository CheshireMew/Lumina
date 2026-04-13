import { useEffect, useState } from "react";
import { listAvailableLlmModels } from "../../api/llmConfigApi";
import { ProviderType } from "./types";

export const useAvailableLlmModels = (
    isOpen: boolean,
    providerType: ProviderType,
) => {
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);

    useEffect(() => {
        if (!isOpen || providerType !== "free") {
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
    }, [isOpen, providerType]);

    return {
        availableModels,
        isLoadingModels,
    };
};
