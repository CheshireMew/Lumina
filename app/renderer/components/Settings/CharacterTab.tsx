import React, { useEffect, useMemo, useState } from "react";
import { CharacterProfile } from "@core/llm/types";

import { CharacterAvatarModel, listCharacterModels } from "../../api/characterApi";
import { VoiceManagerData } from "../../hooks/useVoiceManager";
import { buttonStyle, inputStyle, labelStyle } from "./styles";

interface CharacterTabProps {
    apiBaseUrl: string;
    activeCharacter?: CharacterProfile;
    onSaveCharacter: (character: CharacterProfile) => Promise<boolean>;
    voiceData: VoiceManagerData;
}

const sectionStyle: React.CSSProperties = {
    backgroundColor: "white",
    padding: "15px",
    borderRadius: "8px",
    border: "1px solid #e5e7eb",
};

const rowStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "12px",
};

export const CharacterTab: React.FC<CharacterTabProps> = ({
    apiBaseUrl,
    activeCharacter,
    onSaveCharacter,
    voiceData,
}) => {
    const [draft, setDraft] = useState<CharacterProfile | null>(activeCharacter ?? null);
    const [models, setModels] = useState<CharacterAvatarModel[]>([]);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState("");

    useEffect(() => {
        setDraft(activeCharacter ?? null);
        setMessage("");
    }, [activeCharacter]);

    useEffect(() => {
        let disposed = false;

        listCharacterModels(apiBaseUrl)
            .then((result) => {
                if (!disposed) {
                    setModels(result.models ?? []);
                }
            })
            .catch((error) => {
                console.warn("[CharacterTab] Failed to load avatar models", error);
            });

        return () => {
            disposed = true;
        };
    }, [apiBaseUrl]);

    const voices = useMemo(() => {
        if (draft?.voiceConfig?.service === "gpt-sovits") {
            return voiceData.gptVoices;
        }
        return voiceData.edgeVoices;
    }, [draft?.voiceConfig?.service, voiceData.edgeVoices, voiceData.gptVoices]);

    if (!draft) {
        return (
            <div style={{ padding: "20px", color: "#6b7280", fontSize: "13px" }}>
                Character config is not loaded.
            </div>
        );
    }

    const updateDraft = (updates: Partial<CharacterProfile>) => {
        setDraft((current) => current ? { ...current, ...updates } : current);
        setMessage("");
    };

    const updateVoiceConfig = (
        key: keyof CharacterProfile["voiceConfig"],
        value: string,
    ) => {
        setDraft((current) => {
            if (!current) {
                return current;
            }

            return {
                ...current,
                voiceConfig: {
                    ...current.voiceConfig,
                    [key]: value,
                },
            };
        });
        setMessage("");
    };

    const updateAvatarModel = (modelName: string) => {
        setDraft((current) => {
            if (!current) {
                return current;
            }

            return {
                ...current,
                avatar: {
                    ...current.avatar,
                    type: "live2d",
                    model: modelName,
                },
            };
        });
        setMessage("");
    };

    const handleSave = async () => {
        setIsSaving(true);
        setMessage("");
        try {
            await onSaveCharacter(draft);
            setMessage("Character settings saved");
        } catch (error) {
            console.error("[CharacterTab] Failed to save character", error);
            setMessage(error instanceof Error ? error.message : "Failed to save character");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "15px", padding: "20px", overflowY: "auto" }}>
            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    角色基础设置 (Character)
                </h3>
                <div style={{ ...sectionStyle, display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div>
                        <label style={labelStyle}>Character ID</label>
                        <input
                            value={draft.id}
                            readOnly
                            style={{ ...inputStyle, backgroundColor: "#f9fafb", color: "#6b7280", fontFamily: "monospace" }}
                        />
                    </div>

                    <div style={rowStyle}>
                        <div>
                            <label style={labelStyle}>Name</label>
                            <input
                                value={draft.name}
                                onChange={(event) => updateDraft({ name: event.target.value })}
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label style={labelStyle}>Display Name</label>
                            <input
                                value={draft.displayName ?? ""}
                                onChange={(event) => updateDraft({ displayName: event.target.value })}
                                style={inputStyle}
                            />
                        </div>
                    </div>

                    <div>
                        <label style={labelStyle}>Description</label>
                        <input
                            value={draft.description}
                            onChange={(event) => updateDraft({ description: event.target.value })}
                            style={inputStyle}
                        />
                    </div>

                    <div>
                        <label style={labelStyle}>System Prompt</label>
                        <textarea
                            value={draft.systemPrompt ?? ""}
                            onChange={(event) => updateDraft({ systemPrompt: event.target.value })}
                            style={{ ...inputStyle, minHeight: "140px", resize: "vertical", lineHeight: 1.5 }}
                        />
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    角色表现 (Avatar & Voice)
                </h3>
                <div style={{ ...sectionStyle, display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div>
                        <label style={labelStyle}>Live2D Model</label>
                        <select
                            value={draft.avatar.model}
                            onChange={(event) => updateAvatarModel(event.target.value)}
                            style={inputStyle}
                            disabled={models.length === 0}
                        >
                            {models.length === 0 && <option value={draft.avatar.model}>{draft.avatar.model}</option>}
                            {models.map((model) => (
                                <option key={model.name} value={model.name}>
                                    {model.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div style={rowStyle}>
                        <div>
                            <label style={labelStyle}>Voice Service</label>
                            <select
                                value={draft.voiceConfig.service}
                                onChange={(event) => updateVoiceConfig("service", event.target.value)}
                                style={inputStyle}
                            >
                                <option value="edge-tts">Edge TTS</option>
                                <option value="gpt-sovits">GPT-SoVITS</option>
                            </select>
                        </div>
                        <div>
                            <label style={labelStyle}>Voice</label>
                            <select
                                value={draft.voiceConfig.voiceId}
                                onChange={(event) => updateVoiceConfig("voiceId", event.target.value)}
                                style={inputStyle}
                                disabled={voices.length === 0}
                            >
                                {voices.length === 0 && (
                                    <option value={draft.voiceConfig.voiceId || ""}>
                                        {draft.voiceConfig.voiceId || "No voices available"}
                                    </option>
                                )}
                                {voices.map((voice) => (
                                    <option key={voice.name} value={voice.name}>
                                        {voice.name} {voice.gender ? `(${voice.gender})` : ""}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div style={rowStyle}>
                        <div>
                            <label style={labelStyle}>Rate</label>
                            <input
                                value={draft.voiceConfig.rate ?? "+0%"}
                                onChange={(event) => updateVoiceConfig("rate", event.target.value)}
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label style={labelStyle}>Pitch</label>
                            <input
                                value={draft.voiceConfig.pitch ?? "+0Hz"}
                                onChange={(event) => updateVoiceConfig("pitch", event.target.value)}
                                style={inputStyle}
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    交互行为 (Interaction)
                </h3>
                <div style={{ ...sectionStyle, display: "flex", flexDirection: "column", gap: "12px" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#1f2937" }}>
                        <input
                            type="checkbox"
                            checked={draft.heartbeatEnabled !== false}
                            onChange={(event) => updateDraft({ heartbeatEnabled: event.target.checked })}
                            style={{ height: "16px", width: "16px" }}
                        />
                        Heartbeat enabled
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#1f2937" }}>
                        <input
                            type="checkbox"
                            checked={draft.proactiveChatEnabled !== false}
                            onChange={(event) => updateDraft({ proactiveChatEnabled: event.target.checked })}
                            style={{ height: "16px", width: "16px" }}
                        />
                        Proactive chat enabled
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#1f2937" }}>
                        <input
                            type="checkbox"
                            checked={draft.soulEvolutionEnabled !== false}
                            onChange={(event) => updateDraft({ soulEvolutionEnabled: event.target.checked })}
                            style={{ height: "16px", width: "16px" }}
                        />
                        Soul evolution enabled
                    </label>
                    <div style={{ maxWidth: "180px" }}>
                        <label style={labelStyle}>Silence Threshold (minutes)</label>
                        <input
                            type="number"
                            min={1}
                            max={120}
                            value={draft.proactiveThresholdMinutes ?? 15}
                            onChange={(event) => updateDraft({ proactiveThresholdMinutes: Number(event.target.value) })}
                            style={inputStyle}
                        />
                    </div>
                </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px", justifyContent: "flex-end" }}>
                {message && (
                    <div
                        style={{
                            marginRight: "auto",
                            fontSize: "12px",
                            color: message.endsWith("saved") ? "#065f46" : "#92400e",
                            backgroundColor: message.endsWith("saved") ? "#d1fae5" : "#fef3c7",
                            borderRadius: "6px",
                            padding: "8px",
                        }}
                    >
                        {message}
                    </div>
                )}
                <button
                    type="button"
                    disabled={isSaving}
                    onClick={() => void handleSave()}
                    style={{
                        ...buttonStyle,
                        backgroundColor: "#4f46e5",
                        color: "#fff",
                        opacity: isSaving ? 0.65 : 1,
                    }}
                >
                    {isSaving ? "Saving..." : "Save Character"}
                </button>
            </div>
        </div>
    );
};
