import React from "react";

interface GeneralSettingsPanelProps {
    userName: string;
    setUserName: (value: string) => void;
    backgroundImage: string;
    setBackgroundImage: (value: string) => void;
    highDpiEnabled: boolean;
    setHighDpiEnabled: (value: boolean) => void;
    ttsEnabled: boolean;
    setTtsEnabled: (value: boolean) => void;
    fileInputRef: React.RefObject<HTMLInputElement>;
    onBackgroundFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
    isDirty: boolean;
    saveStatus: "idle" | "saving" | "saved" | "error";
    saveMessage: string;
    onSave: () => Promise<boolean>;
}

export const GeneralSettingsPanel: React.FC<GeneralSettingsPanelProps> = ({
    userName,
    setUserName,
    backgroundImage,
    setBackgroundImage,
    highDpiEnabled,
    setHighDpiEnabled,
    ttsEnabled,
    setTtsEnabled,
    fileInputRef,
    onBackgroundFileSelect,
    isDirty,
    saveStatus,
    saveMessage,
    onSave,
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
        boxSizing: "border-box",
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "25px" }}>
            <section>
                <label
                    htmlFor="general-user-name"
                    style={{
                        display: "block",
                        fontWeight: 600,
                        marginBottom: "8px",
                        color: "#4B5563",
                    }}
                >
                    你的称呼
                </label>
                <input
                    id="general-user-name"
                    value={userName}
                    onChange={(event) => setUserName(event.target.value)}
                    style={inputStyle}
                    placeholder="请输入希望角色使用的称呼"
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
                    htmlFor="general-background"
                    style={{
                        display: "block",
                        fontWeight: 600,
                        marginBottom: "8px",
                        color: "#4B5563",
                    }}
                >
                    背景图片
                </label>
                <div style={{ display: "flex", gap: "10px" }}>
                    <input
                        id="general-background"
                        value={backgroundImage}
                        readOnly
                        style={inputStyle}
                        placeholder="尚未选择背景图片"
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
                        type="button"
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
                        选择文件
                    </button>
                    {backgroundImage && (
                        <button
                            type="button"
                            onClick={() => setBackgroundImage("")}
                            style={{ whiteSpace: "nowrap", padding: "0 16px", borderRadius: 12, border: "1px solid rgba(0,0,0,.1)", background: "transparent", cursor: "pointer" }}
                        >
                            清除
                        </button>
                    )}
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
                        id="general-high-dpi"
                        type="checkbox"
                        checked={highDpiEnabled}
                        onChange={(event) => setHighDpiEnabled(event.target.checked)}
                        style={{ width: "20px", height: "20px", accentColor: "#ec4899" }}
                    />
                    <div>
                        <label htmlFor="general-high-dpi" style={{ fontWeight: 600, color: "#374151" }}>
                            高分辨率渲染
                        </label>
                        <div style={{ fontSize: "13px", color: "#6B7280" }}>
                            在高分屏上以更高精度绘制角色；会增加显卡负担。
                        </div>
                    </div>
                </div>
            </section>

            <section>
                <div style={{ padding: 15, background: "rgba(255,255,255,.5)", borderRadius: 12, border: "1px solid rgba(0,0,0,.05)", display: "flex", alignItems: "center", gap: 15 }}>
                    <input
                        id="general-tts"
                        type="checkbox"
                        checked={ttsEnabled}
                        onChange={(event) => setTtsEnabled(event.target.checked)}
                        style={{ width: 20, height: 20, accentColor: "#ec4899" }}
                    />
                    <div>
                        <label htmlFor="general-tts" style={{ fontWeight: 600, color: "#374151" }}>自动朗读回复</label>
                        <div style={{ fontSize: 13, color: "#6B7280" }}>开启后，新回复会自动播放语音；聊天框中也可以随时切换。</div>
                    </div>
                </div>
            </section>

            <div style={{ position: "sticky", bottom: -1, display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 10, padding: "14px 0", background: "rgba(255,255,255,.88)", backdropFilter: "blur(12px)" }}>
                {saveMessage && (
                    <div role={saveStatus === "error" ? "alert" : "status"} style={{ marginRight: "auto", fontSize: 12, color: saveStatus === "error" ? "#b91c1c" : "#047857" }}>
                        {saveMessage}
                    </div>
                )}
                <button
                    type="button"
                    onClick={() => void onSave()}
                    disabled={!isDirty || saveStatus === "saving"}
                    style={{ border: 0, borderRadius: 10, padding: "10px 16px", background: "#4f46e5", color: "white", fontWeight: 600, cursor: !isDirty || saveStatus === "saving" ? "not-allowed" : "pointer", opacity: !isDirty || saveStatus === "saving" ? .55 : 1 }}
                >
                    {saveStatus === "saving" ? "正在保存…" : "保存常规设置"}
                </button>
            </div>
        </div>
    );
};
