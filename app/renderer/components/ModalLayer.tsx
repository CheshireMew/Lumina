import React from "react";

import { AvatarRendererRef } from "../core/avatar/types";
import { useVoiceManager } from "../hooks/useVoiceManager";
import { GeneralSettingsInput } from "../hooks/useSettings";
import DataViewer from "./DataViewer";
import LLMConfigModal from "./LLMConfig/LLMConfigModal";
import type { ProviderType } from "./LLMConfig/types";
import MotionTester from "./MotionTester";
import SettingsModal, { SettingsTab } from "./SettingsModal";

interface SettingsLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    initialTab?: SettingsTab;
    currentSettings: GeneralSettingsInput;
    onSave: (settings: GeneralSettingsInput) => Promise<void>;
}

interface MotionTesterLayerConfig {
    isOpen: boolean;
    onClose: () => void;
}

interface MemoryInspectorLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    activeCharacterId: string;
}

interface LlmConfigLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    currentSettings: {
        providerType?: ProviderType;
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
    onSettingsChange: (
        apiKey: string,
        baseUrl: string,
        model: string,
        temperature: number,
        thinkingEnabled: boolean,
        historyLimit: number,
        overflowStrategy: "slide" | "reset",
        topP?: number,
        presencePenalty?: number,
        frequencyPenalty?: number,
        providerType?: ProviderType,
    ) => void;
    activeCharacterId: string;
}

interface ModalLayerProps {
    settings: SettingsLayerConfig;
    motionTester: MotionTesterLayerConfig;
    memoryInspector: MemoryInspectorLayerConfig;
    llmConfig: LlmConfigLayerConfig;
    avatarRef: React.RefObject<AvatarRendererRef>;
}

export const ModalLayer: React.FC<ModalLayerProps> = ({
    settings,
    motionTester,
    memoryInspector,
    llmConfig,
    avatarRef,
}) => {
    const voiceManagerData = useVoiceManager(
        settings.isOpen,
    );

    return (
        <>
            <SettingsModal
                isOpen={settings.isOpen}
                onClose={settings.onClose}
                initialTab={settings.initialTab}
                currentSettings={settings.currentSettings}
                onSave={settings.onSave}
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
            />

            <LLMConfigModal
                isOpen={llmConfig.isOpen}
                onClose={llmConfig.onClose}
                currentLlmSettings={llmConfig.currentSettings}
                onSettingsChange={llmConfig.onSettingsChange}
                activeCharacterId={llmConfig.activeCharacterId}
            />
        </>
    );
};
