import React from "react";

import { CharacterProfile } from "@core/llm/types";

import { AvatarRendererRef } from "../core/avatar/types";
import { CapabilityPackageSnapshot } from "../hooks/useCapabilityPackages";
import { useVoiceManager } from "../hooks/useVoiceManager";
import { GeneralSettingsInput } from "../hooks/useSettings";
import AvatarSelectorModal from "./AvatarSelectorModal";
import DataViewer from "./DataViewer";
import LLMConfigModal from "./LLMConfig/LLMConfigModal";
import type { ProviderType } from "./LLMConfig/types";
import MotionTester from "./MotionTester";
import PluginStoreModal from "./PluginStore/PluginStoreModal";
import SettingsModal, { SettingsTab } from "./SettingsModal";

interface SettingsLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    initialTab?: SettingsTab;
    currentSettings: GeneralSettingsInput;
    onSave: (settings: GeneralSettingsInput) => Promise<void>;
}

interface PluginStoreLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    onOpenLlmSettings?: () => void;
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

interface AvatarSelectorLayerConfig {
    isOpen: boolean;
    onClose: () => void;
    activeCharacterId: string;
    activeCharacter?: CharacterProfile;
    live2dPackage?: CapabilityPackageSnapshot;
    characters: CharacterProfile[];
    setCharacters: (chars: CharacterProfile[]) => void;
    onActivateCharacter: (id: string) => void;
    onSaveCharacters: (chars: CharacterProfile[], deletedIds: string[]) => Promise<void>;
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
    pluginStore: PluginStoreLayerConfig;
    motionTester: MotionTesterLayerConfig;
    memoryInspector: MemoryInspectorLayerConfig;
    avatarSelector: AvatarSelectorLayerConfig;
    llmConfig: LlmConfigLayerConfig;
    avatarRef: React.RefObject<AvatarRendererRef>;
}

export const ModalLayer: React.FC<ModalLayerProps> = ({
    settings,
    pluginStore,
    motionTester,
    memoryInspector,
    avatarSelector,
    llmConfig,
    avatarRef,
}) => {
    const voiceManagerData = useVoiceManager(
        settings.isOpen || avatarSelector.isOpen,
    );

    const handleDeleteCharacter = (id: string) => {
        avatarSelector.setCharacters(
            avatarSelector.characters.filter((character) => character.id !== id),
        );
    };

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

            <PluginStoreModal
                isOpen={pluginStore.isOpen}
                onClose={pluginStore.onClose}
                onOpenLLMSettings={pluginStore.onOpenLlmSettings}
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

            <AvatarSelectorModal
                isOpen={avatarSelector.isOpen}
                onClose={avatarSelector.onClose}
                activeCharacterId={avatarSelector.activeCharacterId}
                activeCharacter={avatarSelector.activeCharacter}
                live2dPackage={avatarSelector.live2dPackage}
                characters={avatarSelector.characters}
                setCharacters={avatarSelector.setCharacters}
                onActivateCharacter={avatarSelector.onActivateCharacter}
                onDeleteCharacter={handleDeleteCharacter}
                onSaveCharacters={avatarSelector.onSaveCharacters}
                edgeVoices={voiceManagerData.edgeVoices}
                gptVoices={voiceManagerData.gptVoices}
                activeTtsEngines={voiceManagerData.activeTtsEngines}
                ttsPlugins={voiceManagerData.ttsPlugins}
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
