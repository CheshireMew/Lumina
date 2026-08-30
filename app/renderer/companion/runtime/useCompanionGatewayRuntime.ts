import { useCallback, useEffect, useRef } from "react";
import type { AvatarRendererRef } from "../../core/avatar/types";
import { useAudioPipeline } from "../../hooks/useAudioPipeline";
import { useChatStream } from "../../hooks/useChatStream";
import { useChatStore } from "../../store/useChatStore";
import { FrameMessageUpdateBatcher } from "./messageUpdateBatcher";
import type { GatewaySystemStatus } from "../../runtime/gatewayProtocol";

interface CompanionGatewayRuntimeOptions {
    avatarRef: React.RefObject<AvatarRendererRef>;
    isTtsEnabled: boolean;
}

export function useCompanionGatewayRuntime({
    avatarRef,
    isTtsEnabled,
}: CompanionGatewayRuntimeOptions) {
    const {
        initPipeline,
        enqueueSynthesis,
        feedToken,
        flush,
        clear: clearAudio,
    } = useAudioPipeline();
    const {
        start: startStream,
        reset: resetStream,
        processToken,
        finish: finishStream,
    } = useChatStream();
    const upsertMessage = useChatStore((state) => state.upsertMessage);
    const updateMessage = useChatStore((state) => state.updateMessage);
    const startTurn = useChatStore((state) => state.startTurn);
    const finishTurn = useChatStore((state) => state.finishTurn);
    const activeTurnIdRef = useRef<string | null>(null);
    const updateBatcherRef = useRef<FrameMessageUpdateBatcher | null>(null);
    if (updateBatcherRef.current === null) {
        updateBatcherRef.current = new FrameMessageUpdateBatcher((turnId, buffer) => {
            updateMessage(`${turnId}:assistant`, {
                content: buffer.raw,
                reasoning: buffer.reasoning,
                status: "streaming",
            });
        });
    }

    useEffect(() => () => {
        updateBatcherRef.current?.clear();
    }, []);

    useEffect(() => {
        if (!isTtsEnabled) clearAudio();
    }, [clearAudio, isTtsEnabled]);

    const handleChatStart = useCallback(
        (turnId: string, mode: string) => {
            console.log(`[CompanionRuntime] Chat start (${mode})`);
            activeTurnIdRef.current = turnId;
            startTurn(turnId);
            startStream(turnId);
            upsertMessage({
                id: `${turnId}:assistant`,
                turnId,
                role: "assistant",
                content: "",
                reasoning: "",
                timestamp: Date.now(),
                status: "streaming",
            });

            if (isTtsEnabled) {
                initPipeline((sentence, index) =>
                    enqueueSynthesis(sentence, index),
                );
            }
        },
        [enqueueSynthesis, initPipeline, isTtsEnabled, startStream, startTurn, upsertMessage],
    );

    const handleChatStream = useCallback(
        (turnId: string, token: string) => {
            const buffer = processToken(turnId, token, "content");
            updateBatcherRef.current?.queue(turnId, buffer);
            if (isTtsEnabled) feedToken(token);
        },
        [feedToken, isTtsEnabled, processToken],
    );

    const handleChatReasoning = useCallback(
        (turnId: string, token: string) => {
            const buffer = processToken(turnId, token, "reasoning");
            updateBatcherRef.current?.queue(turnId, buffer);
        },
        [processToken],
    );

    const handleChatEnd = useCallback(
        (turnId: string, status: string) => {
            updateBatcherRef.current?.flush();
            const final = finishStream(turnId);
            const finalStatus =
                status === "interrupted" || status === "failed"
                    ? status
                    : "completed";
            const existing = useChatStore.getState().messages.find(
                (message) => message.id === `${turnId}:assistant`,
            );
            upsertMessage({
                id: `${turnId}:assistant`,
                turnId,
                role: "assistant",
                content: final.content,
                reasoning: final.reasoning,
                timestamp: existing?.timestamp ?? Date.now(),
                status: finalStatus,
            });
            finishTurn(turnId);
            if (activeTurnIdRef.current === turnId) {
                activeTurnIdRef.current = null;
            }
            if (isTtsEnabled && finalStatus === "completed") flush();
        },
        [finishStream, finishTurn, flush, isTtsEnabled, upsertMessage],
    );

    const handleEmotion = useCallback(
        (emotion: string) => avatarRef.current?.setEmotion?.(emotion),
        [avatarRef],
    );

    const handleSessionReset = useCallback(() => {
        clearAudio();
        updateBatcherRef.current?.clear();
        resetStream();
        activeTurnIdRef.current = null;
        useChatStore.getState().clearHistory();
    }, [clearAudio, resetStream]);

    const handleSystemStatus = useCallback(
        (status: GatewaySystemStatus) => {
            if (status.status !== "error") return;
            const turnId = status.turnId;
            if (turnId) {
                updateBatcherRef.current?.drop(turnId);
                resetStream(turnId);
                finishTurn(turnId);
                upsertMessage({
                    id: `${turnId}:assistant`,
                    turnId,
                    role: "assistant",
                    content: "",
                    timestamp: Date.now(),
                    status: "failed",
                    errorCode: status.code,
                    errorMessage: status.message,
                });
            }
        },
        [finishTurn, resetStream, upsertMessage],
    );

    const interruptLocal = useCallback(() => {
        const turnId = activeTurnIdRef.current;
        clearAudio();
        avatarRef.current?.stopExpression?.();
        if (!turnId) return null;
        updateBatcherRef.current?.drop(turnId);
        resetStream(turnId);
        finishTurn(turnId);
        updateMessage(`${turnId}:assistant`, { status: "interrupted" });
        activeTurnIdRef.current = null;
        return turnId;
    }, [avatarRef, clearAudio, finishTurn, resetStream, updateMessage]);

    return {
        activeTurnIdRef,
        handleChatStart,
        handleChatStream,
        handleChatReasoning,
        handleChatEnd,
        handleEmotion,
        handleSessionReset,
        handleSystemStatus,
        interruptLocal,
    };
}
