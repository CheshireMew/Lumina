import React, { useState, useRef, useEffect } from 'react'
import Live2DViewer, { Live2DViewerRef } from './live2d-view/Live2DViewer'
import ChatBubble from './components/ChatBubble'
import InputBox from './components/InputBox'
import VoiceInput from './components/VoiceInput'
import SettingsModal from './components/SettingsModal'
import { ttsService } from '@core/voice/tts_service'
import { SentenceSplitter } from '@core/voice/sentence_splitter'
import { AudioQueue } from '@core/voice/audio_queue'
import { Message, CharacterProfile, DEFAULT_CHARACTERS } from '@core/llm/types'
import { llmService } from '@core/llm/llm_service'
import { memoryService } from '@core/memory/memory_service'

import emotionMapRaw from './emotion_map.json';

const emotionMap: Record<string, { group: string, index: number }> = emotionMapRaw;

// Helper to clean text for TTS (remove emojis and parenthesized text)
const cleanTextForTTS = (text: string): string => {
    return text
        .replace(/\([^)]*\)/g, '') // Remove (text)
        .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '') // Remove emojis
        .trim();
};

function App() {
    const [currentMessage, setCurrentMessage] = useState<string>('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isTTSEnabled, setIsTTSEnabled] = useState(true); // TTS 开关
    const live2dRef = React.useRef<Live2DViewerRef>(null);

    // Characters State
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    const [activeCharacterId, setActiveCharacterId] = useState<string>('');
    const [userName, setUserName] = useState<string>('Master'); // Default User Name

    // Conversation Memory
    const [conversationHistory, setConversationHistory] = useState<Message[]>([]);
    const [conversationSummary, setConversationSummary] = useState<string>(''); // 历史摘要
    const [contextWindow, setContextWindow] = useState(15); // 默认保留15轮
    const [autoSummarizationEnabled, setAutoSummarizationEnabled] = useState(true);

    // TTS 模块引用
    const audioQueueRef = useRef<AudioQueue>(new AudioQueue());
    const sentenceSplitterRef = useRef<SentenceSplitter | null>(null);
    const synthPromisesRef = useRef<Promise<void>[]>([]); // Promise 队列维持顺序
    const emotionBufferRef = useRef<string>(''); // Buffer for detecting (emotion) tags in stream

    // Function to process emotion tags from accumulated text
    const processEmotions = (text: string) => {
        // Regex to find all (emotion) tags
        const matches = text.matchAll(/\(([^)]+)\)/g);
        for (const match of matches) {
            const emotionContent = match[1].toLowerCase();
            // Check if we have a mapping for any word in the content
            for (const [key, motion] of Object.entries(emotionMap)) {
                if (emotionContent.includes(key)) {
                    console.log(`[App] Triggering emotion: ${key} -> Motion: ${motion.group} index ${motion.index}`);
                    if (live2dRef.current) {
                        live2dRef.current.motion(motion.group, motion.index);
                    }
                    break; // Trigger only one emotion per tag
                }
            }
        }
    };

    // 并发合成，但按顺序入队
    const enqueueSynthesis = (sentence: string, index: number) => {
        const synthPromise = (async () => {
            console.log(`[TTS] Starting synthesis ${index}:`, sentence);
            try {
                const audioStream = await ttsService.synthesize(sentence);

                // 等待前面的句子完成（维持顺序）
                if (index > 0) {
                    await synthPromisesRef.current[index - 1]; // Wait for previous Promise to resolve (enqueued)
                }

                if (audioStream) {
                    // 按顺序入队播放
                    audioQueueRef.current.enqueue(audioStream);
                    console.log(`[TTS] Enqueued stream for sentence ${index}`);
                }
            } catch (error) {
                console.error(`[TTS] Synthesis failed for ${index}:`, error);
            }
        })();

        synthPromisesRef.current[index] = synthPromise;
    };

    // Helper: Apply Active Character
    const applyCharacter = (character: CharacterProfile, uName: string) => {
        // 1. Render Prompt Template
        const renderedPrompt = character.systemPromptTemplate
            .replace(/{char}/g, character.name)
            .replace(/{user}/g, uName);

        console.log(`[App] Applying character: ${character.name} for user: ${uName}`);
        llmService.setSystemPrompt(renderedPrompt);

        // 2. Update TTS Voice (Future: bind voice config to ttsService)
        // ttsService.setVoice(character.voiceConfig.voiceId);
    };

    // Load all settings on mount
    useEffect(() => {
        const loadSettings = async () => {
            const settings = (window as any).settings;
            try {
                // LLM Settings
                const apiKey = await settings.get('apiKey');
                const baseUrl = await settings.get('apiBaseUrl') || 'https://api.deepseek.com/v1';
                const model = await settings.get('modelName') || 'deepseek-chat';

                // User Settings
                const loadedUserName = await settings.get('userName') || 'Master';
                setUserName(loadedUserName);

                // Character Settings
                let loadedCharacters = await settings.get('characters') as CharacterProfile[];
                let loadedActiveId = await settings.get('activeCharacterId') as string;

                // Migration / Default Init
                if (!loadedCharacters || loadedCharacters.length === 0) {
                    console.log('[App] No characters found, initializing defaults.');
                    loadedCharacters = DEFAULT_CHARACTERS;
                    loadedActiveId = DEFAULT_CHARACTERS[0].id;
                    await settings.set('characters', loadedCharacters);
                    await settings.set('activeCharacterId', loadedActiveId);
                }

                setCharacters(loadedCharacters);
                setActiveCharacterId(loadedActiveId);

                if (apiKey) {
                    console.log('[App] Initializing LLM Service with loaded settings');
                    llmService.init(apiKey, baseUrl, model);

                    // Initialize Memory Service
                    console.log('[App] Initializing Memory Service');
                    memoryService.configure(apiKey, baseUrl, model);

                    // Apply Active Character
                    const activeChar = loadedCharacters.find(c => c.id === loadedActiveId) || loadedCharacters[0];
                    applyCharacter(activeChar, loadedUserName);
                } else {
                    console.warn('[App] No API Key found in settings');
                }

                // Memory Settings
                const windowSize = await settings.get('contextWindow');
                setContextWindow(windowSize || 15);
            } catch (error) {
                console.error('[App] Failed to load settings:', error);
            }
        };
        loadSettings();
    }, []);

    // Handlers for SettingsModal callbacks
    const handleClearHistory = () => {
        setConversationHistory([]);
        setConversationSummary('');
        console.log('[Memory] Conversation history cleared');
    };

    const handleContextWindowChange = (newWindow: number) => {
        setContextWindow(newWindow);
        console.log(`[Memory] Context window changed to ${newWindow} turns`);
    };

    // Callback when LLM settings change in SettingsModal
    const handleLLMSettingsChange = (apiKey: string, baseUrl: string, model: string) => {
        console.log('[App] Re-initializing LLM Service with new settings');
        llmService.init(apiKey, baseUrl, model);
        memoryService.configure(apiKey, baseUrl, model);
    };

    // Character update handler
    const handleCharactersUpdated = (newCharacters: CharacterProfile[], newActiveId: string) => {
        console.log('[App] Handling character update');
        setCharacters(newCharacters);

        const oldActiveId = activeCharacterId;

        // Update active ID if changed
        if (newActiveId !== activeCharacterId) {
            setActiveCharacterId(newActiveId);
        }

        // Determine if we need to re-apply prompt
        // Case 1: Active ID changed
        // Case 2: Active Character content changed

        const activeChar = newCharacters.find(c => c.id === newActiveId) || newCharacters[0];

        // Currently we just always re-apply to be safe and simple
        applyCharacter(activeChar, userName);
    };

    // User Name update handler
    const handleUserNameUpdated = (newName: string) => {
        console.log('[App] User Name updated:', newName);
        setUserName(newName);

        // Re-apply character with new user name
        const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];
        if (activeChar) {
            applyCharacter(activeChar, newName);
        }
    };

    const handleSend = async (text: string) => {
        setIsProcessing(true);
        setIsStreaming(true);
        setCurrentMessage(''); // 清空旧消息
        synthPromisesRef.current = []; // 清空 Promise 队列
        let sentenceIndex = 0;

        // 添加用户消息到历史
        const userMessage: Message = {
            role: 'user',
            content: text,
            timestamp: Date.now()
        };
        setConversationHistory(prev => [...prev, userMessage]);

        try {
            // 1. Retrieve Relevant Memories (Hybrid Memory L3)
            let relevantMemories = '';
            try {
                // Only search if not empty
                if (text.trim().length > 2) {
                    console.log('[Memory] Searching for relevant memories...');
                    relevantMemories = await memoryService.search(text);
                    if (relevantMemories) {
                        console.log('[Memory] Found related memories:', relevantMemories);
                    }
                }
            } catch (memErr) {
                console.error('[Memory] Search failed (is backend running?):', memErr);
            }

            // 初始化句子分割器
            if (isTTSEnabled) {
                sentenceSplitterRef.current = new SentenceSplitter((sentence) => {
                    // Filter text for TTS (Remove emojis and emotions)
                    const cleanSentence = cleanTextForTTS(sentence);
                    if (cleanSentence.trim().length > 0) {
                        // 并发触发合成，Promise 队列维持顺序
                        enqueueSynthesis(cleanSentence, sentenceIndex++);
                    }
                });
            }

            let fullRawResponse = '';
            emotionBufferRef.current = '';

            // 使用带历史的流式聊天
            await llmService.chatStreamWithHistory(
                conversationHistory,
                text,
                contextWindow,
                (token: string) => {
                    console.log('[LLM Token]:', JSON.stringify(token));
                    fullRawResponse += token;
                    emotionBufferRef.current += token;

                    // 1. Check for complete (emotion) tags to trigger Live2D
                    if (token.includes(')')) {
                        processEmotions(emotionBufferRef.current);
                        emotionBufferRef.current = ''; // Reset buffer
                    }

                    // 2. Filter for Display
                    // Remove complete tags (..) and trailing incomplete tag (..
                    const displayUpdate = fullRawResponse
                        .replace(/\([^)]*\)/g, '')   // Remove complete
                        .replace(/\([^)]*$/, '');    // Remove incomplete trailing

                    setCurrentMessage(displayUpdate);

                    // 3. Feed RAW token to splitter 
                    // (Splitter needs punctuation to decide when to split. 
                    // We clean the *result* sentence in the callback above.)
                    if (isTTSEnabled && sentenceSplitterRef.current) {
                        sentenceSplitterRef.current.feedToken(token);
                    }
                },
                conversationSummary, // 传递当前摘要
                relevantMemories     // 传递长期记忆
            );

            // 流结束后的处理
            setIsStreaming(false);
            setIsProcessing(false);

            // 刷新句子分割器
            if (isTTSEnabled && sentenceSplitterRef.current) {
                sentenceSplitterRef.current.flush();
            }

            // 添加助手回复到历史 (Cleaned)
            const finalCleanContent = fullRawResponse.replace(/\([^)]*\)/g, '').trim();
            const assistantMessage: Message = {
                role: 'assistant',
                content: finalCleanContent,
                timestamp: Date.now()
            };

            // 使用临时变量，因为 state 更新是异步的
            const updatedHistory = [...conversationHistory, userMessage, assistantMessage];
            setConversationHistory(prev => [...prev, assistantMessage]);

            // --- Async: Add to Long-Term Memory (L3) ---
            memoryService.add([userMessage, assistantMessage])
                .catch(err => console.error('[Memory] Failed to store interaction:', err));

            // --- 自动摘要逻辑 (L2) ---
            if (autoSummarizationEnabled) {
                // 如果历史记录超过 contextWindow 的 2.5倍 (留有余量)，触发压缩
                const maxHistoryLength = contextWindow * 2.5;
                if (updatedHistory.length > maxHistoryLength) {
                    console.log('[Memory] History too long, triggering summarization...');

                    // 1. 计算需要移除的消息数量 (保留最近的 contextWindow * 2)
                    // 这样我们既有摘要，又有最近的完整对话
                    const keepCount = contextWindow * 2;
                    const removeCount = updatedHistory.length - keepCount;

                    if (removeCount > 0) {
                        // 2. 提取要总结的消息
                        const messagesToSummarize = updatedHistory.slice(0, removeCount);
                        const keptMessages = updatedHistory.slice(removeCount);

                        // 3. 调用 API 生成摘要
                        llmService.updateSummary(conversationSummary, messagesToSummarize)
                            .then(newSummary => {
                                console.log('[Memory] New Summary:', newSummary);
                                setConversationSummary(newSummary);
                                setConversationHistory(keptMessages);
                            })
                            .catch(err => console.error('[Memory] Summarization failed:', err));
                    }
                }
            }

            // Trigger Live2D Motion
            if (live2dRef.current) {
                live2dRef.current.motion('TapBody');
            }

        } catch (error) {
            console.error('Error in chat:', error);
            setIsProcessing(false);
            setIsStreaming(false);
            setCurrentMessage('Error: Failed to get response.');
        }
    };

    // 用户开始说话时，中断 AI 的语音播放
    const handleUserSpeechStart = () => {
        console.log('[TTS] User started speaking, clearing audio queue');
        audioQueueRef.current.clear();
    };

    return (
        <div style={{ width: '100vw', height: '100vh', backgroundColor: 'transparent', position: 'relative', overflow: 'hidden' }}>

            {/* Live2D Layer */}
            <Live2DViewer
                ref={live2dRef}
                modelPath="/live2d/Hiyori/Hiyori.model3.json"
            />

            {/* UI Layer */}
            <ChatBubble message={currentMessage} isStreaming={isStreaming} />

            {chatMode === 'text' ? (
                <InputBox onSend={handleSend} disabled={isProcessing} />
            ) : (
                <VoiceInput
                    onSend={handleSend}
                    disabled={isProcessing}
                    onSpeechStart={handleUserSpeechStart}
                />
            )}

            <div style={{ position: 'absolute', top: 20, right: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Toggle Mode Button */}
                <button
                    onClick={() => setChatMode(chatMode === 'text' ? 'voice' : 'text')}
                    style={{
                        padding: '12px 20px',
                        fontSize: '16px',
                        backgroundColor: chatMode === 'voice' ? '#ff6b6b' : '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '25px',
                        cursor: 'pointer',
                        boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
                        transition: 'all 0.3s ease'
                    }}
                >
                    {chatMode === 'text' ? '🎤 Voice' : '⌨️ Text'}
                </button>

                {/* Settings Button */}
                <button
                    onClick={() => setIsSettingsOpen(true)}
                    style={{
                        padding: '12px 20px',
                        fontSize: '16px',
                        backgroundColor: '#2196F3',
                        color: 'white',
                        border: 'none',
                        borderRadius: '25px',
                        cursor: 'pointer',
                        boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
                        transition: 'all 0.3s ease'
                    }}
                >
                    ⚙️ Settings
                </button>
            </div>

            {/* Settings Modal */}
            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                onClearHistory={handleClearHistory}
                onContextWindowChange={handleContextWindowChange}
                onLLMSettingsChange={handleLLMSettingsChange}
                onCharactersUpdated={handleCharactersUpdated}
                onUserNameUpdated={handleUserNameUpdated}
            />
        </div>
    );
}

export default App;
