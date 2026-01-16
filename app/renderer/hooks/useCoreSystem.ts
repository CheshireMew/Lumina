import { useState, useRef, useCallback, useEffect } from "react";
import { useCharacterState } from "./useCharacterState";
import { useSettings } from "./useSettings";
import { useAudioPipeline } from "./useAudioPipeline";
import { useChatStream } from "./useChatStream";
import { useGateway } from "./useGateway";
import { API_CONFIG } from "../config";
import { Message } from "@core/llm/types";
import { AvatarRendererRef } from "../core/avatar/types";

export const useCoreSystem = (
    avatarRef: React.RefObject<AvatarRendererRef>
) => {
    // Basic Hooks
    const {
        characters,
        activeCharacterId,
        activeCharacter,
        switchCharacter,
        setCharacters,
        updateCharacterModel,
        saveCharacters,
    } = useCharacterState();
    const {
        settings,
        isLoaded: isSettingsLoaded,
        updateLLMSettings,
        saveSetting,
    } = useSettings();
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

    // Local State
    const [isProcessing, setIsProcessing] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const conversationHistoryRef = useRef<Message[]>([]);
    const isProcessingRef = useRef(false);

    // --- Gateway Callbacks ---
    const handleChatStart = useCallback(
        (mode: string) => {
            console.log(`[Core] Chat Start (mode: ${mode})`);
            isProcessingRef.current = true;
            setIsProcessing(true);
            setIsStreaming(true);
            resetStream();

            if (settings.isTTSEnabled) {
                initPipeline((sentence, index) => {
                    enqueueSynthesis(sentence, index);
                });
            }
        },
        [settings.isTTSEnabled, resetStream, initPipeline, enqueueSynthesis]
    );

    const handleChatStream = useCallback(
        (token: string) => {
            processToken(token, "content", (emotion) => {
                avatarRef.current?.setEmotion?.(emotion);
            });

            if (settings.isTTSEnabled) {
                feedToken(token);
            }
        },
        [processToken, settings.isTTSEnabled, feedToken]
    );

    const handleChatEnd = useCallback(() => {
        console.log("[Core] Chat End");
        isProcessingRef.current = false;
        setIsProcessing(false);
        setIsStreaming(false);

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
            conversationHistoryRef.current.push(msg);
        }
    }, [settings.isTTSEnabled, flush, getFinalContent]);

    const handleEmotion = useCallback(
        (emotion: string) => {
            console.log("[Core] Emotion:", emotion);
            avatarRef.current?.setEmotion?.(emotion);
        },
        [avatarRef]
    );

    // Initialize Gateway
    const { isConnected, send } = useGateway({
        onChatStart: handleChatStart,
        onChatStream: handleChatStream,
        onChatEnd: handleChatEnd,
        onEmotion: handleEmotion,
        baseUrl: API_CONFIG.BASE_URL,
    });

    // --- Actions ---
    const sendMessage = useCallback(
        async (text: string) => {
            if (!text.trim() || isProcessingRef.current) return;

            const userMsg: Message = {
                role: "user",
                content: text,
                timestamp: Date.now(),
            };
            conversationHistoryRef.current.push(userMsg);

            isProcessingRef.current = true;
            setIsProcessing(true);

            send("chat", {
                text,
                character_id: activeCharacterId,
                user_name: settings.userName,
                model: settings.llm.model,
            });
        },
        [activeCharacterId, settings.userName, send]
    );

    const interrupt = useCallback(() => {
        clearAudio();
        avatarRef.current?.stopExpression?.();
    }, [clearAudio, avatarRef]);

    // Character Switch Logic wrapping
    const handleSwitchCharacter = useCallback(
        async (newId: string) => {
            await switchCharacter(newId);
            conversationHistoryRef.current = [];
            resetStream();
        },
        [switchCharacter, resetStream]
    );

    // Return unified interface
    return {
        // State
        activeCharacter,
        activeCharacterId,
        characters,
        settings,
        isSettingsLoaded,
        isProcessing,
        isStreaming,
        displayMessage,
        reasoningContent,
        isConnected,

        // Actions
        sendMessage,
        interrupt,
        switchCharacter: handleSwitchCharacter,
        setCharacters,
        updateCharacterModel,
        saveCharacters,
        updateLLMSettings,
        saveSetting,

        // Refs (if needed exposed)
        conversationHistoryRef,
    };
};
