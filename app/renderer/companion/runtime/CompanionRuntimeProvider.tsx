import React, { createContext, useContext, useMemo } from "react";
import { AvatarRendererRef } from "../../core/avatar/types";
import { useCharacterProfile } from "../../hooks/useCharacterProfile";
import { GeneralSettingsPatch, useSettings } from "../../hooks/useSettings";
import type { ChatSendRequest } from "@core/llm/types";
import { useCompanionChatRuntime } from "./useCompanionChatRuntime";

interface CompanionRuntimeContextValue {
    activeCharacter: ReturnType<typeof useCharacterProfile>["activeCharacter"];
    activeCharacterId: ReturnType<typeof useCharacterProfile>["activeCharacterId"];
    settings: ReturnType<typeof useSettings>["settings"];
    isSettingsLoaded: boolean;
    isConnected: boolean;
    sendMessage: (input: string | ChatSendRequest) => boolean;
    retryTurn: (turnId: string) => boolean;
    interrupt: () => void;
    resetSession: () => void;
    historyError: string;
    retryHistory: () => void;
    saveCharacter: ReturnType<typeof useCharacterProfile>["saveCharacter"];
    updateLLMSettings: ReturnType<typeof useSettings>["updateLLMSettings"];
    saveGeneralSettings: (next: GeneralSettingsPatch) => Promise<void>;
    setTtsEnabled: (enabled: boolean) => Promise<void>;
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
        setTtsEnabled,
    } = useSettings(backendReady, baseUrl);
    const chat = useCompanionChatRuntime({
        avatarRef,
        baseUrl,
        backendReady,
        activeCharacter,
        activeCharacterId,
        settings,
        isSettingsLoaded,
    });

    const value = useMemo<CompanionRuntimeContextValue>(
        () => ({
            activeCharacter,
            activeCharacterId,
            settings,
            isSettingsLoaded,
            ...chat,
            saveCharacter,
            updateLLMSettings,
            saveGeneralSettings,
            setTtsEnabled,
        }),
        [
            activeCharacter,
            activeCharacterId,
            isSettingsLoaded,
            saveCharacter,
            saveGeneralSettings,
            setTtsEnabled,
            settings,
            updateLLMSettings,
            chat,
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
