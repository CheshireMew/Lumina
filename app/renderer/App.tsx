/**
 * App.tsx - Refactored Version (Stage 1)
 * 
 * Modularized with AppToolbar and ModalLayer.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import ChatBubble from './components/ChatBubble'
import InputBox from './components/InputBox'
import VoiceInput from './components/VoiceInput'
import GalGameHud from './components/GalGameHud'
import { events } from './core/events';
import { API_CONFIG } from './config';
import { Message, CharacterProfile } from '@core/llm/types'
import { memoryService } from '@core/memory/memory_service'
import { ttsService } from '@core/voice/tts_service'

// Core Hooks
// Core Hooks
import { useGateway } from './hooks/useGateway';
import { useCoreSystem } from './hooks/useCoreSystem';
import { useCharacterState } from './hooks/useCharacterState';
import { useAudioPipeline } from './hooks/useAudioPipeline';
import { useChatStream } from './hooks/useChatStream';
import { useSettings } from './hooks/useSettings';

// Avatar System
import AvatarContainer from './core/avatar/AvatarContainer';
import { AvatarRendererRef } from './core/avatar/types';

// UI Components
import { AppToolbar } from './components/AppToolbar';
import { ModalLayer } from './components/ModalLayer';
import { WidgetContainer } from './components/plugins/WidgetContainer';

function App() {
    // ==================== HOOKS ====================
    // Refs
    const avatarRef = useRef<AvatarRendererRef>(null);
    
    // Core System Hook (Unified)
    const {
        activeCharacter, activeCharacterId, characters, setCharacters, updateCharacterModel, switchCharacter,
        settings, isSettingsLoaded, updateLLMSettings, saveSetting,
        isProcessing, isStreaming, displayMessage, reasoningContent,
        sendMessage, interrupt, saveCharacters
    } = useCoreSystem(avatarRef);
    
    // ==================== LOCAL STATE ====================
    const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
    
    // Modals State
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isPluginStoreOpen, setIsPluginStoreOpen] = useState(false);
    const [isMotionTesterOpen, setIsMotionTesterOpen] = useState(false);
    const [isSurrealViewerOpen, setIsSurrealViewerOpen] = useState(false);
    const [isAvatarSelectorOpen, setIsAvatarSelectorOpen] = useState(false);
    const [isLLMConfigOpen, setIsLLMConfigOpen] = useState(false);
    const [settingsInitialTab, setSettingsInitialTab] = useState<'general' | 'voice' | 'characters' | 'interaction'>('general');
    const [backgroundImage, setBackgroundImage] = useState<string>('');
    
    // Sync background from settings
    useEffect(() => {
        if (settings?.backgroundImage) {
            setBackgroundImage(settings.backgroundImage);
        }
    }, [settings.backgroundImage]);
    
    // Other Refs
    const currentSystemPromptRef = useRef<string>('');

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

    const handleClearHistory = useCallback(() => {
        console.log('[Memory] History cleared (via System Prompt reset or manual action)');
        // history clearing logic is inside core system ref usually, or we expose a clear method
    }, []);

    const handleLLMSettingsChange = useCallback((apiKey: string, baseUrl: string, model: string, temperature: number, thinkingEnabled: boolean, historyLimit: number, overflowStrategy: 'slide' | 'reset', topP?: number, presencePenalty?: number, frequencyPenalty?: number) => {
        updateLLMSettings({ apiKey, baseUrl, model, temperature, thinkingEnabled, historyLimit, overflowStrategy, topP, presencePenalty, frequencyPenalty });
    }, [updateLLMSettings]);

    const handleCharactersUpdated = useCallback((newCharacters: CharacterProfile[], newActiveId: string) => {
        setCharacters(newCharacters);
        if (newActiveId !== activeCharacterId) {
            handleCharacterSwitch(newActiveId);
        }
    }, [setCharacters, activeCharacterId, handleCharacterSwitch]);

    const handleUserNameUpdated = useCallback((newName: string) => {
        saveSetting('userName', 'userName', newName);
    }, [saveSetting]);

    const handleModelSelect = useCallback(async (modelPath: string) => {
        if (!activeCharacter) return;
        await updateCharacterModel(activeCharacterId, modelPath);
    }, [activeCharacter, activeCharacterId, updateCharacterModel]);

    const handleSaveCharacters = useCallback(async (chars: CharacterProfile[], deletedIds: string[]) => {
        await saveCharacters(chars, deletedIds);
    }, [saveCharacters]);
    
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
            // Fetch soul prompt...
            fetch(`${API_CONFIG.BASE_URL}/soul`)
                .then(res => res.ok ? res.json() : null)
                .then(soul => {
                    if (soul?.system_prompt && soul.system_prompt !== currentSystemPromptRef.current) {
                        window.llm?.setSystemPrompt?.(soul.system_prompt);
                        currentSystemPromptRef.current = soul.system_prompt;
                    }
                })
                .catch(e => console.warn('[App] Failed to fetch soul:', e));
        }
    }, [activeCharacterId, activeCharacter]);

    // ==================== RENDER ====================
    const modelPath = activeCharacter?.modelPath || API_CONFIG.DEFAULT_MODEL_PATH;

    return (
        <div style={{ 
            height: '100vh', 
            width: '100vw', 
            position: 'relative', 
            overflow: 'hidden',
            backgroundColor: '#f3f4f6', // Fallback color
            backgroundImage: backgroundImage ? `url("${backgroundImage}")` : 'linear-gradient(135deg, #eef2ff 0%, #fae8ff 50%, #f0fdf4 100%)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            transition: 'background-image 0.5s ease-in-out'
        }}>
            {/* Avatar */}
            {isSettingsLoaded ? (
                <AvatarContainer
                    ref={avatarRef}
                    modelPath={modelPath}
                    highDpi={settings.live2dHighDpi}
                />
            ) : (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#666' }}>
                    Loading Soul...
                </div>
            )}

            {/* HUD */}
            {isSettingsLoaded && (
                <GalGameHud
                    activeCharacterId={activeCharacterId}
                    onOpenSurrealViewer={() => setIsSurrealViewerOpen(true)}
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
                    height: displayMessage ? 'auto' : 'auto' 
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
                            disabled={isProcessing && !isStreaming}
                            embedded={true}
                            chatMode={chatMode}
                            onToggleChatMode={toggleChatMode}
                            onSpeechStart={handleUserSpeechStart}
                        />
                    </div>
                </div>
            )}

            {/* UI Layer */}
            <AppToolbar 
                chatMode={chatMode}
                onToggleChatMode={toggleChatMode}
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

            <ModalLayer 
                isSettingsOpen={isSettingsOpen}
                onCloseSettings={() => setIsSettingsOpen(false)}
                isPluginStoreOpen={isPluginStoreOpen}
                onClosePluginStore={() => setIsPluginStoreOpen(false)}
                isMotionTesterOpen={isMotionTesterOpen}
                onCloseMotionTester={() => setIsMotionTesterOpen(false)}
                isSurrealViewerOpen={isSurrealViewerOpen}
                onCloseSurrealViewer={() => setIsSurrealViewerOpen(false)}
                isAvatarSelectorOpen={isAvatarSelectorOpen}
                onCloseAvatarSelector={() => setIsAvatarSelectorOpen(false)}
                
                onClearHistory={handleClearHistory}

                // LLM Settings
                isLLMConfigOpen={isLLMConfigOpen}
                onOpenLLMConfig={() => setIsLLMConfigOpen(true)} // Passed here
                onCloseLLMConfig={() => setIsLLMConfigOpen(false)}
                currentLlmSettings={{
                    apiKey: settings.llm.apiKey,
                    apiBaseUrl: settings.llm.baseUrl,
                    modelName: settings.llm.model,
                    temperature: settings.llm.temperature,
                    thinkingEnabled: settings.llm.thinkingEnabled,
                    historyLimit: settings.llm.historyLimit,
                    overflowStrategy: settings.llm.overflowStrategy,
                    topP: settings.llm.topP,
                    presencePenalty: settings.llm.presencePenalty,
                    frequencyPenalty: settings.llm.frequencyPenalty
                }}
                onContextWindowChange={(n) => saveSetting('contextWindow', 'contextWindow', n)}
                onLLMSettingsChange={handleLLMSettingsChange}
                onCharactersUpdated={handleCharactersUpdated}
                onUserNameUpdated={handleUserNameUpdated}
                onLive2DHighDpiChange={(e) => saveSetting('live2dHighDpi', 'live2d_high_dpi', e)}
                onCharacterSwitch={handleCharacterSwitch}
                onThinkingModeChange={enable => updateLLMSettings({ ...settings.llm, thinkingEnabled: enable })}
                onBackgroundImageChange={url => {
                    setBackgroundImage(url);
                    saveSetting('backgroundImage', 'backgroundImage', url);
                }}
                
                // Character Props (Passed to AvatarSelectorModal)
                characters={characters}
                setCharacters={setCharacters}
                onSaveCharacters={handleSaveCharacters}

                activeCharacter={activeCharacter}
                activeCharacterId={activeCharacterId}
                galgameEnabled={activeCharacter?.galgameModeEnabled ?? true}
                onModelSelect={handleModelSelect}
                avatarRef={avatarRef}
                settingsInitialTab={settingsInitialTab}
            />

            {/* Plugin Widgets Layer */}
            <div className="fixed top-24 right-4 z-40 w-80 pointer-events-none flex flex-col gap-4">
                 <WidgetContainer location="sidebar_right" className="w-full" />
            </div>
            
        </div>
    );
}

export default App;
