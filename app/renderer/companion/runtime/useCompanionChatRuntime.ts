import { useCallback, useMemo } from "react";
import type { ChatSendRequest } from "@core/llm/types";
import type { AvatarRendererRef } from "../../core/avatar/types";
import type { useCharacterProfile } from "../../hooks/useCharacterProfile";
import { useGateway } from "../../hooks/useGateway";
import type { useSettings } from "../../hooks/useSettings";
import { useChatStore } from "../../store/useChatStore";
import { companionClient } from "./companionClient";
import { useCharacterVoiceConfig } from "./useCharacterVoiceConfig";
import { useCompanionGatewayRuntime } from "./useCompanionGatewayRuntime";
import { useCompanionHistory } from "./useCompanionHistory";

interface UseCompanionChatRuntimeOptions {
    avatarRef: React.RefObject<AvatarRendererRef>;
    baseUrl: string;
    backendReady: boolean;
    activeCharacter: ReturnType<typeof useCharacterProfile>["activeCharacter"];
    activeCharacterId: ReturnType<typeof useCharacterProfile>["activeCharacterId"];
    settings: ReturnType<typeof useSettings>["settings"];
    isSettingsLoaded: boolean;
}

export function useCompanionChatRuntime({
    avatarRef,
    baseUrl,
    backendReady,
    activeCharacter,
    activeCharacterId,
    settings,
    isSettingsLoaded,
}: UseCompanionChatRuntimeOptions) {
    const addMessage = useChatStore((state) => state.addMessage);
    const updateMessage = useChatStore((state) => state.updateMessage);
    const startTurn = useChatStore((state) => state.startTurn);
    const finishTurn = useChatStore((state) => state.finishTurn);
    const gatewayRuntime = useCompanionGatewayRuntime({
        avatarRef,
        isTtsEnabled: settings.isTTSEnabled,
    });

    const transport = useGateway({
        onChatStart: gatewayRuntime.handleChatStart,
        onChatStream: gatewayRuntime.handleChatStream,
        onChatReasoning: gatewayRuntime.handleChatReasoning,
        onChatEnd: gatewayRuntime.handleChatEnd,
        onEmotion: gatewayRuntime.handleEmotion,
        onSessionReset: gatewayRuntime.handleSessionReset,
        onSystemStatus: gatewayRuntime.handleSystemStatus,
        baseUrl,
        enabled: backendReady,
    });

    const interrupt = useCallback(() => {
        const turnId = gatewayRuntime.activeTurnIdRef.current ?? undefined;
        void companionClient.interrupt(transport, turnId).catch((error) => {
            console.warn("[CompanionRuntime] Interrupt was not accepted:", error);
        });
        gatewayRuntime.interruptLocal();
    }, [gatewayRuntime, transport]);

    const sendMessage = useCallback(
        (input: string | ChatSendRequest): boolean => {
            const request: ChatSendRequest = typeof input === "string"
                ? { displayText: input, requestText: input }
                : input;
            const { isProcessing } = useChatStore.getState();
            if (!request.requestText.trim() || isProcessing) return false;

            const turnId = crypto.randomUUID();
            gatewayRuntime.activeTurnIdRef.current = turnId;
            addMessage({
                id: `${turnId}:user`,
                turnId,
                role: "user",
                content: request.displayText.trim() || "发送了一张图片",
                requestContent: request.requestText,
                attachments: request.attachments,
                timestamp: Date.now(),
                status: "pending",
            });
            startTurn(turnId);

            void companionClient.sendMessage(transport, {
                text: request.requestText,
                turnId,
                characterId: activeCharacterId ?? undefined,
                userName: settings.userName,
                model: settings.llm.model,
            }).then(() => {
                updateMessage(`${turnId}:user`, { status: "completed" });
            }).catch((error) => {
                finishTurn(turnId);
                if (gatewayRuntime.activeTurnIdRef.current === turnId) {
                    gatewayRuntime.activeTurnIdRef.current = null;
                }
                updateMessage(`${turnId}:user`, { status: "failed" });
                addMessage({
                    id: `${turnId}:assistant`,
                    turnId,
                    role: "assistant",
                    content: "",
                    timestamp: Date.now(),
                    status: "failed",
                    errorCode: "gateway_unavailable",
                    errorMessage: "消息未能送达，请检查服务状态后重试。",
                });
            });
            return true;
        },
        [activeCharacterId, addMessage, finishTurn, gatewayRuntime.activeTurnIdRef, settings.llm.model, settings.userName, startTurn, transport, updateMessage],
    );

    const retryTurn = useCallback((turnId: string): boolean => {
        const userMessage = useChatStore.getState().messages.find(
            (message) => message.turnId === turnId && message.role === "user",
        );
        if (!userMessage) return false;
        return sendMessage({
            displayText: userMessage.content,
            requestText: userMessage.requestContent || userMessage.content,
            attachments: userMessage.attachments,
        });
    }, [sendMessage]);

    const resetSession = useCallback(() => {
        void companionClient.resetSession(transport, {
            characterId: activeCharacterId ?? undefined,
            userName: settings.userName,
        }).catch((error) => {
            console.warn("[CompanionRuntime] Session reset failed:", error);
            addMessage({
                id: `system:${crypto.randomUUID()}`,
                role: "system",
                content: "无法开始新会话，请检查服务状态后重试。",
                timestamp: Date.now(),
                status: "failed",
            });
        });
    }, [activeCharacterId, addMessage, settings.userName, transport]);

    const history = useCompanionHistory({
        baseUrl,
        isConnected: transport.isConnected,
        isSettingsLoaded,
        activeCharacterId,
        userName: settings.userName,
    });
    useCharacterVoiceConfig(activeCharacter);

    return useMemo(
        () => ({
            isConnected: transport.isConnected,
            sendMessage,
            retryTurn,
            interrupt,
            resetSession,
            ...history,
        }),
        [
            interrupt,
            resetSession,
            retryTurn,
            sendMessage,
            transport.isConnected,
            history,
        ],
    );
}
