import { useCallback, useEffect, useState } from "react";
import { CharacterProfile } from "@core/llm/types";
import { API_CONFIG } from "../config";

export const ACTIVE_CHARACTER_ID = "hiyori";

export const useCharacterProfile = (backendReady: boolean) => {
    const [activeCharacter, setActiveCharacter] = useState<CharacterProfile>();
    const [isLoading, setIsLoading] = useState(true);

    const fetchCharacter = useCallback(async () => {
        if (!backendReady) {
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/character/config`);
            if (!response.ok) {
                throw new Error(`Failed to fetch character config: ${response.status}`);
            }
            setActiveCharacter(await response.json());
        } catch (error) {
            console.error("[useCharacterProfile] Error fetching character config:", error);
        } finally {
            setIsLoading(false);
        }
    }, [backendReady]);

    const saveCharacter = useCallback(async (character: CharacterProfile) => {
        const response = await fetch(`${API_CONFIG.BASE_URL}/character/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...character, id: ACTIVE_CHARACTER_ID }),
        });

        if (!response.ok) {
            throw new Error(`Failed to save character config: ${response.status}`);
        }

        const saved = await response.json();
        setActiveCharacter(saved.character ?? { ...character, id: ACTIVE_CHARACTER_ID });
        return true;
    }, []);

    useEffect(() => {
        void fetchCharacter();
    }, [fetchCharacter]);

    return {
        activeCharacter,
        activeCharacterId: ACTIVE_CHARACTER_ID,
        isLoading,
        fetchCharacter,
        saveCharacter,
    };
};
