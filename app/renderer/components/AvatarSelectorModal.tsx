import React from "react";

import { CharacterProfile } from "@core/llm/types";

import { CapabilityPackageSnapshot } from "../hooks/useCapabilityPackages";
import { CharacterListView } from "./AvatarSelector/CharacterListView";
import { ModelPickerView } from "./AvatarSelector/ModelPickerView";
import { useAvatarSelectorState } from "./AvatarSelector/useAvatarSelectorState";

interface AvatarSelectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    activeCharacterId: string;
    activeCharacter?: CharacterProfile;
    live2dPackage?: CapabilityPackageSnapshot;
    characters: CharacterProfile[];
    setCharacters: (chars: CharacterProfile[]) => void;
    onActivateCharacter: (id: string) => void;
    onDeleteCharacter: (id: string) => void;
    onSaveCharacters: (chars: CharacterProfile[], deletedIds: string[]) => Promise<void>;
    edgeVoices: any[];
    gptVoices: any[];
    activeTtsEngines: string[];
    ttsPlugins: any[];
}

const AvatarSelectorModal: React.FC<AvatarSelectorModalProps> = ({
    isOpen,
    onClose,
    activeCharacterId,
    live2dPackage,
    characters,
    setCharacters,
    onActivateCharacter,
    onDeleteCharacter,
    onSaveCharacters,
    edgeVoices,
    gptVoices,
    activeTtsEngines,
    ttsPlugins,
}) => {
    const state = useAvatarSelectorState({
        isOpen,
        activeCharacterId,
        characters,
        live2dPackage,
        setCharacters,
        onDeleteCharacter,
        onSaveCharacters,
        onClose,
        activeTtsEngines,
        ttsPlugins,
    });

    if (!isOpen) {
        return null;
    }

    return (
        <div
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(0, 0, 0, 0.6)",
                backdropFilter: "blur(4px)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                zIndex: 3000,
            }}
        >
            <div
                style={{
                    backgroundColor: "white",
                    borderRadius: "16px",
                    width: "650px",
                    height: "80vh",
                    display: "flex",
                    flexDirection: "column",
                    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                    overflow: "hidden",
                }}
            >
                <div style={{ flex: 1, padding: 25, overflow: "hidden" }}>
                    {state.view === "main" ? (
                        <CharacterListView
                            activeCharacterId={activeCharacterId}
                            characters={characters}
                            editingCharId={state.editingCharId}
                            defaultTtsPluginId={state.defaultTtsPluginId}
                            edgeVoices={edgeVoices}
                            gptVoices={gptVoices}
                            activeTtsEngines={activeTtsEngines}
                            ttsPlugins={ttsPlugins}
                            onAddCharacter={state.handleAddCharacter}
                            onActivateCharacter={onActivateCharacter}
                            onToggleEdit={(id) =>
                                state.setEditingCharId(
                                    state.editingCharId === id ? null : id,
                                )
                            }
                            onUpdateCharacter={state.handleUpdateCharacter}
                            onVoiceConfigChange={state.handleVoiceConfigChange}
                            onDeleteClick={state.handleDeleteClick}
                            onOpenPicker={(id) => {
                                state.setPickerTargetCharId(id);
                                state.setView("picker");
                            }}
                        />
                    ) : (
                        <ModelPickerView
                            characters={characters}
                            pickerTargetCharId={state.pickerTargetCharId}
                            models={state.models}
                            customPath={state.customPath}
                            setCustomPath={state.setCustomPath}
                            onBack={() => state.setView("main")}
                            onModelPick={state.handleModelPick}
                        />
                    )}
                </div>

                {state.view === "main" && (
                    <div
                        style={{
                            padding: "15px 25px",
                            borderTop: "1px solid #e5e7eb",
                            display: "flex",
                            justifyContent: "flex-end",
                            gap: 10,
                            background: "#f9fafb",
                        }}
                    >
                        <button
                            onClick={onClose}
                            style={{
                                cursor: "pointer",
                                borderRadius: "6px",
                                backgroundColor: "white",
                                color: "#374151",
                                border: "1px solid #d1d5db",
                                padding: "8px 16px",
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => {
                                void state.handleSaveAndClose();
                            }}
                            style={{
                                cursor: "pointer",
                                border: "none",
                                borderRadius: "6px",
                                backgroundColor: "#6366f1",
                                color: "white",
                                fontWeight: 500,
                                padding: "8px 24px",
                            }}
                        >
                            Save Changes
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AvatarSelectorModal;
