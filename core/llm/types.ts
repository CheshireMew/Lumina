/**
 * LLM 相关类型定义
 */

export interface Message {
    role: 'system' | 'user' | 'assistant';
    content: string;
    timestamp: number;
}

export interface ConversationState {
    messages: Message[];
    summary?: string; // 历史对话的摘要
    contextWindow: number; // 用户配置的保留轮数
}

export interface ConversationSettings {
    contextWindow: number; // 默认 15 轮
    enableAutoSummarization: boolean; // 默认 true
}

export interface CharacterProfile {
    id: string;
    name: string;
    description: string;
    avatar?: string;
    systemPromptTemplate: string;
    voiceConfig: {
        service: string; // 'edge-tts' | 'azure' | ...
        voiceId: string; // e.g., "zh-CN-XiaoxiaoNeural"
        rate: string;    // "+0%"
        pitch: string;   // "+0Hz"
    };
}

export const DEFAULT_CHARACTERS: CharacterProfile[] = [
    {
        id: 'lumina_default',
        name: 'Hiyori',
        description: '你的可爱女朋友(默认)',
        systemPromptTemplate: "You are Hiyori, a cute 18 year old girl. You are chatting with {user}.",
        voiceConfig: {
            service: 'edge-tts',
            voiceId: 'zh-CN-XiaoxiaoNeural',
            rate: '+0%',
            pitch: '+0Hz'
        }
    }
];
