import type { BackendState } from "../platform/electron";
import { useState } from "react";
import { openLogs, retryBackend } from "../platform/electron";

interface StartupStatusProps {
    backendState: BackendState;
    isSettingsLoaded: boolean;
}

export function StartupStatus({ backendState, isSettingsLoaded }: StartupStatusProps) {
    const [actionMessage, setActionMessage] = useState("");
    const [retrying, setRetrying] = useState(false);
    if (isSettingsLoaded && backendState.status === "ready") return null;

    const label = backendState.status === "error"
        ? "后端启动失败"
        : backendState.status === "ready"
            ? "加载中"
            : "正在启动";
    const detail = backendState.status === "error"
        ? backendState.errorMessage || "请检查调试控制台"
        : isSettingsLoaded
            ? "正在连接核心服务"
            : "正在准备界面";

    return (
        <div style={{
            position: "absolute",
            top: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 200,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "auto",
        }}>
            <div style={{
                maxWidth: "420px",
                padding: "10px 14px",
                borderRadius: backendState.status === "error" ? "16px" : "999px",
                background: "rgba(255, 255, 255, 0.78)",
                border: "1px solid rgba(255, 255, 255, 0.55)",
                backdropFilter: "blur(12px)",
                boxShadow: "0 12px 32px rgba(15, 23, 42, 0.12)",
                color: "#334155",
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{
                        width: "12px",
                        height: "12px",
                        borderRadius: "999px",
                        backgroundColor: backendState.status === "error" ? "#ef4444" : "#f59e0b",
                        boxShadow: backendState.status === "error"
                            ? "0 0 16px rgba(239, 68, 68, 0.35)"
                            : "0 0 16px rgba(245, 158, 11, 0.35)",
                    }} />
                    <div style={{ fontSize: "14px", fontWeight: 700 }}>{label}</div>
                    <div style={{
                        fontSize: "13px",
                        color: "#64748b",
                        maxWidth: backendState.status === "error" ? "340px" : "280px",
                        whiteSpace: backendState.status === "error" ? "normal" : "nowrap",
                        overflowWrap: "anywhere",
                    }}>
                        {detail}
                    </div>
                </div>
                {backendState.status === "error" && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, paddingLeft: 24, flexWrap: "wrap" }}>
                        <button type="button" disabled={retrying} onClick={() => {
                            setRetrying(true);
                            setActionMessage("");
                            void retryBackend().catch(() => setActionMessage("重新启动失败，请查看日志。 ")).finally(() => setRetrying(false));
                        }} style={actionButtonStyle}>{retrying ? "正在重试…" : "重新启动"}</button>
                        <button type="button" onClick={() => void navigator.clipboard.writeText(detail).then(() => setActionMessage("详情已复制"))} style={actionButtonStyle}>复制详情</button>
                        <button type="button" onClick={() => void openLogs().catch(() => setActionMessage("无法打开日志目录。 "))} style={actionButtonStyle}>打开日志</button>
                        {actionMessage && <span role="status" style={{ fontSize: 12, color: "#64748b" }}>{actionMessage}</span>}
                    </div>
                )}
            </div>
        </div>
    );
}

const actionButtonStyle: React.CSSProperties = {
    border: "1px solid rgba(71,85,105,.22)",
    borderRadius: 8,
    background: "white",
    color: "#475569",
    padding: "6px 9px",
    cursor: "pointer",
    fontSize: 12,
};
