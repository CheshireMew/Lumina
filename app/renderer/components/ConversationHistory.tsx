import React, { memo, useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "../store/useChatStore";
import { ArrowDown, Copy, RotateCcw, Settings2 } from "lucide-react";
import { RichText } from "./RichText";

interface ConversationHistoryProps {
    messages: Message[];
    onRetry: (turnId: string) => void;
    onOpenModelSettings: () => void;
}

export function ConversationHistory({
    messages,
    onRetry,
    onOpenModelSettings,
}: ConversationHistoryProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const shouldFollowRef = useRef(true);
    const [showLatest, setShowLatest] = useState(false);

    const handleScroll = useCallback(() => {
        const container = containerRef.current;
        if (!container) return;
        shouldFollowRef.current =
            container.scrollHeight - container.scrollTop - container.clientHeight < 72;
        setShowLatest(!shouldFollowRef.current);
    }, []);

    const scrollToLatest = useCallback(() => {
        const container = containerRef.current;
        if (!container) return;
        shouldFollowRef.current = true;
        setShowLatest(false);
        container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    }, []);

    useEffect(() => {
        if (!shouldFollowRef.current) return;
        const frame = window.requestAnimationFrame(() => {
            const container = containerRef.current;
            if (container) container.scrollTop = container.scrollHeight;
        });
        return () => window.cancelAnimationFrame(frame);
    }, [messages]);

    return (
        <div style={{ position: "relative" }}>
            <div
                ref={containerRef}
                onScroll={handleScroll}
                aria-live="polite"
                aria-label="对话记录"
                style={{
                    maxHeight: "38vh",
                    overflowY: "auto",
                    padding: "18px 22px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    borderBottom: "1px solid rgba(15, 23, 42, 0.08)",
                }}
            >
                {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} onRetry={onRetry} onOpenModelSettings={onOpenModelSettings} />
                ))}
            </div>
            {showLatest && (
                <button
                    type="button"
                    onClick={scrollToLatest}
                    aria-label="回到最新消息"
                    style={{
                        position: "absolute", right: 16, bottom: 12, display: "flex", alignItems: "center", gap: 5,
                        border: "1px solid rgba(99,102,241,.2)", borderRadius: 999, padding: "7px 10px",
                        background: "rgba(255,255,255,.94)", color: "#4f46e5", cursor: "pointer", boxShadow: "0 6px 18px rgba(15,23,42,.12)",
                    }}
                >
                    <ArrowDown size={14} /> 最新消息
                </button>
            )}
        </div>
    );
}

const MessageBubble = memo(function MessageBubble({
    message,
    onRetry,
    onOpenModelSettings,
}: {
    message: Message;
    onRetry: (turnId: string) => void;
    onOpenModelSettings: () => void;
}) {
    const isUser = message.role === "user";
    const isSystem = message.role === "system";
    const isThinking = message.role === "assistant" && message.status === "streaming" && !message.content;
    const canOpenSettings = ["provider_authentication_failed", "provider_payment_required", "model_unavailable"].includes(message.errorCode || "");
    const copy = () => void navigator.clipboard.writeText(message.content || message.errorMessage || "");
    return (
        <div style={{ alignSelf: isSystem ? "stretch" : isUser ? "flex-end" : "flex-start", maxWidth: isSystem ? "100%" : "82%" }}>
                    <div
                        role={isSystem ? "alert" : undefined}
                        style={{
                            padding: isSystem ? "10px 12px" : "10px 14px",
                            borderRadius: isSystem
                                ? "12px"
                                : isUser
                                    ? "16px 16px 4px 16px"
                                    : "16px 16px 16px 4px",
                            background: isSystem
                                ? "rgba(254, 226, 226, 0.88)"
                                : isUser
                                    ? "linear-gradient(135deg, #ec4899, #db2777)"
                                    : "rgba(255, 255, 255, 0.82)",
                            color: isSystem
                                ? "#991b1b"
                                : isUser
                                    ? "white"
                                    : "#334155",
                            boxShadow: isSystem
                                ? "none"
                                : "0 4px 14px rgba(15, 23, 42, 0.08)",
                            overflowWrap: "anywhere",
                            lineHeight: 1.6,
                            contentVisibility: "auto",
                            containIntrinsicSize: "48px",
                        }}
                    >
                        {message.reasoning && (
                            <details
                                style={{
                                    marginBottom: "8px",
                                    color: "#64748b",
                                    fontSize: "13px",
                                }}
                            >
                                <summary style={{ cursor: "pointer" }}>
                                    查看思考过程
                                </summary>
                                <div style={{ marginTop: "6px", whiteSpace: "pre-wrap" }}>
                                    {message.reasoning}
                                </div>
                            </details>
                        )}
                        {message.attachments?.map((attachment) => (
                            <img
                                key={attachment.id}
                                src={attachment.previewUrl}
                                alt={attachment.name}
                                style={{ display: "block", maxWidth: 220, maxHeight: 180, objectFit: "cover", borderRadius: 10, marginBottom: message.content ? 8 : 0 }}
                            />
                        ))}
                        {isThinking ? (
                            <span role="status" style={{ color: "#64748b" }}>正在思考<span aria-hidden="true">…</span></span>
                        ) : message.errorMessage ? (
                            <div>
                                <div>{message.errorMessage}</div>
                                {canOpenSettings && (
                                    <button type="button" onClick={onOpenModelSettings} style={actionButtonStyle}>
                                        <Settings2 size={13} /> 打开模型设置
                                    </button>
                                )}
                            </div>
                        ) : message.content ? (
                            isUser || isSystem ? <div style={{ whiteSpace: "pre-wrap" }}>{message.content}</div> : <RichText content={message.content} />
                        ) : message.status === "interrupted" ? (
                            <span style={{ color: "#64748b" }}>已停止生成</span>
                        ) : null}
                    </div>
                    {!isSystem && !isThinking && (
                        <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", gap: 4, marginTop: 4 }}>
                            {(message.content || message.errorMessage) && (
                                <button type="button" onClick={copy} aria-label="复制消息" title="复制消息" style={actionButtonStyle}>
                                    <Copy size={13} /> 复制
                                </button>
                            )}
                            {!isUser && message.turnId && (
                                <button type="button" onClick={() => onRetry(message.turnId!)} aria-label={message.status === "completed" ? "重新生成回复" : "重试消息"} style={actionButtonStyle}>
                                    <RotateCcw size={13} /> {message.status === "completed" ? "重新生成" : "重试"}
                                </button>
                            )}
                        </div>
                    )}
        </div>
    );
});

const actionButtonStyle: React.CSSProperties = {
    border: 0,
    background: "transparent",
    color: "#64748b",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    padding: "4px 6px",
    fontSize: 11,
};
