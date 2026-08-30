import { useCallback, useState } from "react";
import type {
    RuntimeCapabilitySnapshot,
    RuntimeCapabilityState,
} from "../hooks/useRuntimeCapabilities";
import InputBox from "./InputBox";
import { ConversationHistory } from "./ConversationHistory";
import { useChatStore } from "../store/useChatStore";
import type { ChatSendRequest } from "@core/llm/types";

interface CompanionChatPanelProps {
    isBackendReady: boolean;
    visionBaseUrl: string;
    sttCapability?: RuntimeCapabilitySnapshot;
    visionCapability?: RuntimeCapabilitySnapshot;
    onSend: (text: string | ChatSendRequest) => boolean;
    onRetry: (turnId: string) => boolean;
    onInterrupt: () => void;
    onOpenModelSettings: () => void;
    isTtsEnabled: boolean;
    onToggleTts: () => void;
    historyError?: string;
    onRetryHistory?: () => void;
    modelConfigurationError?: string;
}

const capabilityStatus = (
    capability?: RuntimeCapabilitySnapshot,
): RuntimeCapabilityState => capability?.status || "unavailable";

export function CompanionChatPanel({
    isBackendReady,
    visionBaseUrl,
    sttCapability,
    visionCapability,
    onSend,
    onRetry,
    onInterrupt,
    onOpenModelSettings,
    isTtsEnabled,
    onToggleTts,
    historyError,
    onRetryHistory,
    modelConfigurationError,
}: CompanionChatPanelProps) {
    const messages = useChatStore((state) => state.messages);
    const isProcessing = useChatStore((state) => state.isProcessing);
    const [chatMode, setChatMode] = useState<"text" | "voice">("text");
    const toggleChatMode = useCallback(() => {
        setChatMode((current) => current === "text" ? "voice" : "text");
    }, []);

    return (
        <div className="companion-chat-panel" style={{
            position: "absolute",
            bottom: "50px",
            left: "50%",
            transform: "translateX(-50%)",
            width: "90%",
            maxWidth: "800px",
            backgroundColor: "rgba(255, 255, 255, 0.75)",
            backdropFilter: "blur(16px)",
            borderRadius: "24px",
            border: "1px solid rgba(255, 255, 255, 0.4)",
            boxShadow: "0 8px 32px rgba(31, 38, 135, 0.15)",
            display: "flex",
            flexDirection: "column",
            zIndex: 100,
            overflow: "hidden",
            transition: "all 0.3s ease",
            WebkitAppRegion: "no-drag",
            pointerEvents: "auto",
        } as React.CSSProperties}>
            {messages.length > 0 && (
                <ConversationHistory
                    messages={messages}
                    onRetry={(turnId) => { onRetry(turnId); }}
                    onOpenModelSettings={onOpenModelSettings}
                />
            )}

            {historyError && (
                <div role="status" style={{ padding: "8px 16px", color: "#854d0e", background: "rgba(254,249,195,.86)", fontSize: 12 }}>
                    {historyError}
                    {onRetryHistory && <button type="button" onClick={onRetryHistory} style={{ marginLeft: 8, border: 0, background: "transparent", color: "#4f46e5", cursor: "pointer" }}>重新加载</button>}
                </div>
            )}

            {modelConfigurationError && (
                <div role="alert" style={{ padding: "9px 16px", color: "#78350f", background: "rgba(254,243,199,.92)", fontSize: 13 }}>
                    {modelConfigurationError}
                    <button type="button" onClick={onOpenModelSettings} style={{ marginLeft: 8, border: 0, background: "transparent", color: "#4f46e5", cursor: "pointer" }}>打开模型设置</button>
                </div>
            )}

            {visionCapability?.status === "failed" && (
                <div
                    role="status"
                    style={{
                        padding: "8px 16px",
                        color: "#92400e",
                        background: "rgba(254, 243, 199, 0.8)",
                        borderTop: "1px solid rgba(245, 158, 11, 0.2)",
                        fontSize: "13px",
                    }}
                >
                    图片理解服务暂时不可用。
                    <button type="button" onClick={onOpenModelSettings} style={{ marginLeft: 8, border: 0, background: "transparent", color: "#4f46e5", cursor: "pointer" }}>打开模型设置</button>
                </div>
            )}

            <div style={{ width: "100%" }}>
                <InputBox
                    onSend={onSend}
                    disabled={!isBackendReady || isProcessing || Boolean(modelConfigurationError)}
                    isProcessing={isProcessing}
                    onInterrupt={onInterrupt}
                    isTtsEnabled={isTtsEnabled}
                    onToggleTts={onToggleTts}
                    embedded
                    chatMode={chatMode}
                    onToggleChatMode={toggleChatMode}
                    visionBaseUrl={visionBaseUrl}
                    voiceCapabilityState={capabilityStatus(sttCapability)}
                    visionCapabilityState={capabilityStatus(visionCapability)}
                    visionCapabilityError={visionCapability?.status === "failed" ? "图片理解服务暂时不可用" : undefined}
                />
            </div>
        </div>
    );
}
