import { useEffect, useMemo, useState } from "react";

import { CharacterProfile } from "@core/llm/types";

import { API_CONFIG } from "../../config";
import { AvatarModel } from "./types";

interface UseAvatarSelectorStateOptions {
    isOpen: boolean;
    activeCharacterId: string;
    characters: CharacterProfile[];
    setCharacters: (chars: CharacterProfile[]) => void;
    onDeleteCharacter: (id: string) => void;
    onSaveCharacters: (chars: CharacterProfile[], deletedIds: string[]) => Promise<void>;
    onClose: () => void;
    activeTtsEngines: string[];
    ttsPlugins: any[];
}

const sanitizeCharacterId = (name: string) =>
    name
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_\u4e00-\u9fa5]/g, "_")
        .replace(/_+/g, "_");

export const useAvatarSelectorState = ({
    isOpen,
    activeCharacterId,
    characters,
    setCharacters,
    onDeleteCharacter,
    onSaveCharacters,
    onClose,
    activeTtsEngines,
    ttsPlugins,
}: UseAvatarSelectorStateOptions) => {
    const [view, setView] = useState<"main" | "picker">("main");
    const [editingCharId, setEditingCharId] = useState<string | null>(null);
    const [deletedIds, setDeletedIds] = useState<string[]>([]);
    const [pickerTargetCharId, setPickerTargetCharId] = useState<string | null>(null);
    const [customPath, setCustomPath] = useState("");
    const [models, setModels] = useState<AvatarModel[]>([]);

    const defaultTtsPluginId = useMemo(
        () =>
            activeTtsEngines[0] ||
            ttsPlugins.find((plugin) => plugin.active_in_group || plugin.active)?.id ||
            ttsPlugins[0]?.id ||
            "driver.tts.edge",
        [activeTtsEngines, ttsPlugins],
    );

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        setView("main");
        setDeletedIds([]);
        setEditingCharId(null);
        setPickerTargetCharId(null);
        setCustomPath("");

        void fetch(`${API_CONFIG.BASE_URL}/characters/models`)
            .then((response) => response.json())
            .then((data) => {
                if (!data.models) {
                    return;
                }

                setModels(
                    data.models.map((model: any) => ({
                        name: model.name,
                        path: model.path,
                        type: model.type,
                        thumbnail: model.thumbnail,
                    })),
                );
            })
            .catch((error) => console.error("Failed to fetch models", error));
    }, [isOpen]);

    const handleAddCharacter = () => {
        const timestamp = Date.now();
        const newCharacter: CharacterProfile = {
            id: `new_${timestamp}`,
            name: "New Character",
            description: "A new digital soul.",
            systemPrompt: "You are a helpful AI assistant.",
            voiceConfig: {
                service: defaultTtsPluginId,
                voiceId: "default",
                rate: "+0%",
                pitch: "+0Hz",
            },
        };
        setCharacters([...characters, newCharacter]);
        setEditingCharId(newCharacter.id);
    };

    const handleUpdateCharacter = (id: string, updates: Partial<CharacterProfile>) => {
        setCharacters(
            characters.map((character) => {
                if (character.id !== id) {
                    return character;
                }

                const updatedCharacter = { ...character, ...updates };
                if (id.startsWith("new_") && updates.name) {
                    const safeId = sanitizeCharacterId(updates.name);
                    if (safeId.length > 0) {
                        updatedCharacter.id = safeId;
                    }
                }
                return updatedCharacter;
            }),
        );

        if (id.startsWith("new_") && updates.name && editingCharId === id) {
            const safeId = sanitizeCharacterId(updates.name);
            if (safeId.length > 0) {
                setEditingCharId(safeId);
                if (pickerTargetCharId === id) {
                    setPickerTargetCharId(safeId);
                }
            }
        }
    };

    const handleVoiceConfigChange = (id: string, key: string, value: any) => {
        setCharacters(
            characters.map((character) =>
                character.id === id
                    ? {
                          ...character,
                          voiceConfig: { ...character.voiceConfig, [key]: value },
                      }
                    : character,
            ),
        );
    };

    const handleModelPick = (path: string) => {
        if (!pickerTargetCharId) {
            return;
        }

        handleUpdateCharacter(pickerTargetCharId, { modelPath: path });
        setView("main");
        setPickerTargetCharId(null);
    };

    const handleDeleteClick = (id: string, event: React.MouseEvent) => {
        event.stopPropagation();
        if (!confirm("Delete this character? This action is pending save.")) {
            return;
        }

        setDeletedIds([...deletedIds, id]);
        onDeleteCharacter(id);
    };

    const handleSaveAndClose = async () => {
        await onSaveCharacters(characters, deletedIds);
        onClose();
    };

    return {
        view,
        setView,
        editingCharId,
        setEditingCharId,
        pickerTargetCharId,
        setPickerTargetCharId,
        customPath,
        setCustomPath,
        models,
        defaultTtsPluginId,
        handleAddCharacter,
        handleUpdateCharacter,
        handleVoiceConfigChange,
        handleModelPick,
        handleDeleteClick,
        handleSaveAndClose,
    };
};
