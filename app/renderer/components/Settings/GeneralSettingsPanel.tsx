import React from "react";

interface GeneralSettingsPanelProps {
    userName: string;
    setUserName: (value: string) => void;
    backgroundImage: string;
    setBackgroundImage: (value: string) => void;
    highDpiEnabled: boolean;
    setHighDpiEnabled: (value: boolean) => void;
    fileInputRef: React.RefObject<HTMLInputElement>;
    onBackgroundFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
}

export const GeneralSettingsPanel: React.FC<GeneralSettingsPanelProps> = ({
    userName,
    setUserName,
    backgroundImage,
    setBackgroundImage,
    highDpiEnabled,
    setHighDpiEnabled,
    fileInputRef,
    onBackgroundFileSelect,
}) => {
    const inputStyle: React.CSSProperties = {
        width: "100%",
        padding: "10px 14px",
        borderRadius: "12px",
        border: "1px solid rgba(0,0,0,0.1)",
        backgroundColor: "rgba(255,255,255,0.5)",
        fontSize: "14px",
        color: "#1f2937",
        outline: "none",
        transition: "all 0.2s",
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "25px" }}>
            <section>
                <label
                    style={{
                        display: "block",
                        fontWeight: 600,
                        marginBottom: "8px",
                        color: "#4B5563",
                    }}
                >
                    Your Name
                </label>
                <input
                    value={userName}
                    onChange={(event) => setUserName(event.target.value)}
                    style={inputStyle}
                    placeholder="Master"
                    onFocus={(event) => {
                        event.target.style.borderColor = "#ec4899";
                    }}
                    onBlur={(event) => {
                        event.target.style.borderColor = "rgba(0,0,0,0.1)";
                    }}
                />
            </section>

            <section>
                <label
                    style={{
                        display: "block",
                        fontWeight: 600,
                        marginBottom: "8px",
                        color: "#4B5563",
                    }}
                >
                    Background Image
                </label>
                <div style={{ display: "flex", gap: "10px" }}>
                    <input
                        value={backgroundImage}
                        onChange={(event) => setBackgroundImage(event.target.value)}
                        style={inputStyle}
                        placeholder="Image URL or File Path..."
                    />
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={(event) => {
                            void onBackgroundFileSelect(event);
                        }}
                        style={{ display: "none" }}
                        accept="image/*"
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                            whiteSpace: "nowrap",
                            padding: "0 20px",
                            borderRadius: "12px",
                            border: "1px solid rgba(0,0,0,0.1)",
                            background: "white",
                            cursor: "pointer",
                            fontWeight: 500,
                        }}
                    >
                        Browse
                    </button>
                </div>
            </section>

            <section>
                <div
                    style={{
                        padding: "15px",
                        background: "rgba(255,255,255,0.5)",
                        borderRadius: "12px",
                        border: "1px solid rgba(0,0,0,0.05)",
                        display: "flex",
                        alignItems: "center",
                        gap: "15px",
                    }}
                >
                    <input
                        type="checkbox"
                        checked={highDpiEnabled}
                        onChange={(event) => setHighDpiEnabled(event.target.checked)}
                        style={{ width: "20px", height: "20px", accentColor: "#ec4899" }}
                    />
                    <div>
                        <div style={{ fontWeight: 600, color: "#374151" }}>
                            High-DPI Rendering
                        </div>
                        <div style={{ fontSize: "13px", color: "#6B7280" }}>
                            Enable Retina/4K support for clearer avatars.
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};
