import React, { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { VoiceManagerData } from "../../hooks/useVoiceManager";
import { inputStyle } from "./styles";
import { VoiceprintProfileManager } from "./VoiceprintProfileManager";

export const VoiceprintTab: React.FC<VoiceManagerData> = ({
    apiBaseUrl,
    voiceprintEnabled,
    voiceprintThreshold,
    voiceprintProfile,
    voiceprintStatus,
    voiceprintLoaded,
    handleVoiceprintToggle,
    handleVoiceprintThresholdChange,
    handleVoiceprintProfileChange,
    refreshVoiceData,
}) => {
    const [localThreshold, setLocalThreshold] = useState(voiceprintThreshold);
    const [localProfile, setLocalProfile] = useState(voiceprintProfile);

    useEffect(() => {
        setLocalThreshold(voiceprintThreshold);
    }, [voiceprintThreshold]);

    useEffect(() => {
        setLocalProfile(voiceprintProfile);
    }, [voiceprintProfile]);

    const commitThreshold = () => {
        if (localThreshold !== voiceprintThreshold) {
            void handleVoiceprintThresholdChange(localThreshold);
        }
    };

    const commitProfile = (profileName = localProfile) => {
        if (profileName !== voiceprintProfile) {
            void handleVoiceprintProfileChange(profileName);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "15px", padding: "20px", overflowY: "auto" }}>
            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    声纹过滤
                </h3>
                <div
                    style={{
                        backgroundColor: "white",
                        padding: "15px",
                        borderRadius: "8px",
                        border: "1px solid #e5e7eb",
                        display: "flex",
                        flexDirection: "column",
                        gap: "15px",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <input
                            id="voiceprint-enabled"
                            type="checkbox"
                            checked={voiceprintEnabled}
                            onChange={(event) => void handleVoiceprintToggle(event.target.checked)}
                            disabled={!voiceprintLoaded}
                            aria-describedby="voiceprint-toggle-help"
                            style={{ height: "16px", width: "16px", cursor: "pointer" }}
                        />
                        <div>
                            <label htmlFor="voiceprint-enabled" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "#1f2937" }}>
                                启用声纹验证
                            </label>
                            <div id="voiceprint-toggle-help" style={{ fontSize: "12px", color: "#6b7280" }}>
                                {voiceprintLoaded ? "只接受当前已启用声纹对应的声音" : "请先在下方注册、启用并选择一个声纹"}
                            </div>
                        </div>
                    </div>

                    <div>
                        <label htmlFor="voiceprint-threshold" style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", color: "#6b7280", marginBottom: "6px" }}>
                            <span>相似度阈值</span>
                            <strong style={{ color: "#1f2937" }}>{localThreshold.toFixed(2)}</strong>
                        </label>
                        <input
                            id="voiceprint-threshold"
                            type="range"
                            min="0.1"
                            max="0.9"
                            step="0.05"
                            value={localThreshold}
                            onChange={(event) => setLocalThreshold(Number(event.target.value))}
                            onMouseUp={commitThreshold}
                            onTouchEnd={commitThreshold}
                            onBlur={commitThreshold}
                            disabled={!voiceprintEnabled}
                            style={{ width: "100%", accentColor: "#4f46e5" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#9ca3af", marginTop: "4px" }}>
                            <span>低阈值=容易通过</span>
                            <span>高阈值=严格过滤</span>
                        </div>
                    </div>

                    <div>
                        <label htmlFor="voiceprint-profile" style={{ display: "block", fontSize: "13px", color: "#6b7280", marginBottom: "4px" }}>
                            当前声纹
                        </label>
                        <input
                            id="voiceprint-profile"
                            type="text"
                            value={localProfile}
                            onChange={(event) => setLocalProfile(event.target.value)}
                            onBlur={() => commitProfile()}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                    commitProfile();
                                }
                            }}
                            style={inputStyle}
                            placeholder="default"
                        />
                    </div>

                    {voiceprintStatus && (
                        <div
                            style={{
                                fontSize: "12px",
                                padding: "8px",
                                borderRadius: "6px",
                                backgroundColor: voiceprintLoaded ? "#d1fae5" : "#fef3c7",
                                color: voiceprintLoaded ? "#065f46" : "#92400e",
                                textAlign: "center",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: "6px",
                            }}
                        >
                            <ShieldCheck size={14} />
                            <span>{voiceprintStatus}</span>
                        </div>
                    )}
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#374151", marginBottom: "10px" }}>
                    声纹注册管理
                </h3>
                <div style={{ backgroundColor: "white", padding: "15px", borderRadius: "8px", border: "1px solid #e5e7eb" }}>
                    <VoiceprintProfileManager
                        apiBaseUrl={apiBaseUrl}
                        selectedProfile={voiceprintProfile}
                        onProfileSelect={async (profileName) => {
                            setLocalProfile(profileName);
                            await handleVoiceprintProfileChange(profileName);
                        }}
                        onRefreshStatus={refreshVoiceData}
                    />
                </div>
            </div>
        </div>
    );
};
