import React, { useEffect, useState } from "react";
import { Mic, Save, Settings, X } from "lucide-react";

import { VoiceManagerData } from "../hooks/useVoiceManager";
import { GeneralSettingsInput } from "../hooks/useSettings";
import { GeneralSettingsPanel } from "./Settings/GeneralSettingsPanel";
import { VoiceTab } from "./Settings/VoiceTab";
import { useSettingsModalState } from "./Settings/useSettingsModalState";

export type SettingsTab = "general" | "voice";

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    initialTab?: SettingsTab;
    voiceManagerData: VoiceManagerData;
    currentSettings: GeneralSettingsInput;
    onSave: (settings: GeneralSettingsInput) => Promise<void>;
}

const SettingsModal: React.FC<SettingsModalProps> = ({
    isOpen,
    onClose,
    initialTab = "general",
    voiceManagerData,
    currentSettings,
    onSave,
}) => {
    const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
    const {
        userName,
        setUserName,
        highDpiEnabled,
        setHighDpiEnabled,
        backgroundImage,
        setBackgroundImage,
        isSaving,
        fileInputRef,
        handleBackgroundFileSelect,
        handleSave,
    } = useSettingsModalState({
        isOpen,
        currentSettings,
        onSave,
        onClose,
    });

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
        width: "900px",
        height: "700px",
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
    });

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
            <div style={glassPanelStyle}>
                <div
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
                            Settings
                        </span>
                    </h2>

                    <div style={{ flex: 1 }}>
                        <div
                            onClick={() => setActiveTab("general")}
                            style={tabStyle(activeTab === "general")}
                        >
                            <Settings size={18} /> <span>General</span>
                        </div>
                        <div
                            onClick={() => setActiveTab("voice")}
                            style={tabStyle(activeTab === "voice")}
                        >
                            <Mic size={18} /> <span>Voice</span>
                        </div>
                    </div>

                    <button
                        onClick={onClose}
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
                        <X size={18} /> Close
                    </button>
                    <button
                        onClick={() => {
                            void handleSave();
                        }}
                        disabled={isSaving}
                        style={{
                            marginTop: "10px",
                            padding: "12px",
                            borderRadius: "16px",
                            background: "linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)",
                            color: "white",
                            border: "none",
                            cursor: "pointer",
                            fontWeight: 600,
                            boxShadow: "0 4px 12px rgba(79, 70, 229, 0.3)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "8px",
                        }}
                    >
                        {isSaving ? <span className="spinner">...</span> : <Save size={18} />}
                        {isSaving ? "Saving..." : "Save Changes"}
                    </button>
                </div>

                <div style={{ flex: 1, padding: "40px", overflowY: "auto" }}>
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
                        {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Settings
                    </h2>

                    {activeTab === "general" && (
                        <GeneralSettingsPanel
                            userName={userName}
                            setUserName={setUserName}
                            backgroundImage={backgroundImage}
                            setBackgroundImage={setBackgroundImage}
                            highDpiEnabled={highDpiEnabled}
                            setHighDpiEnabled={setHighDpiEnabled}
                            fileInputRef={fileInputRef}
                            onBackgroundFileSelect={handleBackgroundFileSelect}
                        />
                    )}
                    {activeTab === "voice" && <VoiceTab {...voiceManagerData} />}
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
            `}</style>
        </div>
    );
};

export default SettingsModal;
