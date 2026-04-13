import React, { useEffect, useState } from "react";
import { FolderOpen, Mic, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";

import { API_CONFIG } from "../../config";

interface VoiceprintConfigPanelProps {
    threshold: number;
    onThresholdChange: (value: number) => void;
}

export const VoiceprintConfigPanel: React.FC<VoiceprintConfigPanelProps> = ({
    threshold,
    onThresholdChange,
}) => {
    const [profiles, setProfiles] = useState<any[]>([]);
    const [name, setName] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [isFetching, setIsFetching] = useState(true);
    const [message, setMessage] = useState("");
    const [localThreshold, setLocalThreshold] = useState(threshold);

    useEffect(() => {
        setLocalThreshold(threshold);
    }, [threshold]);

    const fetchProfiles = async () => {
        setIsFetching(true);
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/plugins/voiceprint/list`);
            const data = await response.json();
            if (data.profiles) {
                setProfiles(data.profiles);
            }
        } catch (error) {
            console.error(error);
        } finally {
            setIsFetching(false);
        }
    };

    useEffect(() => {
        void fetchProfiles();
    }, []);

    const handleRegister = async () => {
        if (!file || !name) {
            return;
        }

        setLoading(true);
        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch(
                `${API_CONFIG.BASE_URL}/plugins/voiceprint/upload?name=${encodeURIComponent(name)}`,
                {
                    method: "POST",
                    body: formData,
                },
            );

            if (response.ok) {
                setMessage("Registered successfully");
                setFile(null);
                setName("");
                void fetchProfiles();
            } else {
                setMessage("Registration failed");
            }
        } catch (error) {
            setMessage(`Error: ${error}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (profileName: string) => {
        if (!confirm(`Delete voiceprint '${profileName}'?`)) {
            return;
        }

        try {
            await fetch(`${API_CONFIG.BASE_URL}/plugins/voiceprint/${profileName}`, {
                method: "DELETE",
            });
            void fetchProfiles();
        } catch (error) {
            console.error(error);
        }
    };

    const handleToggle = async (profileName: string, currentEnabled: boolean) => {
        try {
            const response = await fetch(
                `${API_CONFIG.BASE_URL}/plugins/voiceprint/toggle/${profileName}?enabled=${!currentEnabled}`,
                { method: "POST" },
            );
            if (response.ok) {
                void fetchProfiles();
            }
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <div style={{ marginTop: 10 }}>
            <div
                style={{
                    background: "rgba(255,255,255,0.05)",
                    padding: "15px",
                    borderRadius: "8px",
                    marginBottom: "20px",
                }}
            >
                <label
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "10px",
                        fontWeight: "bold",
                        color: "#ccc",
                    }}
                >
                    <span>Similarity Threshold</span>
                    <span style={{ color: "#fff" }}>{localThreshold}</span>
                </label>
                <input
                    type="range"
                    min="0.1"
                    max="0.9"
                    step="0.05"
                    value={localThreshold}
                    onChange={(event) => setLocalThreshold(parseFloat(event.target.value))}
                    onMouseUp={() => onThresholdChange(localThreshold)}
                    onTouchEnd={() => onThresholdChange(localThreshold)}
                    style={{ width: "100%", cursor: "pointer", accentColor: "#7928ca" }}
                />
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: "0.75em",
                        color: "#888",
                        marginTop: "5px",
                    }}
                >
                    <span>Low (Permissive)</span>
                    <span>High (Strict)</span>
                </div>
            </div>

            <h4
                style={{
                    margin: "0 0 10px 0",
                    color: "#ddd",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}
            >
                <Mic size={16} /> Active Voiceprints
            </h4>
            <div
                style={{
                    maxHeight: 150,
                    overflowY: "auto",
                    background: "rgba(0,0,0,0.2)",
                    borderRadius: 6,
                    padding: 5,
                    marginBottom: 15,
                }}
            >
                {isFetching ? (
                    <div
                        style={{
                            padding: 20,
                            textAlign: "center",
                            color: "#888",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 10,
                        }}
                    >
                        <div
                            className="spinner"
                            style={{
                                width: 16,
                                height: 16,
                                border: "2px solid rgba(255,255,255,0.1)",
                                borderTopColor: "#a78bfa",
                                borderRadius: "50%",
                                animation: "spin 1s linear infinite",
                            }}
                        />
                        <span>Loading profiles...</span>
                    </div>
                ) : profiles.length === 0 ? (
                    <div
                        style={{
                            padding: 10,
                            color: "#888",
                            textAlign: "center",
                            fontSize: "0.9em",
                        }}
                    >
                        No voiceprints yet
                    </div>
                ) : (
                    profiles.map((profile) => (
                        <div
                            key={profile.name}
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                padding: "6px 10px",
                                borderBottom: "1px solid rgba(255,255,255,0.05)",
                            }}
                        >
                            <div
                                style={{
                                    opacity: profile.enabled ? 1 : 0.5,
                                    transition: "opacity 0.2s",
                                }}
                            >
                                <span
                                    style={{
                                        fontWeight: "bold",
                                        color: "#fff",
                                        marginRight: 8,
                                    }}
                                >
                                    {profile.name}
                                </span>
                                <span style={{ fontSize: "0.75em", color: "#aaa" }}>
                                    {new Date(profile.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                                <button
                                    onClick={() => handleToggle(profile.name, profile.enabled)}
                                    title={profile.enabled ? "Disable" : "Enable"}
                                    style={{
                                        background: "transparent",
                                        border: "none",
                                        color: profile.enabled ? "#4caf50" : "#666",
                                        cursor: "pointer",
                                        display: "flex",
                                        alignItems: "center",
                                    }}
                                >
                                    {profile.enabled ? (
                                        <ToggleRight size={20} />
                                    ) : (
                                        <ToggleLeft size={20} />
                                    )}
                                </button>
                                <button
                                    onClick={() => handleDelete(profile.name)}
                                    title="Delete"
                                    style={{
                                        background: "transparent",
                                        border: "none",
                                        color: "#ff4444",
                                        cursor: "pointer",
                                        display: "flex",
                                    }}
                                >
                                    {loading && name === profile.name ? "..." : <Trash2 size={16} />}
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            <h4 style={{ margin: "0 0 10px 0", color: "#ddd", fontSize: "0.9em" }}>
                Register New Voice
            </h4>
            <div style={{ display: "flex", gap: 10, flexDirection: "column" }}>
                <input
                    type="text"
                    placeholder="User Name (e.g. Master)"
                    className="galgame-input"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                />
                <div style={{ display: "flex", gap: 10 }}>
                    <label
                        style={{
                            flex: 1,
                            cursor: "pointer",
                            background: "rgba(255,255,255,0.1)",
                            padding: "8px",
                            borderRadius: 6,
                            textAlign: "center",
                            border: "1px dashed #666",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 6,
                            fontSize: "0.9em",
                            color: "#ccc",
                        }}
                    >
                        <FolderOpen size={14} />
                        {file ? file.name : "Select WAV File..."}
                        <input
                            type="file"
                            accept=".wav"
                            style={{ display: "none" }}
                            onChange={(event) =>
                                event.target.files && setFile(event.target.files[0])
                            }
                        />
                    </label>
                    <button
                        className="galgame-btn primary"
                        disabled={!file || !name || loading}
                        onClick={handleRegister}
                        style={{ flex: 1, opacity: !file || !name ? 0.5 : 1 }}
                    >
                        {loading ? "Processing..." : "Register"}
                    </button>
                </div>
                {message && (
                    <div
                        style={{
                            marginTop: 5,
                            color: message === "Registered successfully" ? "#4caf50" : "#ff4444",
                            fontSize: "0.9em",
                        }}
                    >
                        {message}
                    </div>
                )}
            </div>
        </div>
    );
};
