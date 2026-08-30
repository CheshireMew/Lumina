/**
 * App.tsx - Refactored Version (Stage 1)
 * 
 * Modularized with AppToolbar and ModalLayer.
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { GeneralSettingsPatch } from './hooks/useSettings';
import { CUSTOM_LLM_PROVIDER_ID, FREE_LLM_PROVIDER_ID, LlmProviderId } from './components/LLMConfig/types';

// Core Hooks
import { useBackendState } from './hooks/useBackendState';
import { useRuntimeCapabilities } from './hooks/useRuntimeCapabilities';
import { useAvatarRuntimeEvents } from './hooks/useAvatarRuntimeEvents';
import { transformImageSrc } from './utils/srcUtils';
import { syncFrontendServiceUrls } from './runtime/appRuntime';
import { buildRuntimeConfig, RuntimeConfig } from './runtime/runtimeConfig';
import {
    CompanionRuntimeProvider,
    useCompanionRuntime,
} from './companion/runtime/CompanionRuntimeProvider';

// Avatar System
import AvatarContainer from './core/avatar/AvatarContainer';
import { AvatarRendererRef } from './core/avatar/types';

// UI Components
import { AppToolbar } from './components/AppToolbar';
import { CompanionChatPanel } from './components/CompanionChatPanel';
import { StartupStatus } from './components/StartupStatus';

const LazyModalLayer = React.lazy(() =>
    import('./components/ModalLayer').then((module) => ({
        default: module.ModalLayer,
    })),
);

function App() {
    const avatarRef = useRef<AvatarRendererRef>(null);
    const backendState = useBackendState();
    const isBackendReady = backendState.status === 'ready';
    const runtimeConfig = useMemo(
        () => buildRuntimeConfig(backendState),
        [backendState],
    );
    const runtimeCapabilities = useRuntimeCapabilities(isBackendReady, runtimeConfig.apiBaseUrl);

    useEffect(() => {
        if (Object.keys(backendState.ports).length === 0) {
            return;
        }

        console.log("🔌 [App] Syncing runtime ports:", backendState.ports);
        syncFrontendServiceUrls(runtimeConfig);
    }, [backendState.ports, runtimeConfig]);

    return (
        <CompanionRuntimeProvider
            avatarRef={avatarRef}
            baseUrl={runtimeConfig.apiBaseUrl}
            backendReady={isBackendReady}
        >
            <CompanionAppShell
                avatarRef={avatarRef}
                backendState={backendState}
                isBackendReady={isBackendReady}
                runtimeConfig={runtimeConfig}
                runtimeCapabilities={runtimeCapabilities}
            />
        </CompanionRuntimeProvider>
    );
}

interface CompanionAppShellProps {
    avatarRef: React.RefObject<AvatarRendererRef>;
    backendState: ReturnType<typeof useBackendState>;
    isBackendReady: boolean;
    runtimeConfig: RuntimeConfig;
    runtimeCapabilities: ReturnType<typeof useRuntimeCapabilities>;
}

function CompanionAppShell({
    avatarRef,
    backendState,
    isBackendReady,
    runtimeConfig,
    runtimeCapabilities,
}: CompanionAppShellProps) {
    const {
        activeCharacter, activeCharacterId,
        settings, isSettingsLoaded, saveCharacter, updateLLMSettings, saveGeneralSettings,
        sendMessage, retryTurn, interrupt, historyError, retryHistory, setTtsEnabled
    } = useCompanionRuntime();
    
    // ==================== LOCAL STATE ====================
    // Modals State
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isMotionTesterOpen, setIsMotionTesterOpen] = useState(false);
    const [isMemoryInspectorOpen, setIsMemoryInspectorOpen] = useState(false);
    const [isLLMConfigOpen, setIsLLMConfigOpen] = useState(false);
    const [settingsInitialTab, setSettingsInitialTab] = useState<'general' | 'character' | 'voice' | 'voiceprint'>('general');
    const [visibleBackgroundImage, setVisibleBackgroundImage] = useState('');
    
    // Other Refs
    // ==================== HANDLERS ====================
    const handleLLMSettingsChange = useCallback(async (apiKey: string, baseUrl: string, model: string, temperature: number, thinkingEnabled: boolean, historyLimit: number, overflowStrategy: 'slide' | 'reset', topP?: number, presencePenalty?: number, frequencyPenalty?: number, providerId: LlmProviderId = CUSTOM_LLM_PROVIDER_ID) => {
        await updateLLMSettings({ providerId, apiKey, baseUrl, model, temperature, thinkingEnabled, historyLimit, overflowStrategy, topP, presencePenalty, frequencyPenalty });
    }, [updateLLMSettings]);

    const handleSaveGeneralSettings = useCallback(async (next: GeneralSettingsPatch) => {
        await saveGeneralSettings(next);
    }, [saveGeneralSettings]);
    
    // ==================== EFFECTS ====================
    useAvatarRuntimeEvents(avatarRef, interrupt);

    useEffect(() => {
        setVisibleBackgroundImage('');

        if (!isSettingsLoaded || !settings.backgroundImage) {
            return;
        }

        const timer = window.setTimeout(() => {
            setVisibleBackgroundImage(settings.backgroundImage);
        }, 1000);

        return () => window.clearTimeout(timer);
    }, [isSettingsLoaded, settings.backgroundImage]);

    // ==================== RENDER ====================
    const sttCapability = runtimeCapabilities.stt;
    const visionCapability = runtimeCapabilities.vision;
    const resolvedModelPath = activeCharacter?.avatar?.modelUrl || "";
    const cubismCoreSrc = activeCharacter?.avatar?.cubismCoreUrl || "";
    const rendererRuntimeSrc = activeCharacter?.avatar?.rendererRuntimeUrl || "";
    const canLoadAvatar = isSettingsLoaded;
    const shouldRenderAvatar = canLoadAvatar && Boolean(resolvedModelPath);
    const hasOpenModal = isSettingsOpen
        || isMotionTesterOpen
        || isMemoryInspectorOpen
        || isLLMConfigOpen;
    const modelConfigurationError = isSettingsLoaded && !settings.llm.model.trim()
        ? '请先在模型设置中选择模型。'
        : isSettingsLoaded
            && settings.llm.providerId === FREE_LLM_PROVIDER_ID
            && !settings.llm.apiKey.trim()
            ? 'Pollinations 需要 API 密钥，配置后才能开始对话。'
            : undefined;

    return (
        <div style={{ 
            height: '100vh', 
            width: '100vw', 
            position: 'relative', 
            overflow: 'hidden',
            backgroundColor: '#f3f4f6', // Fallback color
            backgroundImage: visibleBackgroundImage ? `url("${transformImageSrc(visibleBackgroundImage)}")` : 'linear-gradient(135deg, #eef2ff 0%, #fae8ff 50%, #f0fdf4 100%)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            transition: 'background-image 0.5s ease-in-out'
        }}>
            {/* Avatar */}
            {shouldRenderAvatar ? (
                <AvatarContainer
                    ref={avatarRef}
                    modelPath={resolvedModelPath}
                    highDpi={settings.live2dHighDpi}
                    cubismCoreSrc={cubismCoreSrc}
                    rendererRuntimeSrc={rendererRuntimeSrc}
                    behavior={activeCharacter!.avatar.behavior}
                />
            ) : canLoadAvatar ? (
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                }}>
                    <div style={{
                        width: '140px',
                        height: '140px',
                        borderRadius: '999px',
                        background: 'radial-gradient(circle at 30% 30%, rgba(255,255,255,0.92), rgba(226,232,240,0.65))',
                        border: '1px solid rgba(255,255,255,0.72)',
                        boxShadow: '0 24px 80px rgba(15, 23, 42, 0.12)',
                    }} />
                </div>
            ) : (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#666' }}>
                    正在加载角色…
                </div>
            )}

            <CompanionChatPanel
                isBackendReady={isBackendReady}
                visionBaseUrl={runtimeConfig.visionBaseUrl}
                sttCapability={sttCapability}
                visionCapability={visionCapability}
                onSend={sendMessage}
                onRetry={retryTurn}
                onInterrupt={interrupt}
                onOpenModelSettings={() => setIsLLMConfigOpen(true)}
                isTtsEnabled={settings.isTTSEnabled}
                onToggleTts={() => void setTtsEnabled(!settings.isTTSEnabled)}
                historyError={historyError}
                onRetryHistory={retryHistory}
                modelConfigurationError={modelConfigurationError}
            />

            {/* UI Layer */}
            <AppToolbar 
                onOpenSettings={() => {
                    setSettingsInitialTab('general');
                    setIsSettingsOpen(true);
                }}
                onOpenLLMSettings={() => setIsLLMConfigOpen(true)}
                onOpenMotionTester={() => setIsMotionTesterOpen(true)}
                onOpenMemoryInspector={() => setIsMemoryInspectorOpen(true)}
            />

            {hasOpenModal && (
                <React.Suspense fallback={null}>
                    <LazyModalLayer
                        settings={{
                            isOpen: isSettingsOpen,
                            onClose: () => setIsSettingsOpen(false),
                            initialTab: settingsInitialTab,
                            activeCharacter,
                            currentSettings: {
                                userName: settings.userName,
                                backgroundImage: settings.backgroundImage,
                                live2dHighDpi: settings.live2dHighDpi,
                                isTTSEnabled: settings.isTTSEnabled,
                            },
                            onSaveCharacter: saveCharacter,
                            onChange: handleSaveGeneralSettings,
                        }}
                        motionTester={{
                            isOpen: isMotionTesterOpen,
                            onClose: () => setIsMotionTesterOpen(false),
                        }}
                        memoryInspector={{
                            isOpen: isMemoryInspectorOpen,
                            onClose: () => setIsMemoryInspectorOpen(false),
                            activeCharacterId,
                        }}
                        llmConfig={{
                            isOpen: isLLMConfigOpen,
                            onClose: () => setIsLLMConfigOpen(false),
                            currentSettings: {
                                apiKey: settings.llm.apiKey,
                                providerId: settings.llm.providerId,
                                apiBaseUrl: settings.llm.baseUrl,
                                modelName: settings.llm.model,
                                temperature: settings.llm.temperature,
                                thinkingEnabled: settings.llm.thinkingEnabled,
                                historyLimit: settings.llm.historyLimit,
                                overflowStrategy: settings.llm.overflowStrategy,
                                topP: settings.llm.topP,
                                presencePenalty: settings.llm.presencePenalty,
                                frequencyPenalty: settings.llm.frequencyPenalty,
                            },
                            onSettingsChange: handleLLMSettingsChange,
                            activeCharacterId,
                        }}
                        avatarRef={avatarRef}
                        runtimeConfig={runtimeConfig}
                    />
                </React.Suspense>
            )}

            <StartupStatus
                backendState={backendState}
                isSettingsLoaded={isSettingsLoaded}
            />
            
        </div>
    );
}

export default App;
