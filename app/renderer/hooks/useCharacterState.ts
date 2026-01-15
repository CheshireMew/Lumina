import { useState, useEffect, useRef } from "react";
import { CharacterProfile } from "@core/llm/types";
import { API_CONFIG } from "../config";
import { memoryService } from "@core/memory/memory_service";

export const useCharacterState = (initialActiveId: string = "") => {
  const [characters, setCharacters] = useState<CharacterProfile[]>([]);
  const [activeCharacterId, setActiveCharacterId] =
    useState<string>(initialActiveId);
  const [isLoading, setIsLoading] = useState(true);

  const activeCharacter = characters.find((c) => c.id === activeCharacterId);

  // Fetch characters from backend
  const fetchCharacters = async () => {
    setIsLoading(true);
    try {
      const settings = window.settings;
      // 1. Try fetching from Backend API (Single Source of Truth)
      const charRes = await fetch(`${API_CONFIG.BASE_URL}/characters`);

      if (charRes.ok) {
        const data = await charRes.json();

        // MAPPING: Convert Backend (snake_case) to Frontend (camelCase) where needed
        // Most fields map directly if types match, but we need to ensure compatibility
        const loadedCharacters: CharacterProfile[] = (
          data.characters || []
        ).map((char: any) => ({
          id: char.character_id,
          name: char.name,
          description: char.description,
          systemPrompt: char.system_prompt,
          modelPath: char.live2d_model,
          voiceConfig: char.voice_config,
          // Interaction settings
          heartbeatEnabled: char.heartbeat_enabled !== false,
          proactiveChatEnabled: char.proactive_chat_enabled !== false,
          galgameModeEnabled: char.galgame_mode_enabled !== false,
          soulEvolutionEnabled: char.soul_evolution_enabled !== false,
          proactiveThresholdMinutes: char.proactive_threshold_minutes || 15,
        }));

        setCharacters(loadedCharacters);

        // Update cache
        await settings.set("characters", loadedCharacters);
      } else {
        console.warn(
          "[useCharacterState] Failed to fetch characters from backend, falling back to cache"
        );
        const cached = await settings.get("characters");
        if (cached) setCharacters(cached);
      }
    } catch (e) {
      console.error("[useCharacterState] Error fetching characters:", e);
      // Fallback to cache
      const settings = window.settings;
      const cached = await settings.get("characters");
      if (cached) setCharacters(cached);
    } finally {
      setIsLoading(false);
    }
  };

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
        console.log(`[useCharacterState] ✅ Backend switched to: ${newId}`);
      } else {
        console.error(
          "[useCharacterState] Backend switch failed:",
          await response.text()
        );
      }
    } catch (error) {
      console.error("[useCharacterState] Failed to notify backend:", error);
    }

    // Configure Memory Service
    try {
      const settings = window.settings;
      const apiKey = await settings.get("apiKey");
      const baseUrl = await settings.get("apiBaseUrl");
      const model = await settings.get("modelName");

      await memoryService.configure(apiKey, baseUrl, model, newId);
    } catch (error) {
      console.error("[useCharacterState] Failed to reconfigure memory:", error);
    }

    // Persist
    const settings = window.settings;
    await settings.set("activeCharacterId", newId);

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
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/characters/${characterId}/config`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ live2d_model: modelPath }),
        }
      );

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

  // Initial Load
  useEffect(() => {
    fetchCharacters();
    // Load initial active ID from settings if not provided
    const init = async () => {
      const settings = window.settings;
      const savedId = await settings.get("activeCharacterId");
      if (savedId && !initialActiveId) {
        setActiveCharacterId(savedId);
      }
    };
    init();
  }, []);

  return {
    characters,
    activeCharacterId,
    activeCharacter,
    isLoading,
    fetchCharacters,
    switchCharacter,
    setCharacters,
    updateCharacterModel,
  };
};
