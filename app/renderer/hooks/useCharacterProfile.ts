import { useCallback, useEffect, useState } from "react";
import { CharacterProfile } from "@core/llm/types";
import { fetchCharacterConfig, updateCharacterConfig } from "../api/characterApi";

export const useCharacterProfile = (backendReady: boolean, baseUrl: string) => {
    const [activeCharacter, setActiveCharacter] = useState<CharacterProfile>();
    const [isLoading, setIsLoading] = useState(true);
    const activeCharacterId = activeCharacter?.id ?? null;

    const fetchCharacter = useCallback(async () => {
        if (!backendReady) {
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        try {
            setActiveCharacter(await fetchCharacterConfig(baseUrl));
        } catch (error) {
            console.error("[useCharacterProfile] Error fetching character config:", error);
        } finally {
            setIsLoading(false);
        }
    }, [backendReady, baseUrl]);

    const saveCharacter = useCallback(async (character: CharacterProfile) => {
        await updateCharacterConfig(baseUrl, character);
        setActiveCharacter(await fetchCharacterConfig(baseUrl));
        return true;
    }, [baseUrl]);

    useEffect(() => {
        void fetchCharacter();
    }, [fetchCharacter]);

    return {
        activeCharacter,
        activeCharacterId,
        isLoading,
        fetchCharacter,
        saveCharacter,
    };
};
