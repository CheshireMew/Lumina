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
import { useGateway } from './hooks/useGateway';
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

function App() {
    // ==================== HOOKS ====================
    const { characters, activeCharacterId, activeCharacter, switchCharacter, setCharacters, updateCharacterModel } = useCharacterState();
    const { settings, isLoaded: isSettingsLoaded, updateLLMSettings, saveSetting } = useSettings();
    const { initPipeline, enqueueSynthesis, feedToken, flush, clear: clearAudio } = useAudioPipeline();
    const { displayMessage, reasoningContent, reset: resetStream, processToken, getFinalContent } = useChatStream();
    
    // ==================== LOCAL STATE ====================
    const [isProcessing, setIsProcessing] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
    
    // Modals State
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isPluginStoreOpen, setIsPluginStoreOpen] = useState(false);
    const [isMotionTesterOpen, setIsMotionTesterOpen] = useState(false);
    const [isSurrealViewerOpen, setIsSurrealViewerOpen] = useState(false);
    const [isAvatarSelectorOpen, setIsAvatarSelectorOpen] = useState(false);
    const [isLLMConfigOpen, setIsLLMConfigOpen] = useState(false);
    
    // Refs
    const avatarRef = useRef<AvatarRendererRef>(null);
    const conversationHistoryRef = useRef<Message[]>([]);
    const currentSystemPromptRef = useRef<string>('');
    const isProcessingRef = useRef(false); // Synchronous lock

    // ==================== GATEWAY CALLBACKS ====================
    const handleChatStart = useCallback((mode: string) => {
        console.log(`[App] Chat Start (mode: ${mode})`);
        isProcessingRef.current = true;
        setIsProcessing(true);
        setIsStreaming(true);
        resetStream();
        
        if (settings.isTTSEnabled) {
            initPipeline((sentence, index) => {
                enqueueSynthesis(sentence, index);
            });
        }
    }, [settings.isTTSEnabled, resetStream, initPipeline, enqueueSynthesis]);

    const handleChatStream = useCallback((token: string) => {
        processToken(token, 'content', (emotion) => {
            avatarRef.current?.setEmotion?.(emotion);
        });
        
        if (settings.isTTSEnabled) {
            feedToken(token);
        }
    }, [processToken, settings.isTTSEnabled, feedToken]);

    const handleChatEnd = useCallback(() => {
        console.log('[App] Chat End');
        isProcessingRef.current = false;
        setIsProcessing(false);
        setIsStreaming(false);
        
        if (settings.isTTSEnabled) {
            flush();
        }
        
        const finalContent = getFinalContent();
        if (finalContent) {
            const msg: Message = { role: 'assistant', content: finalContent, timestamp: Date.now() };
            conversationHistoryRef.current.push(msg);
            
            // memoryService.add([msg], settings.userName, activeCharacter?.name || 'Assistant')
            //    .catch(e => console.error('[Memory] Save failed:', e));
        }
    }, [settings.isTTSEnabled, settings.userName, activeCharacter, flush, getFinalContent]);

    const handleEmotion = useCallback((emotion: string) => {
        console.log('[App] Emotion:', emotion);
        avatarRef.current?.setEmotion?.(emotion);
    }, []);

    // Gateway Hook
    const { isConnected, send } = useGateway({
        onChatStart: handleChatStart,
        onChatStream: handleChatStream,
        onChatEnd: handleChatEnd,
        onEmotion: handleEmotion,
        baseUrl: API_CONFIG.BASE_URL
    });

    // ==================== HANDLERS ====================
    const handleSend = useCallback(async (text: string) => {
        if (!text.trim() || isProcessingRef.current) return;
        
        const userMsg: Message = { role: 'user', content: text, timestamp: Date.now() };
        conversationHistoryRef.current.push(userMsg);
        
        // Lock immediately (Synchronous)
        isProcessingRef.current = true;
        setIsProcessing(true); 
        
        send('chat', { 
            text, 
            character_id: activeCharacterId,
            user_name: settings.userName,
            model: settings.llm.model // Pass current model selection
        });
    }, [activeCharacterId, settings.userName, send]);

    const handleUserSpeechStart = useCallback(() => {
        console.log('[TTS] User speaking, clearing queue');
        clearAudio();
    }, [clearAudio]);

    const handleCharacterSwitch = useCallback(async (newCharacterId: string) => {
        console.log('[App] Switching character:', newCharacterId);
        await switchCharacter(newCharacterId);
        conversationHistoryRef.current = [];
        resetStream();
    }, [switchCharacter, resetStream]);

    const handleClearHistory = useCallback(() => {
        conversationHistoryRef.current = [];
        console.log('[Memory] History cleared');
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
        console.log('[App] Switching Model to:', modelPath);
        await updateCharacterModel(activeCharacterId, modelPath);
    }, [activeCharacter, activeCharacterId, updateCharacterModel]);
    
    const toggleChatMode = useCallback(() => {
        setChatMode(prev => prev === 'text' ? 'voice' : 'text');
    }, []);

    // ==================== EFFECTS ====================
    useEffect(() => {
        const handleInterruption = () => {
            clearAudio();
            avatarRef.current?.stopExpression?.();
        };
        
        const handleFaceData = (data: any) => {
             if (avatarRef.current?.setBlendShapes) {
                 avatarRef.current.setBlendShapes(data);
             }
        };

        const u1 = events.on('audio:vad.start', handleInterruption);
        const u2 = events.on('core:interrupt', handleInterruption);
        const u3 = events.on('avatar:face_tracking', handleFaceData);
        
        return () => { u1(); u2(); u3(); };
    }, [clearAudio]);

    useEffect(() => {
        if (activeCharacter) {
            if (activeCharacter.voiceConfig?.voiceId) {
                ttsService.setDefaultVoice(activeCharacter.voiceConfig.voiceId);
            }
            
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
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundImage: 'url(/bg.png)',
            backgroundSize: 'cover', backgroundPosition: 'center',
            overflow: 'hidden', margin: 0, padding: 0
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

            {/* Chat */}
            <ChatBubble message={displayMessage} isStreaming={isStreaming} reasoning={reasoningContent} />

            {/* Input */}
            {chatMode === 'text' ? (
                <InputBox onSend={handleSend} disabled={isProcessing} />
            ) : (
                <VoiceInput onSend={handleSend} disabled={isProcessing} onSpeechStart={handleUserSpeechStart} />
            )}

            {/* UI Layer */}
            <AppToolbar 
                chatMode={chatMode}
                onToggleChatMode={toggleChatMode}
                onOpenAvatarSelector={() => setIsAvatarSelectorOpen(true)}
                onOpenSettings={() => setIsSettingsOpen(true)}
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
                onThinkingModeChange={(e) => updateLLMSettings({ ...settings.llm, thinkingEnabled: e })}
                
                activeCharacter={activeCharacter}
                activeCharacterId={activeCharacterId}
                galgameEnabled={activeCharacter?.galgameModeEnabled ?? true}
                onModelSelect={handleModelSelect}
                avatarRef={avatarRef}
            />
        </div>
    );
}

export default App;
