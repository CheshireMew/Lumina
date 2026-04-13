import { useState, useEffect, useCallback } from "react";
import { CharacterProfile } from "@core/llm/types";
import { API_CONFIG } from "../config";
import { electronSettings, loadBootstrapState } from "../platform/electron";

export const useCharacterState = (
    backendReady: boolean,
    initialActiveId: string = "",
) => {
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    const [activeCharacterId, setActiveCharacterId] =
        useState<string>(initialActiveId);
    const [isLoading, setIsLoading] = useState(true);

    const activeCharacter = characters.find((c) => c.id === activeCharacterId);

    const persistCharacter = async (character: CharacterProfile) => {
        return fetch(`${API_CONFIG.BASE_URL}/characters/${character.id}/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(character),
        });
    };

    // Fetch characters from backend
    const fetchCharacters = useCallback(async () => {
        if (!backendReady) {
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        try {
            const charRes = await fetch(`${API_CONFIG.BASE_URL}/characters`);
            if (!charRes.ok) {
                throw new Error(`Failed to fetch characters: ${charRes.status}`);
            }

            const data = await charRes.json();
            setCharacters(data.characters || []);
        } catch (e) {
            console.error("[useCharacterState] Error fetching characters:", e);
        } finally {
            setIsLoading(false);
        }
    }, [backendReady]);

    // Switch Character
    const switchCharacter = async (newInfo: string | CharacterProfile) => {
        const newId = typeof newInfo === "string" ? newInfo : newInfo.id;

        if (newId === activeCharacterId) {
            console.log("[useCharacterState] Already on this character");
            return false;
        }

        console.log(`[useCharacterState] Switching to character: ${newId}`);
        setActiveCharacterId(newId);

        // Notify Backend
        try {
            const response = await fetch(
                `${API_CONFIG.BASE_URL}/soul/switch_character`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ character_id: newId }),
                }
            );

            if (response.ok) {
                console.log(
                    `[useCharacterState] ✅ Backend switched to: ${newId}`
                );
            } else {
                console.error(
                    "[useCharacterState] Backend switch failed:",
                    await response.text()
                );
            }
        } catch (error) {
            console.error(
                "[useCharacterState] Failed to notify backend:",
                error
            );
        }

        // Persist
        await electronSettings.set("activeCharacterId", newId);

        return true;
    };

    /**
     * Update the model path for a character
     */
    const updateCharacterModel = async (
        characterId: string,
        modelPath: string
    ) => {
        // 1. Optimistic Update (Frontend)
        setCharacters((prev) =>
            prev.map((c) => (c.id === characterId ? { ...c, modelPath } : c))
        );

        // 2. Persist to Backend
        try {
            const targetCharacter = characters.find((c) => c.id === characterId);
            if (!targetCharacter) {
                throw new Error(`Character not found: ${characterId}`);
            }

            const response = await persistCharacter({
                ...targetCharacter,
                modelPath,
            });

            if (!response.ok) {
                console.error(
                    "[useCharacterState] Failed to save model change:",
                    await response.text()
                );
            }
        } catch (e) {
            console.error("[useCharacterState] Network error saving model:", e);
        }
    };

    /**
     * Save all characters to backend
     */
    const saveCharacters = async (
        allCharacters: CharacterProfile[],
        deletedIds: string[] = []
    ) => {
        try {
            console.log(
                "[useCharacterState] Saving characters...",
                allCharacters
            );

            const savePromises = allCharacters.map((char) => persistCharacter(char));

            const deletePromises = deletedIds.map((id) =>
                fetch(`${API_CONFIG.BASE_URL}/characters/${id}`, {
                    method: "DELETE",
                })
            );

            await Promise.all([...savePromises, ...deletePromises]);

            // Refresh State
            setCharacters(allCharacters);

            return true;
        } catch (e) {
            console.error("[useCharacterState] Failed to save characters:", e);
            return false;
        }
    };

    // Initial Load
    useEffect(() => {
        const init = async () => {
            const { localSettings } = await loadBootstrapState();
            const savedId = localSettings.activeCharacterId;
            if (savedId && !initialActiveId) {
                setActiveCharacterId(savedId);
            }
        };
        void init();
    }, [initialActiveId]);

    useEffect(() => {
        void fetchCharacters();
    }, [fetchCharacters]);

    return {
        characters,
        activeCharacterId,
        activeCharacter,
        isLoading,
        fetchCharacters,
        switchCharacter,
        setCharacters,
        updateCharacterModel,
        saveCharacters,
    };
};
