import { useCallback, useEffect } from "react";
import { useCharacterProfile } from "./useCharacterProfile";
import { useSettings } from "./useSettings";
import { useAudioPipeline } from "./useAudioPipeline";
import { useChatStream } from "./useChatStream";
import { useGateway } from "./useGateway";
import { useChatStore } from "../store/useChatStore";
import { API_CONFIG } from "../config";
import { Message } from "@core/llm/types";
import { AvatarRendererRef } from "../core/avatar/types";

export const useCoreSystem = (
    avatarRef: React.RefObject<AvatarRendererRef>,
    backendReady: boolean,
) => {
    // Basic Hooks
    const {
        activeCharacterId,
        activeCharacter,
        saveCharacter,
    } = useCharacterProfile(backendReady);
    const {
        settings,
        isLoaded: isSettingsLoaded,
        updateLLMSettings,
        saveGeneralSettings,
    } = useSettings(backendReady);
    const {
        initPipeline,
        enqueueSynthesis,
        feedToken,
        flush,
        clear: clearAudio,
    } = useAudioPipeline();
    const {
        displayMessage,
        reasoningContent,
        reset: resetStream,
        processToken,
        getFinalContent,
    } = useChatStream();

    // --- Store Integration ---
    const {
        setProcessing,
        setStreaming,
        addMessage,
        // clearHistory, // Exposed if needed
        messages,
    } = useChatStore();

    // Derived state from store (or keep direct usage if performance allows)
    const isProcessing = useChatStore((state) => state.isProcessing);
    const isStreaming = useChatStore((state) => state.isStreaming);

    // --- Gateway Callbacks ---
    const handleChatStart = useCallback(
        (mode: string) => {
            console.log(`[Core] Chat Start (mode: ${mode})`);
            setProcessing(true);
            setStreaming(true);
            resetStream();

            if (settings.isTTSEnabled) {
                initPipeline((sentence, index) => {
                    enqueueSynthesis(sentence, index);
                });
            }
        },
        [
            settings.isTTSEnabled,
            resetStream,
            initPipeline,
            enqueueSynthesis,
            setProcessing,
            setStreaming,
        ],
    );

    const handleChatStream = useCallback(
        (token: string) => {
            processToken(token, "content");

            if (settings.isTTSEnabled) {
                feedToken(token);
            }
        },
        [processToken, settings.isTTSEnabled, feedToken],
    );

    const handleChatEnd = useCallback(() => {
        console.log("[Core] Chat End");
        setProcessing(false);
        setStreaming(false);

        if (settings.isTTSEnabled) {
            flush();
        }

        const finalContent = getFinalContent();
        if (finalContent) {
            const msg: Message = {
                role: "assistant",
                content: finalContent,
                timestamp: Date.now(),
            };
            addMessage(msg);
        }
    }, [
        settings.isTTSEnabled,
        flush,
        getFinalContent,
        setProcessing,
        setStreaming,
        addMessage,
    ]);

    const handleEmotion = useCallback(
        (emotion: string) => {
            console.log("[Core] Emotion:", emotion);
            avatarRef.current?.setEmotion?.(emotion);
        },
        [avatarRef],
    );

    const handleSessionReset = useCallback(
        (newId: number) => {
            console.log(`[Core] 🔄 Session Reset (ID: ${newId})`);
            resetStream();
            setProcessing(false);
            setStreaming(false);
            // Store's session ID and history handled by useGateway or Store actions if we wired it there
            // But here we might want to clear history in Store
            useChatStore.getState().clearHistory();
        },
        [resetStream, setProcessing, setStreaming],
    );

    // Initialize Gateway
    const { isConnected, send } = useGateway({
        // ... Callbacks ...
        onChatStart: handleChatStart,
        onChatStream: handleChatStream,
        onChatEnd: handleChatEnd,
        onEmotion: handleEmotion,
        onSessionReset: handleSessionReset,
        baseUrl: API_CONFIG.BASE_URL,
        enabled: backendReady,
    });

    // --- Actions ---
    const sendMessage = useCallback(
        async (text: string) => {
            if (!text.trim() || isProcessing) return;

            const userMsg: Message = {
                role: "user",
                content: text,
                timestamp: Date.now(),
            };
            addMessage(userMsg);

            setProcessing(true);

            send("input_text", {
                text,
                character_id: activeCharacterId,
                user_name: settings.userName,
                model: settings.llm.model,
            });
        },
        [
            activeCharacterId,
            settings.userName,
            settings.llm.model, // [Fix] Include model to update callback on model change
            send,
            isProcessing,
            addMessage,
            setProcessing,
        ],
    );

    const interrupt = useCallback(() => {
        clearAudio();
        avatarRef.current?.stopExpression?.();
        setProcessing(false);
        setStreaming(false);
    }, [clearAudio, avatarRef, setProcessing, setStreaming]);

    // Return unified interface
    return {
        // State
        activeCharacter,
        activeCharacterId,
        settings,
        isSettingsLoaded,
        isProcessing,
        isStreaming,
        displayMessage,
        reasoningContent,
        isConnected,
        // Expose Messages if needed
        messages,

        // Actions
        sendMessage,
        interrupt,
        saveCharacter,
        updateLLMSettings,
        saveGeneralSettings,
    };
};
