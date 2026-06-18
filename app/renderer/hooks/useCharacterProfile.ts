import { useCallback, useEffect, useState } from "react";
import { CharacterProfile } from "@core/llm/types";

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
            const response = await fetch(`${baseUrl}/settings/character/config`);
            if (!response.ok) {
                throw new Error(`Failed to fetch character config: ${response.status}`);
            }
            setActiveCharacter(await response.json());
        } catch (error) {
            console.error("[useCharacterProfile] Error fetching character config:", error);
        } finally {
            setIsLoading(false);
        }
    }, [backendReady, baseUrl]);

    const saveCharacter = useCallback(async (character: CharacterProfile) => {
        const response = await fetch(`${baseUrl}/settings/character/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(character),
        });

        if (!response.ok) {
            throw new Error(`Failed to save character config: ${response.status}`);
        }

        const saved = await response.json();
        setActiveCharacter(saved.character ?? character);
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
