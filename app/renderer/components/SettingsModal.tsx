import React, { useEffect, useState } from "react";
import { CharacterProfile } from "@core/llm/types";
import { Fingerprint, Mic, Settings, UserRound, X } from "lucide-react";

import { VoiceManagerData } from "../hooks/useVoiceManager";
import { GeneralSettingsInput, GeneralSettingsPatch } from "../hooks/useSettings";
import { useDialogAccessibility } from "../hooks/useDialogAccessibility";
import { CharacterTab } from "./Settings/CharacterTab";
import { GeneralSettingsPanel } from "./Settings/GeneralSettingsPanel";
import { VoiceTab } from "./Settings/VoiceTab";
import { VoiceprintTab } from "./Settings/VoiceprintTab";
import { useSettingsModalState } from "./Settings/useSettingsModalState";

export type SettingsTab = "general" | "character" | "voice" | "voiceprint";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    initialTab?: SettingsTab;
    voiceManagerData: VoiceManagerData;
    activeCharacter?: CharacterProfile;
    currentSettings: GeneralSettingsInput;
    apiBaseUrl: string;
    onSaveCharacter: (character: CharacterProfile) => Promise<boolean>;
    onChange: (settings: GeneralSettingsPatch) => Promise<void>;
}

const SettingsModal: React.FC<SettingsModalProps> = ({
    isOpen,
    onClose,
    initialTab = "general",
    voiceManagerData,
    activeCharacter,
    currentSettings,
    apiBaseUrl,
    onSaveCharacter,
    onChange,
}) => {
    const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
    const [characterDirty, setCharacterDirty] = useState(false);
    const {
        userName,
        setUserName,
        highDpiEnabled,
        setHighDpiEnabled,
        ttsEnabled,
        setTtsEnabled,
        backgroundImage,
        setBackgroundImage,
        fileInputRef,
        handleBackgroundFileSelect,
        isDirty: generalDirty,
        save: saveGeneral,
        reset: resetGeneral,
        saveStatus,
        saveMessage,
    } = useSettingsModalState({
        currentSettings,
        onChange,
    });

    const hasUnsavedChanges = generalDirty || characterDirty;
    const confirmDiscard = () => !hasUnsavedChanges || window.confirm("有尚未保存的更改，确定放弃这些更改吗？");
    const requestClose = () => {
        if (confirmDiscard()) onClose();
    };
    const handleTabChange = (nextTab: SettingsTab) => {
        if (nextTab === activeTab) return;
        const currentTabDirty = activeTab === "general" ? generalDirty : activeTab === "character" ? characterDirty : false;
        if (currentTabDirty && !window.confirm("当前页面有尚未保存的更改，确定放弃并切换吗？")) return;
        if (activeTab === "general" && generalDirty) resetGeneral();
        setCharacterDirty(false);
        setActiveTab(nextTab);
    };
    const dialogRef = useDialogAccessibility<HTMLDivElement>(isOpen, requestClose);

    useEffect(() => {
        if (isOpen) {
            setActiveTab(initialTab);
        }
    }, [initialTab, isOpen]);

    if (!isOpen) {
        return null;
    }

    const glassPanelStyle: React.CSSProperties = {
        backgroundColor: "rgba(255, 255, 255, 0.75)",
        backdropFilter: "blur(20px)",
        borderRadius: "24px",
        border: "1px solid rgba(255, 255, 255, 0.6)",
        boxShadow: "0 20px 50px rgba(0,0,0,0.1), inset 0 0 20px rgba(255,255,255,0.5)",
        width: "min(900px, calc(100vw - 32px))",
        height: "min(700px, calc(100vh - 32px))",
        display: "flex",
        overflow: "hidden",
        color: "#4B5563",
        transform: "translateY(0)",
        animation: "slideUp 0.3s ease-out",
    };

    const tabStyle = (isActive: boolean): React.CSSProperties => ({
        padding: "12px 20px",
        borderRadius: "16px",
        cursor: "pointer",
        fontSize: "15px",
        fontWeight: 600,
        color: isActive ? "#fff" : "#6B7280",
        background: isActive ? "linear-gradient(135deg, #F472B6 0%, #DB2777 100%)" : "transparent",
        boxShadow: isActive ? "0 4px 12px rgba(219, 39, 119, 0.3)" : "none",
        transition: "all 0.2s ease",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginBottom: "8px",
        width: "100%",
        border: "none",
        textAlign: "left",
    });

    const tabLabels: Record<SettingsTab, string> = {
        general: "常规",
        character: "角色",
        voice: "语音",
        voiceprint: "声纹",
    };

    return (
        <div
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(0,0,0,0.3)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                zIndex: 3000,
                backdropFilter: "blur(5px)",
            }}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="lumina-settings-title"
                tabIndex={-1}
                className="lumina-settings-panel"
                style={glassPanelStyle}
            >
                <div
                    className="lumina-settings-sidebar"
                    style={{
                        width: "240px",
                        background: "rgba(255,255,255,0.4)",
                        borderRight: "1px solid rgba(255,255,255,0.5)",
                        padding: "30px 20px",
                        display: "flex",
                        flexDirection: "column",
                    }}
                >
                    <h2
                        id="lumina-settings-title"
                        style={{
                            fontSize: "24px",
                            fontWeight: 800,
                            color: "#374151",
                            marginBottom: "30px",
                            paddingLeft: "10px",
                            background: "linear-gradient(to right, #ec4899, #8b5cf6)",
                            WebkitBackgroundClip: "text",
                            WebkitTextFillColor: "transparent",
                        }}
                    >
                        Lumina{" "}
                        <span
                            style={{
                                fontSize: "14px",
                                opacity: 0.6,
                                fontWeight: 500,
                            }}
                        >
                            设置
                        </span>
                    </h2>

                    <div style={{ flex: 1 }}>
                        <button
                            type="button"
                            onClick={() => handleTabChange("general")}
                            style={tabStyle(activeTab === "general")}
                            aria-pressed={activeTab === "general"}
                        >
                            <Settings size={18} /> <span>常规</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => handleTabChange("character")}
                            style={tabStyle(activeTab === "character")}
                            aria-pressed={activeTab === "character"}
                        >
                            <UserRound size={18} /> <span>角色</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => handleTabChange("voice")}
                            style={tabStyle(activeTab === "voice")}
                            aria-pressed={activeTab === "voice"}
                        >
                            <Mic size={18} /> <span>语音</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => handleTabChange("voiceprint")}
                            style={tabStyle(activeTab === "voiceprint")}
                            aria-pressed={activeTab === "voiceprint"}
                        >
                            <Fingerprint size={18} /> <span>声纹</span>
                        </button>
                    </div>

                    <button
                        onClick={requestClose}
                        style={{
                            padding: "12px",
                            marginTop: "20px",
                            borderRadius: "16px",
                            border: "1px solid rgba(0,0,0,0.1)",
                            background: "white",
                            color: "#6B7280",
                            cursor: "pointer",
                            fontWeight: 600,
                            transition: "all 0.2s",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "8px",
                        }}
                    >
                        <X size={18} /> 关闭
                    </button>
                </div>

                <div
                    className="lumina-settings-content"
                    style={{ flex: 1, padding: "40px", overflowY: "auto" }}
                >
                    <h2
                        style={{
                            fontSize: "20px",
                            fontWeight: 700,
                            color: "#1f2937",
                            marginBottom: "25px",
                            paddingBottom: "10px",
                            borderBottom: "2px solid rgba(0,0,0,0.05)",
                        }}
                    >
                        {tabLabels[activeTab]}设置
                    </h2>

                    {activeTab === "general" && (
                        <GeneralSettingsPanel
                            userName={userName}
                            setUserName={setUserName}
                            backgroundImage={backgroundImage}
                            setBackgroundImage={setBackgroundImage}
                            highDpiEnabled={highDpiEnabled}
                            setHighDpiEnabled={setHighDpiEnabled}
                            ttsEnabled={ttsEnabled}
                            setTtsEnabled={setTtsEnabled}
                            fileInputRef={fileInputRef}
                            onBackgroundFileSelect={handleBackgroundFileSelect}
                            isDirty={generalDirty}
                            saveStatus={saveStatus}
                            saveMessage={saveMessage}
                            onSave={saveGeneral}
                        />
                    )}
                    {activeTab === "character" && (
                        <CharacterTab
                            apiBaseUrl={apiBaseUrl}
                            activeCharacter={activeCharacter}
                            onSaveCharacter={onSaveCharacter}
                            voiceData={voiceManagerData}
                            onDirtyChange={setCharacterDirty}
                        />
                    )}
                    {activeTab === "voice" && (
                        <div>
                            <div style={{ margin: "-14px 0 10px", fontSize: 12, color: "#64748b" }}>此页更改会立即保存。</div>
                            <VoiceTab {...voiceManagerData} />
                        </div>
                    )}
                    {activeTab === "voiceprint" && (
                        <div>
                            <div style={{ margin: "-14px 0 10px", fontSize: 12, color: "#64748b" }}>此页更改会立即保存。</div>
                            <VoiceprintTab {...voiceManagerData} />
                        </div>
                    )}
                </div>
            </div>

            <style>{`
                @keyframes slideUp {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-track { background: transparent; }
                ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }
                @media (max-width: 680px) {
                    .lumina-settings-panel { flex-direction: column; }
                    .lumina-settings-sidebar {
                        width: auto !important;
                        padding: 18px 18px 10px !important;
                        border-right: none !important;
                        border-bottom: 1px solid rgba(255,255,255,0.5);
                    }
                    .lumina-settings-sidebar h2 { margin-bottom: 14px !important; }
                    .lumina-settings-sidebar > div {
                        display: grid;
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                        gap: 6px;
                    }
                    .lumina-settings-sidebar > button { margin-top: 8px !important; }
                    .lumina-settings-content { padding: 22px !important; }
                }
            `}</style>
        </div>
    );
};

export default SettingsModal;
