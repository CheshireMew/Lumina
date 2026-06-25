import React, { useCallback, useEffect, useMemo, useState } from "react";
import { FolderOpen, RefreshCw, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";

import {
    deleteVoiceprintProfile,
    listVoiceprintProfiles,
    toggleVoiceprintProfile,
    uploadVoiceprintProfile,
    VoiceprintProfile,
} from "../../api/voiceApi";
import { buttonStyle, inputStyle } from "./styles";

interface VoiceprintProfileManagerProps {
    apiBaseUrl: string;
    selectedProfile: string;
    onProfileSelect: (profileName: string) => Promise<void>;
    onRefreshStatus: () => Promise<void>;
}

const secondaryButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    backgroundColor: "#f3f4f6",
    color: "#374151",
    border: "1px solid #d1d5db",
};

const iconButtonStyle: React.CSSProperties = {
    border: "none",
    background: "transparent",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "30px",
    height: "30px",
    borderRadius: "6px",
};

const formatCreatedAt = (createdAt: VoiceprintProfile["created_at"]) => {
    if (!createdAt) {
        return "";
    }

    const date = new Date(createdAt);
    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return date.toLocaleDateString();
};

export const VoiceprintProfileManager: React.FC<VoiceprintProfileManagerProps> = ({
    apiBaseUrl,
    selectedProfile,
    onProfileSelect,
    onRefreshStatus,
}) => {
    const [profiles, setProfiles] = useState<VoiceprintProfile[]>([]);
    const [newProfileName, setNewProfileName] = useState("");
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");

    const selectedProfileExists = useMemo(
        () => profiles.some((profile) => profile.name === selectedProfile),
        [profiles, selectedProfile],
    );

    const refreshProfiles = useCallback(async () => {
        setLoading(true);
        try {
            const result = await listVoiceprintProfiles(apiBaseUrl);
            setProfiles(result.profiles ?? []);
            setMessage("");
        } catch (error) {
            console.error("[Voiceprint] Failed to load profiles", error);
            setMessage(error instanceof Error ? error.message : "Failed to load voiceprints");
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl]);

    useEffect(() => {
        void refreshProfiles();
    }, [refreshProfiles]);

    const handleUpload = async () => {
        const profileName = newProfileName.trim();
        if (!profileName || !selectedFile) {
            return;
        }

        setLoading(true);
        try {
            await uploadVoiceprintProfile(apiBaseUrl, profileName, selectedFile);
            setNewProfileName("");
            setSelectedFile(null);
            await refreshProfiles();
            await onProfileSelect(profileName);
            await onRefreshStatus();
            setMessage(`Registered ${profileName}`);
        } catch (error) {
            console.error("[Voiceprint] Failed to register profile", error);
            setMessage(error instanceof Error ? error.message : "Failed to register voiceprint");
        } finally {
            setLoading(false);
        }
    };

    const handleToggle = async (profile: VoiceprintProfile) => {
        setLoading(true);
        try {
            await toggleVoiceprintProfile(apiBaseUrl, profile.name, !profile.enabled);
            await refreshProfiles();
            await onRefreshStatus();
        } catch (error) {
            console.error("[Voiceprint] Failed to toggle profile", error);
            setMessage(error instanceof Error ? error.message : "Failed to update voiceprint");
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (profileName: string) => {
        if (!confirm(`Delete voiceprint '${profileName}'?`)) {
            return;
        }

        setLoading(true);
        try {
            await deleteVoiceprintProfile(apiBaseUrl, profileName);
            if (profileName === selectedProfile) {
                await onProfileSelect("");
            }
            await refreshProfiles();
            await onRefreshStatus();
        } catch (error) {
            console.error("[Voiceprint] Failed to delete profile", error);
            setMessage(error instanceof Error ? error.message : "Failed to delete voiceprint");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                }}
            >
                <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#1f2937" }}>
                        Active Voiceprints
                    </div>
                    <div style={{ fontSize: "12px", color: "#6b7280" }}>
                        {profiles.length ? `${profiles.length} registered` : "No registered voiceprints"}
                    </div>
                </div>
                <button
                    type="button"
                    onClick={() => void refreshProfiles()}
                    disabled={loading}
                    style={secondaryButtonStyle}
                    title="Refresh profiles"
                >
                    <RefreshCw size={15} />
                </button>
            </div>

            <div
                style={{
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    overflow: "hidden",
                    backgroundColor: "#f9fafb",
                }}
            >
                {profiles.length === 0 ? (
                    <div style={{ padding: "12px", color: "#6b7280", fontSize: "12px" }}>
                        {loading ? "Loading profiles..." : "Upload a WAV sample to register your first profile."}
                    </div>
                ) : (
                    profiles.map((profile) => {
                        const createdAt = formatCreatedAt(profile.created_at);

                        return (
                            <div
                                key={profile.name}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    gap: "10px",
                                    padding: "8px 10px",
                                    borderBottom: "1px solid #e5e7eb",
                                    backgroundColor: profile.name === selectedProfile ? "#eef2ff" : "#fff",
                                }}
                            >
                                <button
                                    type="button"
                                    onClick={() => void onProfileSelect(profile.name)}
                                    style={{
                                        border: "none",
                                        background: "transparent",
                                        textAlign: "left",
                                        flex: 1,
                                        cursor: "pointer",
                                        minWidth: 0,
                                        opacity: profile.enabled ? 1 : 0.55,
                                    }}
                                    title={`Use ${profile.name}`}
                                >
                                    <div
                                        style={{
                                            fontSize: "13px",
                                            fontWeight: 600,
                                            color: "#1f2937",
                                            overflow: "hidden",
                                            textOverflow: "ellipsis",
                                            whiteSpace: "nowrap",
                                        }}
                                    >
                                        {profile.name}
                                    </div>
                                    <div style={{ fontSize: "11px", color: "#6b7280" }}>
                                        {profile.enabled ? "Enabled" : "Disabled"}
                                        {createdAt ? ` · ${createdAt}` : ""}
                                    </div>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => void handleToggle(profile)}
                                    disabled={loading}
                                    style={{
                                        ...iconButtonStyle,
                                        color: profile.enabled ? "#059669" : "#9ca3af",
                                    }}
                                    title={profile.enabled ? "Disable profile" : "Enable profile"}
                                >
                                    {profile.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => void handleDelete(profile.name)}
                                    disabled={loading}
                                    style={{ ...iconButtonStyle, color: "#dc2626" }}
                                    title="Delete profile"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        );
                    })
                )}
            </div>

            {selectedProfile && !selectedProfileExists && (
                <div
                    style={{
                        fontSize: "12px",
                        color: "#92400e",
                        backgroundColor: "#fef3c7",
                        borderRadius: "6px",
                        padding: "8px",
                    }}
                >
                    Current profile "{selectedProfile}" is not registered.
                </div>
            )}

            <div style={{ fontSize: "13px", fontWeight: 600, color: "#1f2937" }}>
                Register New Voice
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "8px" }}>
                <input
                    type="text"
                    value={newProfileName}
                    onChange={(event) => setNewProfileName(event.target.value)}
                    style={inputStyle}
                    placeholder="New profile name"
                    disabled={loading}
                />
                <div style={{ display: "flex", gap: "8px" }}>
                    <label
                        style={{
                            ...secondaryButtonStyle,
                            flex: 1,
                            minWidth: 0,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                        }}
                        title={selectedFile?.name ?? "Select WAV file"}
                    >
                        <FolderOpen size={15} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                            {selectedFile?.name ?? "Select WAV"}
                        </span>
                        <input
                            type="file"
                            accept=".wav,audio/wav"
                            style={{ display: "none" }}
                            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                            disabled={loading}
                        />
                    </label>
                    <button
                        type="button"
                        onClick={() => void handleUpload()}
                        disabled={loading || !newProfileName.trim() || !selectedFile}
                        style={{
                            ...buttonStyle,
                            backgroundColor: "#4f46e5",
                            color: "#fff",
                            opacity: loading || !newProfileName.trim() || !selectedFile ? 0.55 : 1,
                        }}
                    >
                        {loading ? "Working..." : "Register"}
                    </button>
                </div>
            </div>

            {message && (
                <div
                    style={{
                        fontSize: "12px",
                        color: message.startsWith("Registered") ? "#065f46" : "#92400e",
                        backgroundColor: message.startsWith("Registered") ? "#d1fae5" : "#fef3c7",
                        borderRadius: "6px",
                        padding: "8px",
                    }}
                >
                    {message}
                </div>
            )}
        </div>
    );
};
