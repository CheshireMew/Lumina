/**
 * App.tsx - Refactored Version (Stage 1)
 * 
 * Modularized with AppToolbar and ModalLayer.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import ChatBubble from './components/ChatBubble'
import InputBox from './components/InputBox'
import GalGameHud from './components/GalGameHud'
import { events } from './core/events';
import { API_CONFIG, updateApiConfig } from './config';
import { CharacterProfile } from '@core/llm/types'
import { ttsService } from '@core/voice/tts_service'
import { GeneralSettingsInput } from './hooks/useSettings';
import type { ProviderType } from './components/LLMConfig/types';

// Core Hooks
import { useCoreSystem } from './hooks/useCoreSystem';
import { useBackendState } from './hooks/useBackendState';
import { useCapabilityPackages } from './hooks/useCapabilityPackages';
import { resolveBundledAssetSrc, transformImageSrc } from './utils/srcUtils';

// Avatar System
import AvatarContainer from './core/avatar/AvatarContainer';
import { AvatarRendererRef } from './core/avatar/types';

// UI Components
import { AppToolbar } from './components/AppToolbar';

const LazyModalLayer = React.lazy(() =>
    import('./components/ModalLayer').then((module) => ({
        default: module.ModalLayer,
    })),
);

const LazyWidgetContainer = React.lazy(() =>
    import('./components/plugins/WidgetContainer').then((module) => ({
        default: module.WidgetContainer,
    })),
);

function App() {
    // ==================== HOOKS ====================
    // Refs
    const avatarRef = useRef<AvatarRendererRef>(null);
    const backendState = useBackendState();
    const isBackendReady = backendState.status === 'ready';
    const runtimeBaseUrl = backendState.ports.memory
        ? `http://127.0.0.1:${backendState.ports.memory}`
        : API_CONFIG.BASE_URL;
    const capabilityPackages = useCapabilityPackages(isBackendReady, runtimeBaseUrl);
    
    // Core System Hook (Unified)
    const {
        activeCharacter, activeCharacterId, characters, setCharacters, switchCharacter,
        settings, isSettingsLoaded, updateLLMSettings, saveGeneralSettings,
        isProcessing, isStreaming, displayMessage, reasoningContent,
        sendMessage, interrupt, saveCharacters
    } = useCoreSystem(avatarRef, isBackendReady);
    
    // ==================== LOCAL STATE ====================
    const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
    
    // Modals State
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isPluginStoreOpen, setIsPluginStoreOpen] = useState(false);
    const [isMotionTesterOpen, setIsMotionTesterOpen] = useState(false);
    const [isMemoryInspectorOpen, setIsMemoryInspectorOpen] = useState(false);
    const [isAvatarSelectorOpen, setIsAvatarSelectorOpen] = useState(false);
    const [isLLMConfigOpen, setIsLLMConfigOpen] = useState(false);
    const [settingsInitialTab, setSettingsInitialTab] = useState<'general' | 'voice' | 'interaction'>('general');
    const [showPluginWidgets, setShowPluginWidgets] = useState(false);
    const [visibleBackgroundImage, setVisibleBackgroundImage] = useState('');
    
    // Other Refs
    // ==================== HANDLERS ====================
    const handleSend = useCallback((text: string) => {
        sendMessage(text);
    }, [sendMessage]);

    const handleUserSpeechStart = useCallback(() => {
        console.log('[App] User speaking, interrupting...');
        interrupt();
    }, [interrupt]);

    const handleCharacterSwitch = useCallback(async (newId: string) => {
        console.log('[App] Switching character:', newId);
        await switchCharacter(newId);
    }, [switchCharacter]);

    const handleLLMSettingsChange = useCallback((apiKey: string, baseUrl: string, model: string, temperature: number, thinkingEnabled: boolean, historyLimit: number, overflowStrategy: 'slide' | 'reset', topP?: number, presencePenalty?: number, frequencyPenalty?: number, providerType: ProviderType = 'custom') => {
        updateLLMSettings({ providerType, apiKey, baseUrl, model, temperature, thinkingEnabled, historyLimit, overflowStrategy, topP, presencePenalty, frequencyPenalty });
    }, [updateLLMSettings]);

    const handleSaveCharacters = useCallback(async (chars: CharacterProfile[], deletedIds: string[]) => {
        await saveCharacters(chars, deletedIds);
    }, [saveCharacters]);

    const handleSaveGeneralSettings = useCallback(async (next: GeneralSettingsInput) => {
        await saveGeneralSettings(next);
    }, [saveGeneralSettings]);
    
    const toggleChatMode = useCallback(() => {
        setChatMode(prev => prev === 'text' ? 'voice' : 'text');
    }, []);

    // ==================== EFFECTS ====================
    useEffect(() => {
        const handleInterruption = () => interrupt();
        
        const handleFaceData = (data: any) => {
             if (avatarRef.current?.setBlendShapes) {
                 avatarRef.current.setBlendShapes(data);
             }
        };

        const u1 = events.on('audio:vad.start', handleInterruption);
        const u2 = events.on('core:interrupt', handleInterruption);
        const u3 = events.on('avatar:face_tracking', handleFaceData);
        
        return () => { u1(); u2(); u3(); };
    }, [interrupt]);

    useEffect(() => {
        if (activeCharacter) {
            if (activeCharacter.voiceConfig?.voiceId) {
                ttsService.setDefaultVoice(activeCharacter.voiceConfig.voiceId);
            }
        }
    }, [activeCharacterId, activeCharacter]);

    useEffect(() => {
        if (Object.keys(backendState.ports).length === 0) {
            return;
        }

        console.log("🔌 [App] Syncing runtime ports:", backendState.ports);
        updateApiConfig(backendState.ports);
    }, [backendState.ports]);

    useEffect(() => {
        if (!isBackendReady) {
            setShowPluginWidgets(false);
            return;
        }

        const timer = window.setTimeout(() => {
            setShowPluginWidgets(true);
        }, 1200);

        return () => window.clearTimeout(timer);
    }, [isBackendReady]);

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
    const modelPath = activeCharacter?.modelPath || API_CONFIG.DEFAULT_MODEL_PATH;
    const live2dPackage = capabilityPackages['live2d-assets'];
    const sttPackage = capabilityPackages['stt-runtime'];
    const visionPackage = capabilityPackages['vision-runtime'];
    const cubismCoreSrc = live2dPackage?.resourceUrls?.libs
        ? `${live2dPackage.resourceUrls.libs}/live2dcubismcore.min.js`
        : undefined;
    const resolvedModelPath = resolveBundledAssetSrc(modelPath);
    const canLoadAvatar = isSettingsLoaded;
    const shouldRenderAvatar = canLoadAvatar && Boolean(resolvedModelPath);
    const hasOpenModal = isSettingsOpen
        || isPluginStoreOpen
        || isMotionTesterOpen
        || isMemoryInspectorOpen
        || isAvatarSelectorOpen
        || isLLMConfigOpen;
    const showStartupStatus = !isSettingsLoaded || backendState.status !== 'ready';
    const startupLabel = backendState.status === 'error'
        ? '后端启动失败'
        : backendState.status === 'ready'
            ? '加载中'
            : '正在启动';
    const startupDetail = backendState.status === 'error'
        ? backendState.errorMessage || '请检查调试控制台'
        : isSettingsLoaded
            ? '正在连接核心服务'
            : '正在准备界面';

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
                    Loading Soul...
                </div>
            )}

            {/* HUD */}
            {isSettingsLoaded && isBackendReady && (
                <GalGameHud
                    activeCharacterId={activeCharacterId}
                    onOpenMemoryInspector={() => setIsMemoryInspectorOpen(true)}
                    galgameEnabled={activeCharacter?.galgameModeEnabled ?? true}
                />
            )}

            {/* ================= Unified Chat Panel ================= */}
            {(
                <div style={{
                    position: 'absolute',
                    bottom: '50px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    width: '90%',
                    maxWidth: '800px',
                    backgroundColor: 'rgba(255, 255, 255, 0.75)',
                    backdropFilter: 'blur(16px)',
                    borderRadius: '24px',
                    border: '1px solid rgba(255, 255, 255, 0.4)',
                    boxShadow: '0 8px 32px rgba(31, 38, 135, 0.15)',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 100,
                    overflow: 'hidden', // Contain children
                    transition: 'all 0.3s ease',
                    // Auto-hide top part if no message
                    height: displayMessage ? 'auto' : 'auto',
                    // Electron Interaction Fixes
                    // @ts-ignore
                    WebkitAppRegion: 'no-drag',
                    pointerEvents: 'auto' 
                }}>
                    
                    {/* 1. Chat Area (Scrollable) */}
                    {displayMessage && (
                        <div style={{
                            maxHeight: '25vh', // Limit height (Reduced from 40vh)
                            overflowY: 'auto',
                            padding: '16px 24px',
                            borderBottom: '1px solid rgba(0,0,0,0.05)',
                        }}>
                            <ChatBubble 
                                message={displayMessage} 
                                isStreaming={isStreaming} 
                                reasoning={reasoningContent}
                                embedded={true}
                            />
                        </div>
                    )}

                    {/* 2. Input Area (Fixed at bottom of panel) */}
                    <div style={{ width: '100%' }}>
                        <InputBox 
                            onSend={handleSend} 
                            disabled={!isBackendReady || (isProcessing && !isStreaming)}
                            embedded={true}
                            chatMode={chatMode}
                            onToggleChatMode={toggleChatMode}
                            onSpeechStart={handleUserSpeechStart}
                            voiceCapabilityState={sttPackage?.state || 'unavailable'}
                            visionCapabilityState={visionPackage?.state || 'unavailable'}
                        />
                    </div>
                </div>
            )}

            {/* UI Layer */}
            <AppToolbar 
                onOpenAvatarSelector={() => {
                    setIsAvatarSelectorOpen(true);
                }}
                onOpenSettings={() => {
                    setSettingsInitialTab('general');
                    setIsSettingsOpen(true);
                }}
                onOpenLLMSettings={() => setIsLLMConfigOpen(true)}
                onOpenPlugins={() => setIsPluginStoreOpen(true)}
                onOpenMotionTester={() => setIsMotionTesterOpen(true)}
            />

            {hasOpenModal && (
                <React.Suspense fallback={null}>
                    <LazyModalLayer
                        settings={{
                            isOpen: isSettingsOpen,
                            onClose: () => setIsSettingsOpen(false),
                            initialTab: settingsInitialTab,
                            currentSettings: {
                                userName: settings.userName,
                                backgroundImage: settings.backgroundImage,
                                live2dHighDpi: settings.live2dHighDpi,
                            },
                            onSave: handleSaveGeneralSettings,
                        }}
                        pluginStore={{
                            isOpen: isPluginStoreOpen,
                            onClose: () => setIsPluginStoreOpen(false),
                            onOpenLlmSettings: () => setIsLLMConfigOpen(true),
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
                        avatarSelector={{
                            isOpen: isAvatarSelectorOpen,
                            onClose: () => setIsAvatarSelectorOpen(false),
                            activeCharacterId,
                            activeCharacter,
                            live2dPackage,
                            characters,
                            setCharacters,
                            onActivateCharacter: handleCharacterSwitch,
                            onSaveCharacters: handleSaveCharacters,
                        }}
                        llmConfig={{
                            isOpen: isLLMConfigOpen,
                            onClose: () => setIsLLMConfigOpen(false),
                            currentSettings: {
                                apiKey: settings.llm.apiKey,
                                providerType: settings.llm.providerType,
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
                    />
                </React.Suspense>
            )}

            {/* Plugin Widgets Layer */}
            <div className="fixed top-24 right-4 z-40 w-80 pointer-events-none flex flex-col gap-4">
                {isBackendReady && showPluginWidgets && (
                    <React.Suspense fallback={null}>
                        <LazyWidgetContainer location="sidebar_right" className="w-full" />
                    </React.Suspense>
                )}
            </div>

            {showStartupStatus && (
                <div style={{
                    position: 'absolute',
                    top: '20px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                }}>
                    <div style={{
                        maxWidth: '420px',
                        padding: '10px 14px',
                        borderRadius: '999px',
                        background: 'rgba(255, 255, 255, 0.78)',
                        border: '1px solid rgba(255, 255, 255, 0.55)',
                        backdropFilter: 'blur(12px)',
                        boxShadow: '0 12px 32px rgba(15, 23, 42, 0.12)',
                        color: '#334155',
                    }}>
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                        }}>
                            <div style={{
                                width: '12px',
                                height: '12px',
                                borderRadius: '999px',
                                backgroundColor: backendState.status === 'error' ? '#ef4444' : '#f59e0b',
                                boxShadow: backendState.status === 'error'
                                    ? '0 0 16px rgba(239, 68, 68, 0.35)'
                                    : '0 0 16px rgba(245, 158, 11, 0.35)',
                            }} />
                            <div style={{
                                fontSize: '14px',
                                fontWeight: 700,
                            }}>
                                {startupLabel}
                            </div>
                            <div style={{
                                fontSize: '13px',
                                color: '#64748b',
                                maxWidth: '280px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                            }}>
                                {startupDetail}
                            </div>
                        </div>
                    </div>
                </div>
            )}
            
        </div>
    );
}

export default App;
