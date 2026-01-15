import React from 'react';
import SettingsModal from './SettingsModal';
import LLMConfigModal from './LLMConfig/LLMConfigModal';
import PluginStoreModal from './PluginStore/PluginStoreModal';
import MotionTester from './MotionTester';
import DataViewer from './DataViewer';
import AvatarSelectorModal from './AvatarSelectorModal';
import { CharacterProfile } from '@core/llm/types';
import { AvatarRendererRef } from '../core/avatar/types';

interface ModalLayerProps {
    // Visibility States
    isSettingsOpen: boolean;
    onCloseSettings: () => void;
    
    isPluginStoreOpen: boolean;
    onClosePluginStore: () => void;
    
    isMotionTesterOpen: boolean;
    onCloseMotionTester: () => void;
    
    isSurrealViewerOpen: boolean;
    onCloseSurrealViewer: () => void;
    
    isAvatarSelectorOpen: boolean;
    onCloseAvatarSelector: () => void;

    isLLMConfigOpen?: boolean;

    onOpenLLMConfig?: () => void; // New Prop
    onCloseLLMConfig?: () => void;
    currentLlmSettings?: {
        apiKey: string;
        apiBaseUrl: string;
        modelName: string;
        temperature: number;
        temperature: number;
        thinkingEnabled: boolean;
        historyLimit?: number;
        overflowStrategy?: 'slide' | 'reset';
        topP?: number;
        presencePenalty?: number;
        frequencyPenalty?: number;
    };

    // Handlers
    onClearHistory: () => void;
    onContextWindowChange: (n: number) => void;
    onLLMSettingsChange: (apiKey: string, baseUrl: string, model: string, temperature: number, thinkingEnabled: boolean, historyLimit: number, overflowStrategy: 'slide' | 'reset', topP?: number, presencePenalty?: number, frequencyPenalty?: number) => void;
    onCharactersUpdated: (chars: CharacterProfile[], activeId: string) => void;
    onUserNameUpdated: (name: string) => void;
    onLive2DHighDpiChange: (enabled: boolean) => void;
    onCharacterSwitch: (id: string) => void;
    onThinkingModeChange: (enabled: boolean) => void;
    
    // Data
    activeCharacterId: string;
    galgameEnabled: boolean;
    activeCharacter?: CharacterProfile;
    onModelSelect: (path: string) => void;
    
    // Refs
    avatarRef: React.RefObject<AvatarRendererRef>;
}

export const ModalLayer: React.FC<ModalLayerProps> = ({
    isSettingsOpen, onCloseSettings,
    isPluginStoreOpen, onClosePluginStore,
    isMotionTesterOpen, onCloseMotionTester,
    isSurrealViewerOpen, onCloseSurrealViewer,
    isAvatarSelectorOpen, onCloseAvatarSelector,

    isLLMConfigOpen, onOpenLLMConfig, onCloseLLMConfig, currentLlmSettings,
    
    onClearHistory,
    onContextWindowChange,
    onLLMSettingsChange,
    onCharactersUpdated,
    onUserNameUpdated,
    onLive2DHighDpiChange,
    onCharacterSwitch,
    onThinkingModeChange,
    
    activeCharacterId,
    galgameEnabled,
    activeCharacter,
    onModelSelect,
    avatarRef
}) => {
    return (
        <>
            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={onCloseSettings}
                onClearHistory={onClearHistory}
                onContextWindowChange={onContextWindowChange}
                onLLMSettingsChange={onLLMSettingsChange}
                onCharactersUpdated={onCharactersUpdated}
                onUserNameUpdated={onUserNameUpdated}
                onLive2DHighDpiChange={onLive2DHighDpiChange}
                onCharacterSwitch={onCharacterSwitch}
                activeCharacterId={activeCharacterId}
                onThinkingModeChange={onThinkingModeChange}
            />

            <PluginStoreModal 
                isOpen={isPluginStoreOpen} 
                onClose={onClosePluginStore} 
                onOpenLLMSettings={onOpenLLMConfig}
            />

            <MotionTester
                isOpen={isMotionTesterOpen}
                onClose={onCloseMotionTester}
                onTriggerMotion={(group, index) => avatarRef.current?.motion?.(group, index)}
            />

            <DataViewer 
                isOpen={isSurrealViewerOpen} 
                onClose={onCloseSurrealViewer} 
                activeCharacterId={activeCharacterId}
                dataSource="surreal"
            />
            
            <AvatarSelectorModal
                isOpen={isAvatarSelectorOpen}
                onClose={onCloseAvatarSelector}
                activeCharacter={activeCharacter}
                onModelSelect={onModelSelect}
            />

            <LLMConfigModal
                isOpen={isLLMConfigOpen!} 
                onClose={onCloseLLMConfig!} 
                currentLlmSettings={currentLlmSettings!}
                onSettingsChange={onLLMSettingsChange}
            />
        </>
    );
};
