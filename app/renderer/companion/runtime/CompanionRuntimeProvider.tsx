import React, { createContext, useCallback, useContext, useMemo } from "react";
import { ttsService } from "@core/voice/tts_service";
import { Message } from "@core/llm/types";
import { AvatarRendererRef } from "../../core/avatar/types";
import { useAudioPipeline } from "../../hooks/useAudioPipeline";
import { useCharacterProfile } from "../../hooks/useCharacterProfile";
import { useChatStream } from "../../hooks/useChatStream";
import { useGateway } from "../../hooks/useGateway";
import { GeneralSettingsPatch, useSettings } from "../../hooks/useSettings";
import { useChatStore } from "../../store/useChatStore";
import { companionClient } from "./companionClient";

interface CompanionRuntimeContextValue {
    activeCharacter: ReturnType<typeof useCharacterProfile>["activeCharacter"];
    activeCharacterId: ReturnType<typeof useCharacterProfile>["activeCharacterId"];
    settings: ReturnType<typeof useSettings>["settings"];
    isSettingsLoaded: boolean;
    isProcessing: boolean;
    isStreaming: boolean;
    displayMessage: string;
    reasoningContent: string;
    isConnected: boolean;
    sendMessage: (text: string) => void;
    interrupt: () => void;
    resetSession: () => void;
    saveCharacter: ReturnType<typeof useCharacterProfile>["saveCharacter"];
    updateLLMSettings: ReturnType<typeof useSettings>["updateLLMSettings"];
    saveGeneralSettings: (next: GeneralSettingsPatch) => Promise<void>;
}

const CompanionRuntimeContext = createContext<CompanionRuntimeContextValue | null>(null);

interface CompanionRuntimeProviderProps {
    avatarRef: React.RefObject<AvatarRendererRef>;
    baseUrl: string;
    backendReady: boolean;
    children: React.ReactNode;
}

export function CompanionRuntimeProvider({
    avatarRef,
    baseUrl,
    backendReady,
    children,
}: CompanionRuntimeProviderProps) {
    const {
        activeCharacterId,
        activeCharacter,
        saveCharacter,
    } = useCharacterProfile(backendReady, baseUrl);
    const {
        settings,
        isLoaded: isSettingsLoaded,
        updateLLMSettings,
        saveGeneralSettings,
    } = useSettings(backendReady, baseUrl);
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

    const setProcessing = useChatStore((state) => state.setProcessing);
    const setStreaming = useChatStore((state) => state.setStreaming);
    const addMessage = useChatStore((state) => state.addMessage);
    const isProcessing = useChatStore((state) => state.isProcessing);
    const isStreaming = useChatStore((state) => state.isStreaming);

    const handleChatStart = useCallback(
        (mode: string) => {
            console.log(`[CompanionRuntime] Chat start (${mode})`);
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
            enqueueSynthesis,
            initPipeline,
            resetStream,
            setProcessing,
            setStreaming,
            settings.isTTSEnabled,
        ],
    );

    const handleChatStream = useCallback(
        (token: string) => {
            processToken(token, "content");
            if (settings.isTTSEnabled) {
                feedToken(token);
            }
        },
        [feedToken, processToken, settings.isTTSEnabled],
    );

    const handleChatEnd = useCallback(() => {
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
        addMessage,
        flush,
        getFinalContent,
        setProcessing,
        setStreaming,
        settings.isTTSEnabled,
    ]);

    const handleEmotion = useCallback(
        (emotion: string) => {
            avatarRef.current?.setEmotion?.(emotion);
        },
        [avatarRef],
    );

    const handleSessionReset = useCallback(() => {
        resetStream();
        setProcessing(false);
        setStreaming(false);
        useChatStore.getState().clearHistory();
    }, [resetStream, setProcessing, setStreaming]);

    const handleSystemStatus = useCallback(
        (status: string, details: string) => {
            if (status !== "error") {
                return;
            }

            const content = details || "AI response failed.";
            console.error("[CompanionRuntime] System error:", content);
            setProcessing(false);
            setStreaming(false);
            resetStream();
            addMessage({
                role: "system",
                content,
                timestamp: Date.now(),
            });
        },
        [addMessage, resetStream, setProcessing, setStreaming],
    );

    const transport = useGateway({
        onChatStart: handleChatStart,
        onChatStream: handleChatStream,
        onChatEnd: handleChatEnd,
        onEmotion: handleEmotion,
        onSessionReset: handleSessionReset,
        onSystemStatus: handleSystemStatus,
        baseUrl,
        enabled: backendReady,
    });

    const sendMessage = useCallback(
        (text: string) => {
            if (!text.trim() || isProcessing) {
                return;
            }

            addMessage({
                role: "user",
                content: text,
                timestamp: Date.now(),
            });
            setProcessing(true);

            companionClient.sendMessage(transport, {
                text,
                characterId: activeCharacterId ?? undefined,
                userName: settings.userName,
                model: settings.llm.model,
            });
        },
        [
            activeCharacterId,
            addMessage,
            isProcessing,
            setProcessing,
            settings.llm.model,
            settings.userName,
            transport,
        ],
    );

    const interrupt = useCallback(() => {
        companionClient.interrupt(transport);
        clearAudio();
        avatarRef.current?.stopExpression?.();
        setProcessing(false);
        setStreaming(false);
    }, [avatarRef, clearAudio, setProcessing, setStreaming, transport]);

    const resetSession = useCallback(() => {
        companionClient.resetSession(transport, {
            characterId: activeCharacterId ?? undefined,
            userName: settings.userName,
        });
    }, [activeCharacterId, settings.userName, transport]);

    React.useEffect(() => {
        if (activeCharacter?.voiceConfig?.voiceId) {
            ttsService.setDefaultVoice(activeCharacter.voiceConfig.voiceId);
        }
    }, [activeCharacter]);

    const value = useMemo<CompanionRuntimeContextValue>(
        () => ({
            activeCharacter,
            activeCharacterId,
            settings,
            isSettingsLoaded,
            isProcessing,
            isStreaming,
            displayMessage,
            reasoningContent,
            isConnected: transport.isConnected,
            sendMessage,
            interrupt,
            resetSession,
            saveCharacter,
            updateLLMSettings,
            saveGeneralSettings,
        }),
        [
            activeCharacter,
            activeCharacterId,
            displayMessage,
            interrupt,
            isProcessing,
            isSettingsLoaded,
            isStreaming,
            reasoningContent,
            resetSession,
            saveCharacter,
            saveGeneralSettings,
            sendMessage,
            settings,
            transport.isConnected,
            updateLLMSettings,
        ],
    );

    return (
        <CompanionRuntimeContext.Provider value={value}>
            {children}
        </CompanionRuntimeContext.Provider>
    );
}

export function useCompanionRuntime(): CompanionRuntimeContextValue {
    const value = useContext(CompanionRuntimeContext);
    if (!value) {
        throw new Error("useCompanionRuntime must be used inside CompanionRuntimeProvider");
    }
    return value;
}
