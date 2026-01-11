/**
 * TTS Provider Interface
 * 抽象接口，方便后续切换 TTS 引擎
 */

export interface ITTSProvider {
  /**
   * 合成语音
   * @param text 要合成的文本
   * @param voice 音色ID（可选）
   * @returns 音频流及类型
   */
  synthesize(text: string, voice?: string): Promise<AudioResponse | null>;

  /**
   * 获取可用音色列表
   */
  listVoices?(): Promise<VoiceInfo[]>;

  /**
   * 停止所有正在进行的合成请求
   */
  stop(): void;
}

export interface AudioResponse {
  stream: ReadableStream<Uint8Array>;
  contentType: string;
}

export interface VoiceInfo {
  name: string;
  gender: "Male" | "Female";
  locale?: string;
}

export interface TTSConfig {
  provider: "edge" | "cosyvoice" | "elevenlabs"; // 可扩展
  voice: string;
  speed?: number;
  pitch?: number;
}
