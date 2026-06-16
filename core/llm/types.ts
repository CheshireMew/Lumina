/**
 * LLM 相关类型定义
 */

export interface Message {
  role: "system" | "user" | "assistant";
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
  displayName?: string;
  description: string;
  systemPrompt?: string; // Full system prompt instructions
  avatar?: string;
  voiceConfig: {
    service: string; // 'edge-tts' | 'azure' | ...
    voiceId: string; // e.g., "zh-CN-XiaoxiaoNeural"
    rate?: string; // "+0%"
    pitch?: string; // "+0Hz"
  };
  modelPath?: string; // Path to Live2D model (relative to public)
  heartbeatEnabled?: boolean; // ⚡ Heartbeat Toggle
  // ⚡ Interaction Settings
  soulEvolutionEnabled?: boolean; // ⚡ New: Decoupled Logic Toggle
  proactiveChatEnabled?: boolean; // ⚡ Master Proactive Switch
  proactiveThresholdMinutes?: number; // ⚡ Silence threshold
  metadata?: Record<string, unknown>;
}

