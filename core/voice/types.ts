/**
 * TTS Provider Interface
 * 抽象接口，方便后续切换 TTS 引擎
 */

export interface ITTSProvider {
    /**
     * 合成语音
     * @param text 要合成的文本
     * @param voice 音色ID（可选）
     * @returns 音频数据 (ArrayBuffer)
     */
    synthesize(text: string, voice?: string): Promise<ReadableStream<Uint8Array> | null>;

    /**
     * 获取可用音色列表
     */
    listVoices?(): Promise<VoiceInfo[]>;
}

export interface VoiceInfo {
    name: string;
    gender: 'Male' | 'Female';
    locale?: string;
}

export interface TTSConfig {
    provider: 'edge' | 'cosyvoice' | 'elevenlabs'; // 可扩展
    voice: string;
    speed?: number;
    pitch?: number;
}
