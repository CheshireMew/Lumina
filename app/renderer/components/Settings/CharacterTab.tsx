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
    onDirtyChange?: (dirty: boolean) => void;
}

const sectionStyle: React.CSSProperties = {
    backgroundColor: "white",
    padding: "15px",
    borderRadius: "8px",
    border: "1px solid #e5e7eb",
};

const rowStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "12px",
};

export const CharacterTab: React.FC<CharacterTabProps> = ({
    apiBaseUrl,
    activeCharacter,
    onSaveCharacter,
    voiceData,
    onDirtyChange,
}) => {
    const [draft, setDraft] = useState<CharacterProfile | null>(activeCharacter ?? null);
    const [baseline, setBaseline] = useState<CharacterProfile | null>(activeCharacter ?? null);
    const [models, setModels] = useState<CharacterAvatarModel[]>([]);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState("");

    useEffect(() => {
        setDraft(activeCharacter ?? null);
        setBaseline(activeCharacter ?? null);
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
        const service = draft?.voiceConfig?.service || "";
        return voiceData.voicesByEngine[service] || [];
    }, [draft?.voiceConfig?.service, voiceData.voicesByEngine]);

    const isDirty = useMemo(
        () => JSON.stringify(draft) !== JSON.stringify(baseline),
        [baseline, draft],
    );

    useEffect(() => {
        onDirtyChange?.(isDirty);
        return () => onDirtyChange?.(false);
    }, [isDirty, onDirtyChange]);

    if (!draft) {
        return (
            <div style={{ padding: "20px", color: "#6b7280", fontSize: "13px" }}>
                角色配置尚未加载。
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
            const saved = await onSaveCharacter(draft);
            if (!saved) {
                throw new Error("角色设置未能保存。 ");
            }
            setBaseline(draft);
            setMessage("角色设置已保存");
        } catch (error) {
            console.error("[CharacterTab] Failed to save character", error);
            setMessage(error instanceof Error ? error.message : "保存角色设置失败");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "15px", padding: "20px", overflowY: "auto" }}>
            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    角色基础设置
                </h3>
                <div style={{ ...sectionStyle, display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div>
                        <label htmlFor="character-id" style={labelStyle}>角色 ID</label>
                        <input
                            id="character-id"
                            value={draft.id}
                            readOnly
                            style={{ ...inputStyle, backgroundColor: "#f9fafb", color: "#6b7280", fontFamily: "monospace" }}
                        />
                    </div>

                    <div style={rowStyle}>
                        <div>
                            <label htmlFor="character-name" style={labelStyle}>名称</label>
                            <input
                                id="character-name"
                                value={draft.name}
                                onChange={(event) => updateDraft({ name: event.target.value })}
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label htmlFor="character-display-name" style={labelStyle}>显示名称</label>
                            <input
                                id="character-display-name"
                                value={draft.displayName ?? ""}
                                onChange={(event) => updateDraft({ displayName: event.target.value })}
                                style={inputStyle}
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="character-description" style={labelStyle}>角色描述</label>
                        <input
                            id="character-description"
                            value={draft.description}
                            onChange={(event) => updateDraft({ description: event.target.value })}
                            style={inputStyle}
                        />
                    </div>

                    <div>
                        <label htmlFor="character-prompt" style={labelStyle}>角色提示词</label>
                        <textarea
                            id="character-prompt"
                            value={draft.systemPrompt ?? ""}
                            onChange={(event) => updateDraft({ systemPrompt: event.target.value })}
                            style={{ ...inputStyle, minHeight: "140px", resize: "vertical", lineHeight: 1.5 }}
                        />
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    角色表现
                </h3>
                <div style={{ ...sectionStyle, display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div>
                        <label htmlFor="character-avatar" style={labelStyle}>Live2D 模型</label>
                        <select
                            id="character-avatar"
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
                            <label htmlFor="character-voice-service" style={labelStyle}>语音服务</label>
                            <select
                                id="character-voice-service"
                                value={draft.voiceConfig.service}
                                onChange={(event) => updateVoiceConfig("service", event.target.value)}
                                style={inputStyle}
                            >
                                {!voiceData.ttsEngines.some((engine) => engine.id === draft.voiceConfig.service) && (
                                    <option value={draft.voiceConfig.service} disabled>
                                        {draft.voiceConfig.service}（当前不可用）
                                    </option>
                                )}
                                {voiceData.ttsEngines.map((engine) => (
                                    <option key={engine.id} value={engine.id}>
                                        {engine.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label htmlFor="character-voice" style={labelStyle}>声音</label>
                            <select
                                id="character-voice"
                                value={draft.voiceConfig.voiceId}
                                onChange={(event) => updateVoiceConfig("voiceId", event.target.value)}
                                style={inputStyle}
                                disabled={voices.length === 0}
                            >
                                {voices.length === 0 && (
                                    <option value={draft.voiceConfig.voiceId || ""}>
                                        {draft.voiceConfig.voiceId || "没有可用声音"}
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
                            <label htmlFor="character-rate" style={labelStyle}>语速</label>
                            <input
                                id="character-rate"
                                value={draft.voiceConfig.rate}
                                onChange={(event) => updateVoiceConfig("rate", event.target.value)}
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label htmlFor="character-pitch" style={labelStyle}>音高</label>
                            <input
                                id="character-pitch"
                                value={draft.voiceConfig.pitch}
                                onChange={(event) => updateVoiceConfig("pitch", event.target.value)}
                                style={inputStyle}
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    交互行为
                </h3>
                <div style={{ ...sectionStyle, display: "flex", flexDirection: "column", gap: "12px" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#1f2937" }}>
                        <input
                            type="checkbox"
                            checked={draft.heartbeatEnabled !== false}
                            onChange={(event) => updateDraft({ heartbeatEnabled: event.target.checked })}
                            style={{ height: "16px", width: "16px" }}
                        />
                        启用定时状态检查
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#1f2937" }}>
                        <input
                            type="checkbox"
                            checked={draft.proactiveChatEnabled !== false}
                            onChange={(event) => updateDraft({ proactiveChatEnabled: event.target.checked })}
                            style={{ height: "16px", width: "16px" }}
                        />
                        允许角色主动发起对话
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#1f2937" }}>
                        <input
                            type="checkbox"
                            checked={draft.soulEvolutionEnabled !== false}
                            onChange={(event) => updateDraft({ soulEvolutionEnabled: event.target.checked })}
                            style={{ height: "16px", width: "16px" }}
                        />
                        允许角色更新长期设定
                    </label>
                    <div style={{ maxWidth: "180px" }}>
                        <label htmlFor="character-proactive-wait" style={labelStyle}>主动对话等待时间（分钟）</label>
                        <input
                            id="character-proactive-wait"
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

            <div style={{ position: "sticky", bottom: -20, display: "flex", alignItems: "center", gap: "10px", justifyContent: "flex-end", padding: "14px 0", background: "rgba(255,255,255,.9)", backdropFilter: "blur(12px)" }}>
                {message && (
                    <div
                        style={{
                            marginRight: "auto",
                            fontSize: "12px",
                            color: message.endsWith("已保存") ? "#065f46" : "#92400e",
                            backgroundColor: message.endsWith("已保存") ? "#d1fae5" : "#fef3c7",
                            borderRadius: "6px",
                            padding: "8px",
                        }}
                    >
                        {message}
                    </div>
                )}
                <button
                    type="button"
                    disabled={isSaving || !isDirty}
                    onClick={() => void handleSave()}
                    style={{
                        ...buttonStyle,
                        backgroundColor: "#4f46e5",
                        color: "#fff",
                        opacity: isSaving || !isDirty ? 0.55 : 1,
                        cursor: isSaving || !isDirty ? "not-allowed" : "pointer",
                    }}
                >
                    {isSaving ? "正在保存…" : "保存角色设置"}
                </button>
            </div>
        </div>
    );
};
