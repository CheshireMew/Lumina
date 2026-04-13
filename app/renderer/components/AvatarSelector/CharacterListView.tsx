import React from "react";
import { Check, Edit2, Plus, Trash2, User } from "lucide-react";

import { CharacterProfile } from "@core/llm/types";

import { SchemaForm } from "../Settings/SchemaForm";

interface CharacterListViewProps {
    activeCharacterId: string;
    characters: CharacterProfile[];
    editingCharId: string | null;
    defaultTtsPluginId: string;
    edgeVoices: any[];
    gptVoices: any[];
    activeTtsEngines: string[];
    ttsPlugins: any[];
    onAddCharacter: () => void;
    onActivateCharacter: (id: string) => void;
    onToggleEdit: (id: string) => void;
    onUpdateCharacter: (id: string, updates: Partial<CharacterProfile>) => void;
    onVoiceConfigChange: (id: string, key: string, value: any) => void;
    onDeleteClick: (id: string, event: React.MouseEvent) => void;
    onOpenPicker: (id: string) => void;
}

const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "8px 12px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    fontSize: "14px",
    outline: "none",
    transition: "border-color 0.15s",
};

const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "12px",
    fontWeight: 600,
    color: "#4b5563",
    marginBottom: "4px",
    textTransform: "uppercase",
    letterSpacing: "0.02em",
};

const buttonStyle: React.CSSProperties = {
    cursor: "pointer",
    border: "none",
    borderRadius: "6px",
    backgroundColor: "#6366f1",
    color: "white",
    fontWeight: 500,
    transition: "all 0.15s",
};

export const CharacterListView: React.FC<CharacterListViewProps> = ({
    activeCharacterId,
    characters,
    editingCharId,
    defaultTtsPluginId,
    edgeVoices,
    gptVoices,
    activeTtsEngines,
    ttsPlugins,
    onAddCharacter,
    onActivateCharacter,
    onToggleEdit,
    onUpdateCharacter,
    onVoiceConfigChange,
    onDeleteClick,
    onOpenPicker,
}) => (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div
            style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 15,
            }}
        >
            <h3 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 600 }}>
                Character Management
            </h3>
            <button
                onClick={onAddCharacter}
                style={{
                    ...buttonStyle,
                    padding: "6px 12px",
                    fontSize: "13px",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                }}
            >
                <Plus size={16} /> New Character
            </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", paddingRight: 5, paddingBottom: 20 }}>
            {characters.length === 0 && (
                <div style={{ textAlign: "center", color: "#999", padding: 20 }}>
                    No characters found.
                </div>
            )}

            {[...characters]
                .sort((a, b) =>
                    a.id === activeCharacterId ? -1 : b.id === activeCharacterId ? 1 : 0,
                )
                .map((character) => {
                    const isExpanded = editingCharId === character.id;
                    const isActive = activeCharacterId === character.id;

                    return (
                        <div
                            key={character.id}
                            style={{
                                marginBottom: 10,
                                borderRadius: 8,
                                border: isActive ? "2px solid #818cf8" : "1px solid #e5e7eb",
                                backgroundColor: "white",
                                overflow: "hidden",
                            }}
                        >
                            <div
                                onClick={() => onActivateCharacter(character.id)}
                                style={{
                                    padding: "12px",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    cursor: "pointer",
                                    backgroundColor: isActive ? "#f5f7ff" : "white",
                                }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                    <div
                                        style={{
                                            width: 36,
                                            height: 36,
                                            borderRadius: "50%",
                                            backgroundColor: isActive ? "#c7d2fe" : "#f3f4f6",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                        }}
                                    >
                                        {isActive ? (
                                            <Check size={18} color="#4f46e5" />
                                        ) : (
                                            <User size={18} color="#9ca3af" />
                                        )}
                                    </div>
                                    <div>
                                        <div
                                            style={{ fontWeight: 600, color: "#1f2937" }}
                                        >
                                            {character.name}
                                            {isActive && (
                                                <span
                                                    style={{
                                                        fontSize: "10px",
                                                        background: "#4f46e5",
                                                        color: "white",
                                                        padding: "2px 6px",
                                                        borderRadius: 10,
                                                        marginLeft: 5,
                                                    }}
                                                >
                                                    ACTIVE
                                                </span>
                                            )}
                                        </div>
                                        <div
                                            style={{
                                                fontSize: "12px",
                                                color: "#6b7280",
                                                maxWidth: 300,
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }}
                                        >
                                            {character.description || "No description"}
                                        </div>
                                    </div>
                                </div>

                                <button
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        onToggleEdit(character.id);
                                    }}
                                    style={{
                                        padding: 6,
                                        borderRadius: 4,
                                        background: isExpanded ? "#e5e7eb" : "transparent",
                                        border: "none",
                                        cursor: "pointer",
                                    }}
                                >
                                    <Edit2 size={16} color="#4b5563" />
                                </button>
                            </div>

                            {isExpanded && (
                                <div
                                    style={{
                                        padding: 15,
                                        borderTop: "1px solid #f3f4f6",
                                        backgroundColor: "#fafafa",
                                    }}
                                    onClick={(event) => event.stopPropagation()}
                                >
                                    <div style={{ marginBottom: 10 }}>
                                        <label style={labelStyle}>
                                            Folder Name / ID{" "}
                                            <span
                                                style={{
                                                    fontWeight: 400,
                                                    textTransform: "none",
                                                    color: "#999",
                                                }}
                                            >
                                                ({character.id.startsWith("new_")
                                                    ? "Auto-generated"
                                                    : "Fixed"})
                                            </span>
                                        </label>
                                        <input
                                            value={character.id}
                                            readOnly
                                            style={{
                                                ...inputStyle,
                                                background: "#f3f4f6",
                                                color: "#666",
                                                fontFamily: "monospace",
                                            }}
                                        />
                                    </div>

                                    <div
                                        style={{
                                            display: "grid",
                                            gridTemplateColumns: "1fr 1fr",
                                            gap: 10,
                                            marginBottom: 10,
                                        }}
                                    >
                                        <div>
                                            <label style={labelStyle}>Name</label>
                                            <input
                                                value={character.name}
                                                onChange={(event) =>
                                                    onUpdateCharacter(character.id, {
                                                        name: event.target.value,
                                                    })
                                                }
                                                style={inputStyle}
                                            />
                                        </div>
                                        <div>
                                            <label style={labelStyle}>Description</label>
                                            <input
                                                value={character.description}
                                                onChange={(event) =>
                                                    onUpdateCharacter(character.id, {
                                                        description: event.target.value,
                                                    })
                                                }
                                                style={inputStyle}
                                            />
                                        </div>
                                    </div>

                                    <div style={{ marginBottom: 15 }}>
                                        <label style={labelStyle}>System Prompt</label>
                                        <textarea
                                            value={character.systemPrompt || ""}
                                            onChange={(event) =>
                                                onUpdateCharacter(character.id, {
                                                    systemPrompt: event.target.value,
                                                })
                                            }
                                            style={{
                                                ...inputStyle,
                                                minHeight: 80,
                                                fontFamily: "inherit",
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: 15 }}>
                                        <label style={labelStyle}>Avatar Model</label>
                                        <div style={{ display: "flex", gap: 10 }}>
                                            <input
                                                value={character.modelPath || ""}
                                                readOnly
                                                style={{
                                                    ...inputStyle,
                                                    background: "#f9fafb",
                                                    cursor: "pointer",
                                                }}
                                                onClick={() => onOpenPicker(character.id)}
                                                placeholder="Select a model..."
                                            />
                                            <button
                                                onClick={() => onOpenPicker(character.id)}
                                                style={{
                                                    ...buttonStyle,
                                                    padding: "0 15px",
                                                    backgroundColor: "#3b82f6",
                                                }}
                                            >
                                                Select
                                            </button>
                                        </div>
                                    </div>

                                    <div
                                        style={{
                                            marginBottom: 15,
                                            padding: 10,
                                            border: "1px solid #e5e7eb",
                                            borderRadius: 8,
                                            backgroundColor: "white",
                                        }}
                                    >
                                        <label
                                            style={{
                                                ...labelStyle,
                                                marginBottom: 10,
                                            }}
                                        >
                                            Voice Configuration
                                        </label>
                                        {(() => {
                                            const selectedService =
                                                character.voiceConfig.service ||
                                                defaultTtsPluginId;
                                            const currentPlugin = ttsPlugins.find(
                                                (plugin) => plugin.id === selectedService,
                                            );

                                            return (
                                                <>
                                                    <select
                                                        value={selectedService}
                                                        onChange={(event) =>
                                                            onVoiceConfigChange(
                                                                character.id,
                                                                "service",
                                                                event.target.value,
                                                            )
                                                        }
                                                        style={{
                                                            ...inputStyle,
                                                            marginBottom: 10,
                                                        }}
                                                    >
                                                        {ttsPlugins.map((plugin) => (
                                                            <option
                                                                key={plugin.id}
                                                                value={plugin.id}
                                                            >
                                                                {plugin.name}{" "}
                                                                {activeTtsEngines.includes(
                                                                    plugin.id,
                                                                )
                                                                    ? "OK"
                                                                    : "OFF"}
                                                            </option>
                                                        ))}
                                                        {ttsPlugins.length === 0 && (
                                                            <option value={defaultTtsPluginId}>
                                                                Default TTS
                                                            </option>
                                                        )}
                                                    </select>

                                                    {currentPlugin?.config_schema ? (
                                                        <SchemaForm
                                                            schema={currentPlugin.config_schema}
                                                            values={character.voiceConfig}
                                                            onChange={(key, value) =>
                                                                onVoiceConfigChange(
                                                                    character.id,
                                                                    key,
                                                                    value,
                                                                )
                                                            }
                                                            dataSources={{
                                                                edgeVoices,
                                                                gptVoices,
                                                            }}
                                                        />
                                                    ) : (
                                                        <div
                                                            style={{
                                                                fontSize: 12,
                                                                color: "#999",
                                                            }}
                                                        >
                                                            No schema available
                                                        </div>
                                                    )}
                                                </>
                                            );
                                        })()}
                                    </div>

                                    <div
                                        style={{
                                            display: "flex",
                                            justifyContent: "space-between",
                                            marginTop: 10,
                                        }}
                                    >
                                        <button
                                            onClick={(event) =>
                                                onDeleteClick(character.id, event)
                                            }
                                            style={{
                                                ...buttonStyle,
                                                backgroundColor: "#fee2e2",
                                                color: "#dc2626",
                                                padding: "6px 12px",
                                            }}
                                        >
                                            <Trash2 size={16} /> Delete
                                        </button>

                                        {character.id !== activeCharacterId && (
                                            <button
                                                onClick={() =>
                                                    onActivateCharacter(character.id)
                                                }
                                                style={{
                                                    ...buttonStyle,
                                                    backgroundColor: "#e0e7ff",
                                                    color: "#4f46e5",
                                                    padding: "6px 12px",
                                                }}
                                            >
                                                Set Active
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
        </div>
    </div>
);
