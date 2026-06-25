import React from "react";
import { CharacterProfile } from "@core/llm/types";

import { AvatarRendererRef } from "../core/avatar/types";
import { useVoiceManager } from "../hooks/useVoiceManager";
import { GeneralSettingsInput, GeneralSettingsPatch } from "../hooks/useSettings";
import { RuntimeConfig } from "../runtime/runtimeConfig";
import DataViewer from "./DataViewer";
import LLMConfigModal from "./LLMConfig/LLMConfigModal";
import type { LlmProviderId, LlmSettingsChangeHandler } from "./LLMConfig/types";
import MotionTester from "./MotionTester";
import SettingsModal, { SettingsTab } from "./SettingsModal";

interface SettingsLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    initialTab?: SettingsTab;
    activeCharacter?: CharacterProfile;
    currentSettings: GeneralSettingsInput;
    onSaveCharacter: (character: CharacterProfile) => Promise<boolean>;
    onChange: (settings: GeneralSettingsPatch) => Promise<void>;
}

interface MotionTesterLayerConfig {
    isOpen: boolean;
    onClose: () => void;
}

interface MemoryInspectorLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    activeCharacterId: string | null;
}

interface LlmConfigLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    currentSettings: {
        providerId?: LlmProviderId;
        apiKey: string;
        apiBaseUrl: string;
        modelName: string;
        temperature: number;
        thinkingEnabled: boolean;
        historyLimit?: number;
        overflowStrategy?: "slide" | "reset";
        topP?: number;
        presencePenalty?: number;
        frequencyPenalty?: number;
    };
    onSettingsChange: LlmSettingsChangeHandler;
    activeCharacterId: string | null;
}

interface ModalLayerProps {
    settings: SettingsLayerConfig;
    motionTester: MotionTesterLayerConfig;
    memoryInspector: MemoryInspectorLayerConfig;
    llmConfig: LlmConfigLayerConfig;
    avatarRef: React.RefObject<AvatarRendererRef>;
    runtimeConfig: RuntimeConfig;
}

export const ModalLayer: React.FC<ModalLayerProps> = ({
    settings,
    motionTester,
    memoryInspector,
    llmConfig,
    avatarRef,
    runtimeConfig,
}) => {
    const voiceManagerData = useVoiceManager(
        settings.isOpen,
        runtimeConfig,
    );

    return (
        <>
            <SettingsModal
                isOpen={settings.isOpen}
                onClose={settings.onClose}
                initialTab={settings.initialTab}
                activeCharacter={settings.activeCharacter}
                currentSettings={settings.currentSettings}
                apiBaseUrl={runtimeConfig.apiBaseUrl}
                onSaveCharacter={settings.onSaveCharacter}
                onChange={settings.onChange}
                voiceManagerData={voiceManagerData}
            />

            <MotionTester
                isOpen={motionTester.isOpen}
                onClose={motionTester.onClose}
                onTriggerMotion={(group, index) =>
                    avatarRef.current?.motion?.(group, index)
                }
            />

            <DataViewer
                isOpen={memoryInspector.isOpen}
                onClose={memoryInspector.onClose}
                activeCharacterId={memoryInspector.activeCharacterId}
                apiBaseUrl={runtimeConfig.apiBaseUrl}
            />

            <LLMConfigModal
                isOpen={llmConfig.isOpen}
                onClose={llmConfig.onClose}
                currentLlmSettings={llmConfig.currentSettings}
                onSettingsChange={llmConfig.onSettingsChange}
                activeCharacterId={llmConfig.activeCharacterId}
                apiBaseUrl={runtimeConfig.apiBaseUrl}
            />
        </>
    );
};
