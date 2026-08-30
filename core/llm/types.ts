/**
 * LLM 相关类型定义
 */

export interface ChatAttachment {
  id: string;
  type: "image";
  name: string;
  previewUrl: string;
  description: string;
}

export interface ChatSendRequest {
  displayText: string;
  requestText: string;
  attachments?: ChatAttachment[];
}

export interface Message {
  id: string;
  turnId?: string;
  role: "system" | "user" | "assistant";
  content: string;
  timestamp: number;
  reasoning?: string;
  status?: "pending" | "streaming" | "completed" | "interrupted" | "failed";
  requestContent?: string;
  attachments?: ChatAttachment[];
  errorCode?: string;
  errorMessage?: string;
}

export interface Live2DBehavior {
  idleMotionGroup: string;
  tapMotionGroup: string;
  tapHitArea: string;
  idleThresholdMs: number;
  fitScale: number;
  verticalPositionRatio: number;
  timeScale: number;
  parameters: {
    eyeBlinkLeft: string;
    eyeBlinkRight: string;
    mouthOpen: string;
    headPan: string;
    headTilt: string;
    headRoll: string;
    bodyPan: string;
  };
}

export interface CharacterProfile {
  id: string;
  name: string;
  displayName?: string;
  description: string;
  systemPrompt?: string; // Full system prompt instructions
  avatar: {
    type: "live2d";
    model: string;
    modelUrl: string;
    cubismCoreUrl: string;
    rendererRuntimeUrl: string;
    behavior: Live2DBehavior;
  };
  voiceConfig: {
    service: string; // 'edge-tts' | 'azure' | ...
    voiceId: string;
    rate: string;
    pitch: string;
  };
  heartbeatEnabled?: boolean; // ⚡ Heartbeat Toggle
  // ⚡ Interaction Settings
  soulEvolutionEnabled?: boolean; // ⚡ New: Decoupled Logic Toggle
  proactiveChatEnabled?: boolean;
  proactiveThresholdMinutes?: number; // ⚡ Silence threshold
  metadata?: Record<string, unknown>;
}

