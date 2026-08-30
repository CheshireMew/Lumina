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
            setMessage(error instanceof Error ? error.message : "读取声纹列表失败");
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
            setMessage(`已注册声纹：${profileName}`);
        } catch (error) {
            console.error("[Voiceprint] Failed to register profile", error);
            setMessage(error instanceof Error ? error.message : "注册声纹失败");
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
            setMessage(error instanceof Error ? error.message : "更新声纹状态失败");
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (profileName: string) => {
        if (!confirm(`确定删除声纹“${profileName}”吗？`)) {
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
            setMessage(error instanceof Error ? error.message : "删除声纹失败");
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
                        已注册声纹
                    </div>
                    <div style={{ fontSize: "12px", color: "#6b7280" }}>
                        {profiles.length ? `共 ${profiles.length} 个` : "尚未注册声纹"}
                    </div>
                </div>
                <button
                    type="button"
                    onClick={() => void refreshProfiles()}
                    disabled={loading}
                    style={secondaryButtonStyle}
                    title="刷新声纹列表"
                    aria-label="刷新声纹列表"
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
                        {loading ? "正在读取声纹列表…" : "上传一段 WAV 录音即可注册第一个声纹。"}
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
                                    title={`使用声纹 ${profile.name}`}
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
                                        {profile.enabled ? "已启用" : "已停用"}
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
                                    title={profile.enabled ? "停用声纹" : "启用声纹"}
                                    aria-label={profile.enabled ? `停用声纹 ${profile.name}` : `启用声纹 ${profile.name}`}
                                >
                                    {profile.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => void handleDelete(profile.name)}
                                    disabled={loading}
                                    style={{ ...iconButtonStyle, color: "#dc2626" }}
                                    title="删除声纹"
                                    aria-label={`删除声纹 ${profile.name}`}
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
                    当前选择的声纹“{selectedProfile}”尚未注册。
                </div>
            )}

            <div style={{ fontSize: "13px", fontWeight: 600, color: "#1f2937" }}>
                注册新声纹
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "8px" }}>
                <input
                    type="text"
                    value={newProfileName}
                    onChange={(event) => setNewProfileName(event.target.value)}
                    style={inputStyle}
                    placeholder="声纹名称"
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
                        title={selectedFile?.name ?? "选择 WAV 录音"}
                    >
                        <FolderOpen size={15} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                            {selectedFile?.name ?? "选择 WAV 录音"}
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
                        {loading ? "正在处理…" : "注册"}
                    </button>
                </div>
            </div>

            {message && (
                <div
                    style={{
                        fontSize: "12px",
                        color: message.startsWith("已注册") ? "#065f46" : "#92400e",
                        backgroundColor: message.startsWith("已注册") ? "#d1fae5" : "#fef3c7",
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
