import { useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "@core/llm/types";
import { useChatStore } from "../../store/useChatStore";
import { companionClient } from "./companionClient";

interface CompanionHistoryOptions {
    baseUrl: string;
    isConnected: boolean;
    isSettingsLoaded: boolean;
    activeCharacterId: string | null;
    userName: string;
}

export function useCompanionHistory({
    baseUrl,
    isConnected,
    isSettingsLoaded,
    activeCharacterId,
    userName,
}: CompanionHistoryOptions) {
    const mergeHistory = useChatStore((state) => state.mergeHistory);
    const sessionId = useChatStore((state) => state.sessionId);
    const requestVersionRef = useRef(0);
    const [reloadToken, setReloadToken] = useState(0);
    const [historyError, setHistoryError] = useState("");

    const retryHistory = useCallback(() => {
        setHistoryError("");
        setReloadToken((current) => current + 1);
    }, []);

    useEffect(() => {
        if (!isConnected || !isSettingsLoaded || !activeCharacterId || sessionId <= 0) {
            return;
        }

        const requestVersion = ++requestVersionRef.current;
        setHistoryError("");
        void companionClient
            .fetchHistory(baseUrl, {
                characterId: activeCharacterId,
                userName,
                sessionId,
            })
            .then((history) => {
                if (requestVersionRef.current !== requestVersion) return;
                const normalized: Message[] = history.messages.map((message, index) => ({
                    id: message.id || `${message.turn_id || "legacy"}:${message.role}:${index}`,
                    turnId: message.turn_id || undefined,
                    role: message.role,
                    content: message.content,
                    reasoning: message.reasoning || "",
                    timestamp: message.created_at ? Date.parse(message.created_at) : index,
                    status: "completed",
                }));
                mergeHistory(normalized);
            })
            .catch((error) => {
                console.warn("[CompanionRuntime] History load failed:", error);
                if (requestVersionRef.current === requestVersion) {
                    setHistoryError("历史消息暂时无法加载，本次对话仍可继续。 ");
                }
            });

        return () => {
            requestVersionRef.current += 1;
        };
    }, [activeCharacterId, baseUrl, isConnected, isSettingsLoaded, mergeHistory, reloadToken, sessionId, userName]);

    return { historyError, retryHistory };
}
