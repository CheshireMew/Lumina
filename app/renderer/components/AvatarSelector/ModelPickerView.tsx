import React from "react";
import { Box, Image as ImageIcon, Layers } from "lucide-react";

import { CharacterProfile } from "@core/llm/types";

import { AvatarModel } from "./types";

interface ModelPickerViewProps {
    characters: CharacterProfile[];
    pickerTargetCharId: string | null;
    models: AvatarModel[];
    customPath: string;
    setCustomPath: (value: string) => void;
    onBack: () => void;
    onModelPick: (path: string) => void;
}

export const ModelPickerView: React.FC<ModelPickerViewProps> = ({
    characters,
    pickerTargetCharId,
    models,
    customPath,
    setCustomPath,
    onBack,
    onModelPick,
}) => {
    const targetCharacter = characters.find(
        (character) => character.id === pickerTargetCharId,
    );

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    marginBottom: 20,
                }}
            >
                <button
                    onClick={onBack}
                    style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "#666",
                    }}
                >
                    {"<"} Back
                </button>
                <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600 }}>
                    Select Avatar Model
                </h3>
            </div>

            <div style={{ flex: 1, overflowY: "auto", paddingRight: 5 }}>
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                        gap: 15,
                    }}
                >
                    {models.map((model, index) => {
                        const isSelected = targetCharacter?.modelPath === model.path;
                        return (
                            <div
                                key={`${model.path}-${index}`}
                                onClick={() => onModelPick(model.path)}
                                style={{
                                    border: isSelected
                                        ? "2px solid #3b82f6"
                                        : "1px solid #e5e7eb",
                                    borderRadius: 12,
                                    padding: 10,
                                    cursor: "pointer",
                                    textAlign: "center",
                                    backgroundColor: isSelected ? "#eff6ff" : "white",
                                    transition: "all 0.2s",
                                }}
                            >
                                <div
                                    style={{
                                        width: 48,
                                        height: 48,
                                        borderRadius: "50%",
                                        backgroundColor: "#e5e7eb",
                                        margin: "0 auto 10px",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        overflow: "hidden",
                                    }}
                                >
                                    {model.thumbnail ? (
                                        <img
                                            src={model.thumbnail}
                                            alt=""
                                            style={{
                                                width: "100%",
                                                height: "100%",
                                                objectFit: "cover",
                                            }}
                                        />
                                    ) : model.type === "vrm" ? (
                                        <Box size={24} />
                                    ) : model.type === "sprite" ? (
                                        <ImageIcon size={24} />
                                    ) : (
                                        <Layers size={24} />
                                    )}
                                </div>
                                <div style={{ fontWeight: 500, fontSize: "0.9rem" }}>
                                    {model.name}
                                </div>
                                <div
                                    style={{
                                        fontSize: "0.7rem",
                                        color: "#9ca3af",
                                        marginTop: 4,
                                    }}
                                >
                                    {(model.type || "unknown").toUpperCase()}
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div
                    style={{
                        marginTop: 20,
                        paddingTop: 20,
                        borderTop: "1px solid #eee",
                    }}
                >
                    <h4 style={{ fontSize: "0.9rem", marginBottom: 10 }}>
                        Custom Path
                    </h4>
                    <div style={{ display: "flex", gap: 10 }}>
                        <input
                            type="text"
                            placeholder="/models/my_avatar.vrm"
                            value={customPath}
                            onChange={(event) => setCustomPath(event.target.value)}
                            style={{
                                flex: 1,
                                padding: "8px",
                                borderRadius: 6,
                                border: "1px solid #ddd",
                            }}
                        />
                        <button
                            onClick={() => onModelPick(customPath)}
                            disabled={!customPath}
                            style={{
                                cursor: "pointer",
                                border: "none",
                                borderRadius: "6px",
                                backgroundColor: "#6366f1",
                                color: "white",
                                fontWeight: 500,
                                transition: "all 0.15s",
                                padding: "0 15px",
                                opacity: customPath ? 1 : 0.5,
                            }}
                        >
                            Use Path
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
