import React, { useState, useRef, useEffect } from 'react'
import Live2DViewer, { Live2DViewerRef } from './live2d-view/Live2DViewer'
import ChatBubble from './components/ChatBubble'
import InputBox from './components/InputBox'
import VoiceInput from './components/VoiceInput'
import SettingsModal from './components/SettingsModal'
import MotionTester from './components/MotionTester'
import SurrealViewer from './components/SurrealViewer'
import GalGameHud from './components/GalGameHud' // Integrated Soul HUD
import { ttsService } from '@core/voice/tts_service'
import { SentenceSplitter } from '@core/voice/sentence_splitter'
import { AudioQueue } from '@core/voice/audio_queue'
import { Message, CharacterProfile, DEFAULT_CHARACTERS } from '@core/llm/types'
import { memoryService } from '@core/memory/memory_service'

import emotionMapRaw from './emotion_map.json';

const emotionMap: Record<string, { group: string, index: number }> = emotionMapRaw;

// Helper to clean text for TTS (remove emojis and [emotion] tags)
const cleanTextForTTS = (text: string): string => {
    return text
        .replace(/\[[^\]]*\]/g, '') // Remove [text]
        .replace(/[\(（][^)）]*[\)）]/g, '') // Also remove (text) / （text） just in case
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
    const [characters, setCharacters] = useState<CharacterProfile[]>([]);
    const [activeCharacterId, setActiveCharacterId] = useState<string>('');
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

    // TTS 模块引用
    const audioQueueRef = useRef<AudioQueue>(new AudioQueue());
    const sentenceSplitterRef = useRef<SentenceSplitter | null>(null);
    const synthPromisesRef = useRef<Promise<void>[]>([]); // Promise 队列维持顺序
    const emotionBufferRef = useRef<string>(''); // Buffer for detecting tags in stream

    // Function to process emotion tags from accumulated text
    const processEmotions = (text: string) => {
        console.log('[App] processEmotions called with text:', text);
        // Regex to find all [emotion] tags (and fallback to parens)
        const matches = text.matchAll(/(?:\[([^\]]+)\])|(?:[\(（]([^)）]+)[\)）])/g);
        const matchesArray = Array.from(matches);
        console.log('[App] Found emotion tag matches:', matchesArray.length);

        for (const match of matchesArray) {
            // match[1] is [content], match[2] is (content)
            const emotionContent = (match[1] || match[2] || '').trim().toLowerCase();
            console.log('[App] Processing emotion content:', emotionContent);

            // Check if we have a mapping for any word in the content
            let emotionFound = false;

            // Define mutation effects
            // [sad]/[angry] -> Energy -1
            // [happy]/[love] -> Intimacy +1
            // [shy]/[hopeful] -> Intimacy +0.5
            let d_energy = 0;
            let d_intimacy = 0;
            
            if (emotionContent.includes('sad') || emotionContent.includes('angry') || emotionContent.includes('depress') || emotionContent.includes('cry')) {
                 d_energy = -1;
                 d_intimacy = -1; // Negative emotions decrease intimacy
            } else if (emotionContent.includes('happy') || emotionContent.includes('love') || emotionContent.includes('joy') || emotionContent.includes('excite')) {
                 d_intimacy = 0.5;
                 d_energy = 0.2;
            } else if (emotionContent.includes('shy') || emotionContent.includes('hope')) {
                 d_intimacy = 0.2;
                 d_energy = -0.5;
            }
    
            // Call Backend Mutation API if there is a change
            if (d_energy !== 0 || d_intimacy !== 0) {
                console.log(`[App] 🧬 Mutating Soul: Energy ${d_energy}, Intimacy ${d_intimacy}`);
                // Fire and forget, don't block UI
                fetch(`http://localhost:8001/soul/mutate?pleasure=0&arousal=0&dominance=0&intimacy=${d_intimacy}&energy=${d_energy}`, { 
                    method: 'POST' 
                }).catch(e => console.error("[App] Failed to mutate soul:", e));
            }

            for (const [key, motion] of Object.entries(emotionMap)) {
                if (emotionContent.includes(key)) {
                    console.log(`[App] ✅ Triggering emotion: "${key}" -> Motion: ${motion.group} index ${motion.index}`);
                    if (live2dRef.current) {
                        live2dRef.current.motion(motion.group, motion.index);
                    } else {
                        console.warn('[App] ⚠️ live2dRef.current is null!');
                    }
                    emotionFound = true;
                    break; // Trigger only one emotion per tag
                }
            }
            if (!emotionFound) {
                console.log(`[App] ❌ No emotion mapping found for: "${emotionContent}"`);
            }
        }
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
            const res = await fetch('http://localhost:8001/soul');
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
        console.log(`[App] 🔄 Switching character to: ${newCharacterId}`);
        
        if (newCharacterId === activeCharacterId) {
            console.log('[App] Already on this character, skipping switch');
            return;
        }
        
        // 1. 更新活跃角色
        setActiveCharacterId(newCharacterId);
        
        // 2. 清空当前对话历史（新角色重新开始）
        setConversationHistory([]);
        setConversationSummary('');
        
        // 3. 通知后端切换角色（重要！确保 soul_client 切换）
        try {
            const response = await fetch('http://localhost:8001/soul/switch_character', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ character_id: newCharacterId })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log(`[App] ✅ Backend switched to: ${data.character_name}`);
            } else {
                console.error('[App] Backend character switch failed:', await response.text());
            }
        } catch (error) {
            console.error('[App] Failed to notify backend about character switch:', error);
        }
        
        // 4. 重新配置 Memory Service（切换到新角色的记忆库）
        try {
            const settings = (window as any).settings;
            const apiKey = await settings.get('apiKey');
            const baseUrl = await settings.get('apiBaseUrl') || 'https://api.deepseek.com/v1';
            const model = await settings.get('modelName') || 'deepseek-chat';
            
            console.log(`[App] Reconfiguring memory for character: ${newCharacterId}`);
            await memoryService.configure(apiKey, baseUrl, model, newCharacterId);
        } catch (error) {
            console.error('[App] Failed to reconfigure memory:', error);
        }
        
        // 5. 应用新角色配置（system prompt, voice 等）
        const newChar = characters.find(c => c.id === newCharacterId);
        if (newChar) {
            await applyCharacter(newChar, userName);
        }
        
        // 5. 保存到 localStorage
        const settings = (window as any).settings;
        await settings.set('activeCharacterId', newCharacterId);
        
        console.log(`[App] ✅ Character switched to: ${newCharacterId}`);
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
                
                // ⚡ Initialize refs with loaded values to prevent false-positive reconfigure
                prevApiKeyRef.current = apiKey || '';
                prevBaseUrlRef.current = baseUrl;
                prevModelRef.current = model;

                // User Settings
                const loadedUserName = await settings.get('userName') || 'Master';
                setUserName(loadedUserName);

                // Character Settings
                // ⚡ Fetch characters from Backend API (Single Source of Truth)
                let loadedCharacters: CharacterProfile[] = [];
                try {
                    const charRes = await fetch('http://localhost:8001/characters');
                    if (charRes.ok) {
                        const data = await charRes.json();
                        // Backend returns { characters: [...] }
                        // ⚡ MAPPING: Convert Backend (snake_case) to Frontend (camelCase)
                        loadedCharacters = (data.characters || []).map((char: any) => ({
                            id: char.character_id,
                            name: char.name,
                            description: char.description,
                            avatar: char.avatar || '',
                            modelPath: char.live2d_model,
                            systemPrompt: char.system_prompt,
                            voiceConfig: char.voice_config
                        }));
                        console.log(`[App] Loaded ${loadedCharacters.length} characters from Backend API`);
                    } else {
                        console.warn('[App] Failed to fetch characters from API, falling back to defaults');
                    }
                } catch (e) {
                    console.error('[App] Error fetching characters:', e);
                }

                if (loadedCharacters.length === 0) {
                     console.warn('[App] No characters found (API empty/failed). Backend likely offline.');
                     // ⚡ Prevent fallback to DEFAULT_CHARACTERS to avoid polling invalid 'lumina_default'
                     // loadedCharacters = DEFAULT_CHARACTERS;
                }

                // Update local 'characters' cache for other components if needed (optional)
                await settings.set('characters', loadedCharacters);

                let loadedActiveId = await settings.get('activeCharacterId') as string;

                // Migration / Default Init
                if (!loadedCharacters || loadedCharacters.length === 0) {
                    // Logic handled above
                }

                // Ensure active character ID is valid and exists in current list
                const characterExists = loadedCharacters.some(c => c.id === loadedActiveId);
                
                if (!loadedActiveId || !characterExists) {
                     if (loadedCharacters.length > 0) {
                         console.warn(`[App] Active ID '${loadedActiveId}' not found in loaded characters. Resetting to default.`);
                         loadedActiveId = loadedCharacters[0].id;
                         await settings.set('activeCharacterId', loadedActiveId);
                     } else {
                         // ⚡ Clear ID if no characters available (stop polling)
                         loadedActiveId = '';
                         await settings.set('activeCharacterId', '');
                     }
                }
                
                console.log(`[App] Init Active Character: ${loadedActiveId}`);
                console.log('[App] Available Character IDs:', loadedCharacters.map(c => c.id));

                setCharacters(loadedCharacters);
                setActiveCharacterId(loadedActiveId);

                if (apiKey) {
                    console.log('[App] Initializing LLM Service with loaded settings');
                    // llmService.init(apiKey, baseUrl, model); -> Handled in Main Process on settings:set

                    // ⚡ 重要：首先通知后端切换到当前活跃的角色
                    console.log(`[App] Syncing backend to active character: ${loadedActiveId}`);
                    try {
                        const switchRes = await fetch('http://localhost:8001/soul/switch_character', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ character_id: loadedActiveId })
                        });
                        
                        if (switchRes.ok) {
                            const switchData = await switchRes.json();
                            console.log(`[App] ✅ Backend initialized to: ${switchData.character_name}`);
                        } else {
                            console.error('[App] Failed to sync backend character on startup');
                        }
                    } catch (error) {
                        console.error('[App] Error syncing backend character:', error);
                    }

                    // Initialize Memory Service
                    console.log('[App] Initializing Memory Service');
                    memoryService.setCharacter(loadedActiveId); // ⚡ Sync Memory Service State
                    memoryService.configure(apiKey, baseUrl, model);

                    // Apply Active Character
                    const activeChar = loadedCharacters.find(c => c.id === loadedActiveId) || loadedCharacters[0];
                    applyCharacter(activeChar, loadedUserName);
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
                fetch('http://localhost:8001/dream/wake_up', { method: 'POST' })
                    .catch(e => console.warn("[App] Startup Dreaming failed:", e));
            }, 5000); // Wait 5s for backend to be fully ready
        }
    }, []);
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
                    fetch('http://localhost:8001/dream/wake_up', { method: 'POST' })
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



    // ⚡ Proactive Chat Polling
    const isProactiveProcessing = useRef(false);

    useEffect(() => {
        if (!activeCharacterId) return;

        const syncState = async () => {
            if (isProactiveProcessing.current) return;
            
            // Only check if we are NOT currently processing a message/talking
            if (!isProcessing && !isStreaming) {
                try {
                    const res = await fetch(`http://localhost:8001/galgame/${activeCharacterId}/state`);
                    if (res.ok) {
                        const stateData = await res.json();
                        
                        // ⚡ Sync Prompts from Character-Specific Endpoint (More Reliable)
                        if (stateData.dynamic_instruction) {
                            dynamicInstructionRef.current = stateData.dynamic_instruction;
                        }
                        if (stateData.system_prompt) {
                            currentSystemPromptRef.current = stateData.system_prompt;
                             (window as any).llm.setSystemPrompt(stateData.system_prompt);
                        }

                        // Check for 'pending_interaction'
                        if (stateData.pending_interaction) {
                            console.log('[App] ⚡ Proactive Trigger Detected from Backend!', stateData.pending_interaction);
                            
                            // 1. 先上锁，防止下一次轮询进入
                            isProactiveProcessing.current = true;
                            
                            // 2. 只有在成功清除后台标记后，才让 AI 说话
                            try {
                                await fetch(`http://localhost:8001/soul/mutate?clear_pending=true`, { method: 'POST' });
                            } catch (clearErr) {
                                console.error('[App] Failed to clear pending state, aborting interaction to avoid loop.');
                                isProactiveProcessing.current = false;
                                return;
                            }
                            
                            // ⚡ 获取关系信息
                            const relationship = stateData.relationship || {};
                            const level = relationship.level || 0;
                            const currentStageLabel = relationship.current_stage_label || 'Stranger';
                            const charName = characters.find(c => c.id === activeCharacterId)?.name || 'AI';
                            
                            // ⚡ Build Rich Prompt with History + Inspiration
                            // 1. Get recent conversation history
                            const recentHistory = conversationHistory
                                .filter(m => !m.content.trim().startsWith('(Private System Instruction')) // 🛡️ Prevent recursion!
                                .slice(-5)
                                .map(m => `${m.role === 'user' ? userName : charName}: ${m.content.substring(0, 100)}...`)
                                .join('\n');
                            
                            // 2. Fetch random inspiration from memories (SurrealDB)
                            let inspirationText = '';
                            try {
                                const inspirationRes = await fetch(`http://localhost:8001/memory/inspiration?character_id=${activeCharacterId}&limit=3`);
                                if (inspirationRes.ok) {
                                    const inspirations = await inspirationRes.json();
                                    if (inspirations.length > 0) {
                                        // ⚡ Support both SQLite (content) and SurrealDB (context) formats
                                        inspirationText = inspirations.map((i: any) => {
                                            if (i.context) return `- ${i.context}`; // SurrealDB
                                            if (i.content) return `- ${i.content}`; // SQLite
                                            // Fallback for edge format: Subject VERB Object
                                            if (i.subject && i.relation && i.object) return `- ${i.subject} ${i.relation} ${i.object}`;
                                            return '';
                                        }).filter((s: string) => s !== '').join('\n');
                                        
                                        console.log(`[App] 🎲 Loaded ${inspirations.length} inspirations for proactive chat`);
                                    }
                                }
                            } catch (e) {
                                console.warn('[App] Failed to fetch inspiration, proceeding without');
                            }
                            
                            // 3. Build enhanced instruction with time and relationship info
                            const nowStr = new Date().toLocaleString();
                            const dynamicInstruction = dynamicInstructionRef.current || '';
                            
                            const instruction = `(Private System Instruction - DO NOT EXPOSE THIS TO USER)
[SYSTEM NOTICE]
Current Time: ${nowStr}
Relationship: Lv.${level} (${currentStageLabel})
Task: Continue a conversation naturally.

${dynamicInstruction}

${inspirationText ? `## Related Topics (Memory)\n${inspirationText}\n` : ''}
GUIDELINES:
- Use the [Related Topics] as a topic starter IF they seem interesting, or just continue the conversation.
- Keep it natural, casual, and brief.
- Context: You are ${charName}. Don't mention you are an AI.
- Based on your personality and the silence, initiate a brand new natural conversation topic. Do NOT repeat previous greetings.`;
                            
                            // Use Ref to call handleSend
                            handleSendRef.current(instruction);
                            
                            // 释放锁（在 handleSend 完成后）
                            isProactiveProcessing.current = false;
                        }
                    }
                } catch (e) {
                    // silent fail for network issues
                    isProactiveProcessing.current = false;
                }
            }
        };

        // ⚡ Run immediately on mount/change
        syncState();

        const interval = setInterval(syncState, 5000); // Check every 5 seconds
        return () => clearInterval(interval);
    }, [activeCharacterId, isProcessing, isStreaming, characters, conversationHistory, userName]); // Dependencies updater on Interaction
    const resetIdleTimer = () => {
        lastActivityTime.current = Date.now();
        if (isDreamingRef.current) {
            console.log('[Dreaming] Activity detected. Waking up from dreaming state.');
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
        console.log(`[App] Old: ${prevApiKeyRef.current?.substring(0,8)}... | New: ${apiKey?.substring(0,8)}...`);
        
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

    const handleLive2DHighDpiChange = (enabled: boolean) => {
        console.log(`[App] Live2D High DPI changed to: ${enabled}`);
        setLive2dHighDpi(enabled);
    };

    const handleSend = async (text: string) => {
        resetIdleTimer();
        setIsProcessing(true);
        setIsStreaming(true);
        setCurrentMessage(''); // 清空旧消息
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
            
            const onToken = (token: string) => {
                // Accumulate in Ref
                fullRawResponseRef.current += token;
                emotionBufferRef.current += token;

                // 1. Check for complete (emotion) tags or [emotion] tags to trigger Live2D
                if (token.includes(')') || token.includes(']') || token.includes('）')) {
                    console.log('[App] Emotion tag delimiter detected, buffer:', emotionBufferRef.current);
                    processEmotions(emotionBufferRef.current);
                    emotionBufferRef.current = ''; // Reset buffer
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
                console.log('[App] Stream ended');
                // 流结束后的处理
                setIsStreaming(false);
                setIsProcessing(false);

                // 刷新句子分割器
                if (isTTSEnabled && sentenceSplitterRef.current) {
                    sentenceSplitterRef.current.flush();
                }

                // 添加助手回复到历史 (Cleaned)
                const finalCleanContent = fullRawResponseRef.current
                    .replace(/\([^)]*\)/g, '')  // 移除情感标签
                    .replace(/&/g, '')          // 移除 TTS 断句符
                    .trim();
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
                    const res = await fetch(`http://localhost:8001/galgame/${activeCharacterId}/state`);
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
                dynamicState        // ✅ Pass Dynamic Instruction Separately (No Header Wrapper)
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
                 const res = await fetch('http://localhost:8001/soul');
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
            width: '100vw', 
            height: '100vh', 
            backgroundImage: 'url(/bg.png)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            position: 'relative', 
            overflow: 'hidden' 
        }}>

            {/* Live2D Layer */}
            {/* Live2D Layer - Block until settings loaded to prevent Hiyori Flash */}
            {isSettingsLoaded ? (() => {
                const activeChar = characters.find(c => c.id === activeCharacterId) || characters[0];
                const modelPath = activeChar?.modelPath || "/live2d/Hiyori/Hiyori.model3.json";
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
                />
            )}

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

                {/* Motion Tester Button */}
                <button
                    onClick={() => setIsMotionTesterOpen(true)}
                    style={{
                        padding: '12px 20px',
                        fontSize: '16px',
                        backgroundColor: '#9C27B0',
                        color: 'white',
                        border: 'none',
                        borderRadius: '25px',
                        cursor: 'pointer',
                        boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
                        transition: 'all 0.3s ease'
                    }}
                >
                    🎭 测试动作
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

            {/* SurrealDB Viewer */}
            <SurrealViewer
                isOpen={isSurrealViewerOpen}
                onClose={() => setIsSurrealViewerOpen(false)}
            />
        </div>
    );

}

export default App;
