
import React, { useState, useRef, useEffect } from 'react'
import Live2DViewer, { Live2DViewerRef } from './live2d-view/Live2DViewer'
import ChatBubble from './components/ChatBubble'
import InputBox from './components/InputBox'
import VoiceInput from './components/VoiceInput'
import SettingsModal from './components/SettingsModal';
import { events } from './core/events';
import MotionTester from './components/MotionTester'
import SurrealViewer from './components/SurrealViewer'
import GalGameHud from './components/GalGameHud' // Integrated Soul HUD
import EMOTION_MAP from './emotion_map.json';

import { API_CONFIG } from './config';
import { ttsService } from '@core/voice/tts_service'
import { SentenceSplitter } from '@core/voice/sentence_splitter'
import { AudioQueue } from '@core/voice/audio_queue'
import { 
    CheckCircle, Clock, Search, Table as TableIcon, Activity, Sparkles, Trash2, Edit, Plus, GitMerge,
    Mic, Keyboard, Settings as SettingsIcon, Play as PlayIcon
} from 'lucide-react';
import { Message, CharacterProfile, DEFAULT_CHARACTERS } from '@core/llm/types'
import { memoryService } from '@core/memory/memory_service'

import { processEmotions } from './utils/emotionProcessor';
import { useProactiveChat } from './hooks/useProactiveChat';
import { useCharacterState } from './hooks/useCharacterState';
// Helper to clean text for TTS (remove emojis and [emotion] tags)
const cleanTextForTTS = (text: string): string => {
    return text
        .replace(/\[[^\]]*\]/g, '') // Remove [text]
        .replace(/[\(（][^)）]*[\)）]/g, '') // Also remove (text) / （正） just in case
        .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '') // Remove emojis
        // 修复全大写英文单词（避免 TTS 逐字母朗读）- 转为首字母大写
        .replace(/\b([A-Z]{2,})\b/g, (match) => match.charAt(0) + match.slice(1).toLowerCase())
        .trim();
};

function App() {
    const [currentMessage, setCurrentMessage] = useState<string>('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isMotionTesterOpen, setIsMotionTesterOpen] = useState(false);
    const [isSurrealViewerOpen, setIsSurrealViewerOpen] = useState(false);
    const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isTTSEnabled, setIsTTSEnabled] = useState(true); // TTS 开关
    const live2dRef = React.useRef<Live2DViewerRef>(null);

    // Characters State
    // Custom Hooks
    const { 
        characters, 
        activeCharacterId, 
        activeCharacter, 
        switchCharacter: switchCharacterBackend, 
        setCharacters 
    } = useCharacterState();
    
    // Local State
    const [userName, setUserName] = useState<string>('Master'); // Default User Name
    const [isSettingsLoaded, setIsSettingsLoaded] = useState(false); // ⚡ Prevent FOUC

    // ⚡ Track previous LLM settings for change detection
    const prevApiKeyRef = useRef<string>('');
    const prevBaseUrlRef = useRef<string>('');
    const prevModelRef = useRef<string>('');

    // Conversation Memory
    const [conversationHistory, setConversationHistory] = useState<Message[]>([]);
    const [conversationSummary, setConversationSummary] = useState<string>(''); // 历史摘要
    const [contextWindow, setContextWindow] = useState(15); // 默认保留15轮
    const [autoSummarizationEnabled, setAutoSummarizationEnabled] = useState(true);
    const [live2dHighDpi, setLive2dHighDpi] = useState(false);
    // ⚡ DeepSeek R1 Thinking Mode
    const [isThinkingEnabled, setIsThinkingEnabled] = useState(true); // Default to True to showcase feature
    const [reasoningContent, setReasoningContent] = useState('');

    // TTS 模块引用
    const audioQueueRef = useRef<AudioQueue>(new AudioQueue());
    const sentenceSplitterRef = useRef<SentenceSplitter | null>(null);
    const synthPromisesRef = useRef<Promise<void>[]>([]); // Promise 队列维持顺序
    const emotionBufferRef = useRef<string>(''); // Buffer for detecting tags in stream

    // Function to process emotion tags from accumulated text
    const handleProcessEmotions = (text: string) => {
        processEmotions(text, {
            activeCharacter,
            live2dRef
        });
    };

    // TTS 合成策略: 
    // - 允许多句并发合成（不阻塞）
    // - 但必须按顺序入队到 AudioQueue（保证播放顺序）
    const enqueueSynthesis = (sentence: string, index: number) => {
        const synthPromise = (async () => {
            // ⚡ 修复: 过滤空句子和纯符号句子（防止发送 ".&" 到 GPT-SoVITS）
            const cleanSentence = sentence.replace(/[。！？.!?,，、；&\n\s]/g, '').trim();
            if (cleanSentence.length === 0) {
                console.log(`[TTS] Skipping empty/symbol-only sentence: "${sentence}"`);
                return;
            }

            console.log(`[TTS] Starting synthesis ${index}:`, sentence);
            try {
                // ⚡ 移除 '&' 断句符（GPT-SoVITS 不认识，会导致合成问题）
                const cleanedSentence = sentence.replace(/&/g, '');

                // 1️⃣ 立即开始合成（并发，不等待前一句）
                const audioResponse = await ttsService.synthesize(cleanedSentence);

                // 2️⃣ 等待前一句入队完成（保证顺序）
                if (index > 0) {
                    await synthPromisesRef.current[index - 1];
                }

                // 3️⃣ 按顺序入队
                if (audioResponse) {
                    audioQueueRef.current.enqueue(audioResponse);
                    console.log(`[TTS] Enqueued stream for sentence ${index} (Queue length: ${audioQueueRef.current.length})`)
                }
            } catch (error) {
                console.error(`[TTS] Synthesis failed for ${index}:`, error);
            }
        })();

        synthPromisesRef.current[index] = synthPromise;
    };

    // Helper: Apply Active Character
    const applyCharacter = async (character: CharacterProfile, uName: string) => {
        console.log(`[App] Applying character: ${character.name} for user: ${uName}`);

        // ✅ 直接使用后端返回的 System Prompt（后端已包含 custom_prompt）
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/soul`);
            if (res.ok) {
                const soul = await res.json();
                const systemPrompt = soul.system_prompt || '';
                console.log(`[App] Setting System Prompt from Backend (Length: ${systemPrompt.length})`);
                (window as any).llm.setSystemPrompt(systemPrompt);
            }
        } catch (e) {
            console.error('[App] Failed to fetch soul for prompt:', e);
        }

        // Update TTS Voice Configuration
        if (character.voiceConfig?.voiceId) {
            const engine = character.voiceConfig.service || 'edge-tts';
            console.log(`[App] Switching TTS Voice to: ${character.voiceConfig.voiceId} (Engine: ${engine})`);
            ttsService.setDefaultVoice(character.voiceConfig.voiceId);
            ttsService.setEngine(engine);
        }
    };

    // ⚡ 角色切换处理
    const handleCharacterSwitch = async (newCharacterId: string) => {
        if (newCharacterId === activeCharacterId) return;

        // 1. Delegate to Hook (Backend Switch + Memory Config + State Update)
        const success = await switchCharacterBackend(newCharacterId);
        if (!success) return;

        // 2. Clear History & Reset App State
        setConversationHistory([]);
        setConversationSummary('');
        isDreamingRef.current = false;
        startupExecutedRef.current = true;

        // 3. Apply New Character Config (Voice & System Prompt)
        const newChar = characters.find(c => c.id === newCharacterId);
        if (newChar) {
            await applyCharacter(newChar, userName);
        }

        console.log(`[App] ✅ Character switched to: ${newCharacterId}`);
    };


    // --- Event Bus Listeners ---
    useEffect(() => {
        const handleInterruption = () => {
            console.log('[App] Interruption Event Received');
            
            // 1. Stop Audio Queue
            if (audioQueueRef.current) {
                audioQueueRef.current.clear();
            }
            
            // 2. Stop TTS (if playing)
            ttsService.stop();
            
            // 3. Reset Live2D
            if (live2dRef.current) {
                live2dRef.current.stopExpression();
            }
        };

        const u1 = events.on('audio:vad.start', handleInterruption); // Voice Interruption
        const u2 = events.on('core:interrupt', handleInterruption);  // Manual/Text Interruption

        return () => {
            u1();
            u2();
        };
    }, []);

    // Load all settings on mount
    useEffect(() => {
        const loadSettings = async () => {
            const settings = (window as any).settings;
            try {
                // LLM Settings
                const apiKey = await settings.get('apiKey');
                const baseUrl = await settings.get('apiBaseUrl') || 'https://api.deepseek.com/v1';
                const model = await settings.get('modelName') || 'deepseek-chat';

                // ⚡ Initialize refs with loaded values to prevent false-positive reconfigure
                prevApiKeyRef.current = apiKey || '';
                prevBaseUrlRef.current = baseUrl;
                prevModelRef.current = model;

                // User Settings
                const loadedUserName = await settings.get('userName') || 'Master';
                setUserName(loadedUserName);
                
                // Note: Character fetching is now handled by usage of useCharacterState

                if (apiKey) {
                    console.log('[App] Initializing LLM Service with loaded settings');
                    // llmService.init(apiKey, baseUrl, model); -> Handled in Main Process on settings:set

                    // Initialize Memory Service
                    console.log('[App] Initializing Memory Service');
                    // memoryService.setCharacter(loadedActiveId); // ⚡ Sync Memory Service State - Handled by useCharacterState
                    memoryService.configure(apiKey, baseUrl, model);

                    // Apply Active Character - Handled by dedicated useEffect below
                } else {
                    console.warn('[App] No API Key found in settings');
                }

                // Memory Settings
                const windowSize = await settings.get('contextWindow');
                setContextWindow(windowSize || 50);

                // Live2D Settings
                const highDpi = await settings.get('live2d_high_dpi');
                setLive2dHighDpi(highDpi || false);

            } catch (error) {
                console.error('[App] Failed to load settings:', error);
            }
        };

        loadSettings().then(() => {
            console.log('[App] Settings & Characters Initialization Complete.');
            setIsSettingsLoaded(true); // ⚡ Only render UI after this
        });

        // [Startup] Trigger Dreaming Cycle on App Launch
        // "Recall the past when waking up"
        if (!startupExecutedRef.current) {
            startupExecutedRef.current = true;
            setTimeout(() => {
                console.log('[App] 🌅 Startup Dreaming Cycle Initiated...');
                fetch(`${API_CONFIG.BASE_URL}/dream/wake_up`, { method: 'POST' })
                    .catch(e => console.warn("[App] Startup Dreaming failed:", e));
            }, 5000); // Wait 5s for backend to be fully ready
        }
    }, []);

    // Sync active character when it changes
    useEffect(() => {
        if (activeCharacter && userName) {
            // Apply character config when active character is loaded/changed
            applyCharacter(activeCharacter, userName).catch(console.error);
        }
    }, [activeCharacterId, userName, activeCharacter]); // activeCharacter derived from ID

    const lastActivityTime = useRef<number>(Date.now());
    const currentSystemPromptRef = useRef<string>(''); // Track System Prompt (Static)
    const dynamicInstructionRef = useRef<string>(''); // Track Dynamic Instruction (Mood/Trades/Values)
    const isDreamingRef = useRef<boolean>(false); // Track dreaming state
    const startupExecutedRef = useRef<boolean>(false); // ⚡ Prevent double execution in StrictMode
    const IDLE_THRESHOLD_MS = 15 * 60 * 1000; // 15 Minutes

    // Heartbeat to check idle status AND Backend Proactive Trigger (Dual Check)
    useEffect(() => {
        const interval = setInterval(async () => {
            const now = Date.now();
            const inactiveDuration = now - lastActivityTime.current;
            const inactiveMinutes = (inactiveDuration / 60000).toFixed(1);

            // 1. Frontend Idle Check (Dreaming)
            if (inactiveDuration > IDLE_THRESHOLD_MS) {
                if (!isDreamingRef.current) {
                    console.log(`[Dreaming] 🌙 User has been idle for ${inactiveMinutes} mins. Triggering Dreaming...`);
                    isDreamingRef.current = true; // Prevent multiple triggers
                    fetch(`${API_CONFIG.BASE_URL}/dream/wake_up`, { method: 'POST' })
                        .catch(err => console.error("[Dreaming] Trigger failed:", err));
                }
            } else {
                if (Math.floor(inactiveDuration / 1000) % 60 === 0) {
                    // console.log(`[Dreaming] ⏱️ User inactive for ${inactiveMinutes} min...`);
                }
            }

            // NOTE: Proactive Chat is handled by a dedicated useEffect with locking below.
            // Do NOT add proactive check here to avoid duplicate triggers.

        }, 5000); // Check every 5 seconds

        return () => clearInterval(interval);
    }, [activeCharacterId, isProcessing, isStreaming]);





    const resetIdleTimer = () => {
        lastActivityTime.current = Date.now();
        if (isDreamingRef.current) {
            console.log('[Dreaming] Activity detected. Waking up from dreaming state.');
            isDreamingRef.current = false;
        }
    };

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
        // ⚡ Only reconfigure if settings actually changed
        if (apiKey === prevApiKeyRef.current && baseUrl === prevBaseUrlRef.current && model === prevModelRef.current) {
            console.log('[App] LLM settings unchanged, skipping reconfigure.');
            return;
        }

        console.log('[App] 🔄 LLM settings changed, reconfiguring...');
        console.log(`[App] Old: ${prevApiKeyRef.current?.substring(0, 8)}... | New: ${apiKey?.substring(0, 8)}...`);

        // Update refs
        prevApiKeyRef.current = apiKey;
        prevBaseUrlRef.current = baseUrl;
        prevModelRef.current = model;

        // Only now call configure
        memoryService.configure(apiKey, baseUrl, model);
    };

    // Character update handler
    const handleCharactersUpdated = (newCharacters: CharacterProfile[], newActiveId: string) => {
        console.log('[App] Handling character update');
        setCharacters(newCharacters);

        const oldActiveId = activeCharacterId;

        // Update active ID if changed
        if (newActiveId !== activeCharacterId) {
            // setActiveCharacterId(newActiveId); // Handled by useCharacterState
            // Trigger character switch logic
            handleCharacterSwitch(newActiveId);
        }

        // Determine if we need to re-apply prompt/voice
        const activeChar = newCharacters.find(c => c.id === newActiveId) || newCharacters[0];
        const oldChar = characters.find(c => c.id === oldActiveId);

        // ⚡ Smart Update: Only re-apply if critical core settings changed (Voice, Model, Prompt)
        // Simple flags like 'galgameModeEnabled' or 'proactiveChatEnabled' should NOT trigger a reload.
        let shouldReload = false;
        if (newActiveId !== oldActiveId) shouldReload = true;
        else if (oldChar) {
            if (activeChar.voiceConfig?.voiceId !== oldChar.voiceConfig?.voiceId) shouldReload = true;
            if (activeChar.modelPath !== oldChar.modelPath) shouldReload = true;
            if (activeChar.systemPrompt !== oldChar.systemPrompt) shouldReload = true;
        } else {
            shouldReload = true; // Fallback
        }

        if (shouldReload) {
            console.log('[App] 🔄 Critical character settings changed, reloading core...', activeChar.name);
            applyCharacter(activeChar, userName);
        } else {
            console.log('[App] ✨ Lightweight setting update (skipped core reload).');
        }
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

    const handleLive2DHighDpiChange = (enabled: boolean) => {
        console.log(`[App] Live2D High DPI changed to: ${enabled}`);
        setLive2dHighDpi(enabled);
    };

    const handleSend = async (text: string, options?: { 
        temperature?: number; 
        topP?: number; 
        presencePenalty?: number; 
        frequencyPenalty?: number;
        enableThinking?: boolean;
    }) => {
        resetIdleTimer();
        
        // ⚡ Global Heartbeat Reset: Tell Backend we are active!
        // This ensures the "Proactive Chat" timer is reset regardless of which LLM is used.
        fetch(`${API_CONFIG.BASE_URL}/soul/interact`, { method: 'POST' }).catch(e => console.warn('[App] Failed to signal interaction:', e));

        // ⚡ Fetch Route-Specific Params for Chat if not provided (User Message)
        let gptOptions = options;
        if (!gptOptions) {
            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/params/chat`);
                if (res.ok) {
                    const data = await res.json();
                    gptOptions = {
                        temperature: data.temperature,
                        topP: data.top_p,
                        presencePenalty: data.presence_penalty,
                        frequencyPenalty: data.frequency_penalty
                    };
                    console.log('[App] ⚙️ Applying "Chat" route parameters:', gptOptions);
                }
            } catch (e) {
                console.warn('[App] Failed to fetch chat parameters, using service defaults.');
            }
        }

        setIsProcessing(true);
        setIsStreaming(true);
        setCurrentMessage(''); // Clean old message
        synthPromisesRef.current = []; // 清空 Promise 队列
        let sentenceIndex = 0;

        // 添加用户消息到历史 (Skip for System Instructions)
        let userMessage: Message | null = null;
        if (!text.trim().startsWith('(Private System Instruction')) {
            userMessage = {
                role: 'user',
                content: text,
                timestamp: Date.now()
            };
            setConversationHistory(prev => [...prev, userMessage!]);
        }

        try {
            // 1. Retrieve Relevant Memories (Hybrid Memory L3)
            let relevantMemories = '';
            try {
                // Only search if not empty AND not a system instruction (which handles its own inspiration)
                if (text.trim().length > 2 && !text.startsWith('(Private System Instruction')) {
                    console.log('[Memory] Searching for relevant memories...');
                    const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];
                    relevantMemories = await memoryService.search(text, 10, userName, activeChar.name);
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

            // 使用 Ref 来存储累积的响应，防止闭包过时问题
            const fullRawResponseRef = { current: '' };
            emotionBufferRef.current = '';
            // ⚡ Thinking Mode Buffer
            const reasoningBufferRef = { current: '' };

            const onToken = (token: string, type: 'content' | 'reasoning' = 'content') => {
                if (type === 'reasoning') {
                    // Accumulate reasoning
                    reasoningBufferRef.current += token;
                    // Update UI state for thinking process (e.g. separate from main message)
                    // If you have a specific state for this, set it here.
                    // For now, we can prepend it to the message OR use a dedicated state.
                    // Let's use a dedicated callback or state if available, but for now let's just log it 
                    // or append it in a special way if valid.
                    // Actually, let's create a NEW state for reasoning content to display it separately.
                    setReasoningContent(reasoningBufferRef.current);
                    return; 
                }

                // Normal Content Handling
                // Accumulate in Ref
                fullRawResponseRef.current += token;
                emotionBufferRef.current += token;

                // 1. Check for complete (emotion) tags or [emotion] tags to trigger Live2D
                if (token.includes(')') || token.includes(']') || token.includes('）')) {
                    // Try to finding known emotions in the buffer
                    
                    // Determine Model Name from Path
                    // e.g. "public/live2d/Hiyori/Hiyori.model3.json" -> "Hiyori"
                    const activeChar = characters.find(c => c.id === activeCharacterId);
                    let modelName = 'default';
                    // ⚡ FIX: Use 'modelPath' instead of 'live2dPath'
                    if (activeChar && activeChar.modelPath) {
                        const parts = activeChar.modelPath.split('/');
                        // Usually [public, live2d, ModelName, file.model3.json] or just relative
                        // If path is absolute or different, this heuristic might need adjustment
                        // e.g. "public/live2d/Hiyori/Hiyori.model3.json" -> parts[...-2] = "Hiyori"
                        if (parts.length >= 2) {
                             // Taking the parent folder name is the safest guess for Model Name
                             // e.g. "live2d/Mao/mao.model3.json" -> "Mao"
                             modelName = parts[parts.length - 2];
                        }
                    }

                    // Select correct map
                    const currentMap = (EMOTION_MAP as any)[modelName] || (EMOTION_MAP as any)['default'] || {};

                    // Find matching emotion
                    for (const [keyword, motion] of Object.entries(currentMap)) {
                        // Check if buffer contains this keyword (e.g. "Happy", "Sad")
                        // Case insensitive check
                        if (emotionBufferRef.current.toLowerCase().includes(keyword.toLowerCase())) {
                            console.log(`[App] Emotion Detected: ${keyword} -> Triggering Motion`, motion);
                            if (live2dRef.current) {
                                live2dRef.current.motion((motion as any).group, (motion as any).index);
                            }
                            emotionBufferRef.current = ''; // Reset buffer after trigger
                            break;
                        }
                    }
                    
                    // Cap buffer size
                    if (emotionBufferRef.current.length > 50) {
                         emotionBufferRef.current = emotionBufferRef.current.slice(-20);
                    }
                }

                // 2. Filter for Display
                // Improved Logic: 
                // - Only verify balanced brackets if possible, otherwise be lenient.
                // - Handle nested brackets by strictly matching innermost or just ignoring nesting for now.
                // - Stop stripping incomplete tags at the end to prevent "flickering" or data loss if tag is malformed? 
                //   Actually hiding incomplete tags is good UX, but let's be safer.

                let displayUpdate = fullRawResponseRef.current;

                // Remove complete [tag] and (tag) - Non-greedy
                displayUpdate = displayUpdate.replace(/\[[^\]]*\]/g, '').replace(/\([^)]*\)/g, '').replace(/（[^）]*）/g, '');

                // ⚡ 移除 TTS 断句符号 '&' (用户不应该看到)
                displayUpdate = displayUpdate.replace(/&/g, '');

                // Remove incomplete trailing tags (Visual polish, but risky if stream pauses)
                // Only remove if it looks like a started tag (short length)
                displayUpdate = displayUpdate.replace(/\[[^\]]{0,20}$/, '');
                displayUpdate = displayUpdate.replace(/\([^)]{0,20}$/, '');

                setCurrentMessage(displayUpdate);

                // 3. Feed RAW token to splitter 
                if (isTTSEnabled && sentenceSplitterRef.current) {
                    sentenceSplitterRef.current.feedToken(token);
                }
            };

            const onEnd = () => {
                // 1. Calculate Final Content FIRST
                const finalCleanContent = fullRawResponseRef.current
                    .replace(/\[[^\]]*\]/g, '') // Ensure brackets are gone
                    .replace(/\([^)]*\)/g, '')  // Remove parens
                    .replace(/&/g, '')          // Remove TTS markers
                    .trim();

                // 2. Force flush final message (before stopping stream) to update UI
                setCurrentMessage(finalCleanContent);

                console.log('[App] Stream ended');
                
                // 3. Stop Stream State
                setIsStreaming(false);
                setIsProcessing(false);

                // 4. Flush TTS Splitter
                if (isTTSEnabled && sentenceSplitterRef.current) {
                    sentenceSplitterRef.current.flush();
                }

                // 5. Create History Object
                // Include Reasoning Content if available? 
                // Maybe as metadata or hidden field? For now, we only store content.
                const assistantMessage: Message = {
                    role: 'assistant',
                    content: finalCleanContent,
                    timestamp: Date.now()
                };

                // 使用临时变量，因为 state 更新是异步的
                setConversationHistory(prev => {
                    const updatedHistory = [...prev, assistantMessage];

                    // --- Smart Pruning / Smart Archive Logic (L3) ---
                    // DeepSeek Cache Strategy: Keep distinct prefix as long as possible.
                    // Don't prune 1-by-1. Prune in bulk when limit reached.

                    // Limit: 200 turns = 400 messages (Soft Limit)
                    const PRUNING_THRESHOLD = 400;

                    if (updatedHistory.length > PRUNING_THRESHOLD) {
                        console.log(`[Memory] History length (${updatedHistory.length}) exceeded threshold (${PRUNING_THRESHOLD}). Triggering Smart Pruning...`);

                        // Strategy: Archive oldest 70%, Keep recent 30%
                        const keepRatio = 0.3;
                        const keepCount = Math.floor(PRUNING_THRESHOLD * keepRatio); // ~120 msgs
                        const archiveCount = updatedHistory.length - keepCount;      // ~280+ msgs

                        const messagesToArchive = updatedHistory.slice(0, archiveCount);
                        const messagesToKeep = updatedHistory.slice(archiveCount);

                        console.log(`[Memory] Archiving ${messagesToArchive.length} messages, Keeping ${messagesToKeep.length}.`);

                        // 1. Send to Backend for Consolidation (Dreaming/VectorDB)
                        const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];
                        memoryService.consolidateHistory(messagesToArchive, userName, activeChar.name);

                        // 2. Update Frontend State (The "Cache Break" happens here once)
                        return messagesToKeep;
                    }

                    return updatedHistory;
                });

                // --- Async: Add to Long-Term Memory (L3) --- (Need activeChar and userName)
                // Note: activeCharacterId, characters, userName are closure vars.
                const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];
                const messagesToStore = userMessage ? [userMessage, assistantMessage] : [assistantMessage];

                memoryService.add(messagesToStore, userName, activeChar.name)
                    .catch(err => console.error('[Memory] Failed to store interaction:', err));

                // Cleanup
                (window as any).llm.removeStreamListeners();
            };

            // Setup Listeners BEFORE sending request
            (window as any).llm.onStreamToken(onToken);
            (window as any).llm.onStreamEnd(onEnd); // This will handle cleanup too via our wrapper logic if we want, but let's be explicit

            // Send Request via IPC with complete parameters
            const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];

            // Determine role based on content
            const isSystemInstruction = text.startsWith('(Private System Instruction');
            const messageRole = isSystemInstruction ? 'system' : 'user';

            // ⚡ Mix RAG Context + Dynamic Instruction (Split Prompt Strategy)
            let dynamicState = dynamicInstructionRef.current || '';

            // 🛡️ Just-In-Time Fetch Override (Fixes "Missing Soul" race condition)
            if (!dynamicState && activeCharacterId) {
                console.log('[App] ⚠️ Dynamic State undefined, performing JIT fetch...');
                try {
                    const res = await fetch(`${API_CONFIG.BASE_URL}/galgame/${activeCharacterId}/state`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.dynamic_instruction) {
                            dynamicState = data.dynamic_instruction;
                            dynamicInstructionRef.current = dynamicState; // Update Ref too
                            console.log('[App] ✅ JIT Fetch Successful, length:', dynamicState.length);
                        }
                    }
                } catch (e) {
                    console.error('[App] JIT Fetch failed:', e);
                }
            }
            // const finalContext = (relevantMemories ? relevantMemories + "\n\n" : "") + dynamicState; 
            // ❌ Don't mix them! Pass separately to fix "Related Memories" header issue.

            console.log(`[App] Sending Context: RAG(${relevantMemories ? relevantMemories.length : 0} chars) + Dynamic(${dynamicState.length} chars)`);

            (window as any).llm.chatStreamWithHistory(
                conversationHistory,
                text,
                contextWindow,
                conversationSummary,
                relevantMemories,   // ✅ Pass RAG Only (Wrapped with Header in Main)
                userName,
                activeChar.name,
                messageRole,
                dynamicState,       // ✅ Pass Dynamic Instruction Separately (No Header Wrapper)
                options?.enableThinking ?? isThinkingEnabled,
                options?.temperature,
                options?.topP,
                options?.presencePenalty,
                options?.frequencyPenalty
            );

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

    // ⚡ Proactive Chat Hook (Must be after handleSend)
    useProactiveChat({
        activeCharacterId,
        isProcessing,
        isStreaming,
        characters,
        conversationHistory,
        userName,
        dynamicInstructionRef,
        currentSystemPromptRef,
        onSend: handleSend
    });

    // Proactive Interaction Loop
    const handleSendRef = React.useRef(handleSend);
    const isProcessingRef = React.useRef(isProcessing); // Add Ref for state

    useEffect(() => {
        handleSendRef.current = handleSend;
        isProcessingRef.current = isProcessing; // Sync Ref
    });

    // ⚡ Dynamic System Prompt Sync (从后端获取最新的 System Prompt)
    // 注意：Proactive Interaction 检查已移至 L430-505 的多角色版本
    useEffect(() => {
        const timer = setInterval(async () => {
            if (isProcessingRef.current) return;
            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/soul`);
                if (!res.ok) return;
                const soul = await res.json();

                // Dynamic System Prompt Update
                // Only update if content changed significantly to avoid jitter
                if (soul.system_prompt && soul.system_prompt !== currentSystemPromptRef.current) {
                    console.log('[App] 🧠 System Prompt Dynamically Updated from Backend');
                    (window as any).llm.setSystemPrompt(soul.system_prompt);
                    currentSystemPromptRef.current = soul.system_prompt;
                }

                // Update Dynamic Instruction Ref
                if (soul.dynamic_instruction) {
                    dynamicInstructionRef.current = soul.dynamic_instruction;
                }
                // ⚡ 移除：pending_interaction 检查已由 L430-505 多角色版本处理
            } catch (e) { }
        }, 5000);
        return () => clearInterval(timer);
    }, []);

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: 'url(/bg.png)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            overflow: 'hidden',
            margin: 0,
            padding: 0
        }}>

            {/* Live2D Layer */}
            {/* Live2D Layer - Block until settings loaded to prevent Hiyori Flash */}
            {isSettingsLoaded ? (() => {
                const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];
                const modelPath = activeChar?.modelPath || "./live2d/Hiyori/Hiyori.model3.json";
                console.log(`[App] Rendering Live2D for: ${activeCharacterId}, Path: ${modelPath}`);
                return (
                    <Live2DViewer
                        key={modelPath} // Force remount on model change
                        ref={live2dRef}
                        modelPath={modelPath}
                        highDpi={live2dHighDpi}
                    />
                );
            })() : (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#666' }}>
                    Loading Soul...
                </div>
            )}

            {/* GalGame Mode HUD */}
            {isSettingsLoaded && (
                <GalGameHud
                    activeCharacterId={activeCharacterId}
                    onOpenSurrealViewer={() => setIsSurrealViewerOpen(true)}
                    galgameEnabled={activeCharacter?.galgameModeEnabled ?? true}
                />
            )}

            {/* UI Layer */}
            <ChatBubble 
                message={currentMessage} 
                isStreaming={isStreaming} 
                reasoning={reasoningContent}
            />

            {chatMode === 'text' ? (
                <InputBox onSend={handleSend} disabled={isProcessing} />
            ) : (
                <VoiceInput
                    onSend={handleSend}
                    disabled={isProcessing}
                    onSpeechStart={handleUserSpeechStart}
                />
            )}

            <div style={{ position: 'absolute', top: 30, right: 30, display: 'flex', flexDirection: 'column', gap: 15, zIndex: 100 }}>
                {/* Toggle Mode Button */}
                <button
                    onClick={() => setChatMode(chatMode === 'text' ? 'voice' : 'text')}
                    title={chatMode === 'text' ? "Switch to Voice Mode" : "Switch to Text Mode"}
                    style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        backgroundColor: chatMode === 'voice' ? 'rgba(255, 107, 107, 0.2)' : 'rgba(76, 175, 80, 0.2)',
                        color: 'white',
                        border: '1px solid rgba(255,255,255,0.3)',
                        backdropFilter: 'blur(10px)',
                        display: 'flex', justifyContent: 'center', alignItems: 'center',
                        cursor: 'pointer',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                        transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.1)')}
                    onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
                >
                    {chatMode === 'text' ? <Mic size={24} /> : <Keyboard size={24} />}
                </button>

                {/* Settings Button */}
                <button
                    onClick={() => setIsSettingsOpen(true)}
                    title="Settings"
                    style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        backgroundColor: 'rgba(33, 150, 243, 0.2)',
                        color: 'white',
                        border: '1px solid rgba(255,255,255,0.3)',
                        backdropFilter: 'blur(10px)',
                        display: 'flex', justifyContent: 'center', alignItems: 'center',
                        cursor: 'pointer',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                        transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.1)')}
                    onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
                >
                    <SettingsIcon size={24} />
                </button>

                {/* Motion Tester Button */}
                <button
                    onClick={() => setIsMotionTesterOpen(true)}
                    title="Motion Tester"
                    style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        backgroundColor: 'rgba(156, 39, 176, 0.2)',
                        color: 'white',
                        border: '1px solid rgba(255,255,255,0.3)',
                        backdropFilter: 'blur(10px)',
                        display: 'flex', justifyContent: 'center', alignItems: 'center',
                        cursor: 'pointer',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                        transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.1)')}
                    onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
                >
                    <Activity size={24} />
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
                onLive2DHighDpiChange={handleLive2DHighDpiChange}
                onCharacterSwitch={handleCharacterSwitch}
                activeCharacterId={activeCharacterId} // ⚡ Pass prop
                onThinkingModeChange={setIsThinkingEnabled}
            />

            {/* Motion Tester */}
            <MotionTester
                isOpen={isMotionTesterOpen}
                onClose={() => setIsMotionTesterOpen(false)}
                onTriggerMotion={(group, index) => {
                    if (live2dRef.current) {
                        console.log(`[App] Motion Tester triggered: ${group} ${index}`);
                        live2dRef.current.motion(group, index);
                    }
                }}
            />

            {/* Memory Core (SurrealDB Explorer) */}
            <SurrealViewer
                isOpen={isSurrealViewerOpen}
                onClose={() => setIsSurrealViewerOpen(false)}
                activeCharacterId={activeCharacterId}
            />
        </div>
    );

}

export default App;
