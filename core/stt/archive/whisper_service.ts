import path from 'path';
import { nodewhisper } from 'nodejs-whisper';

/**
 * WhisperService - 本地语音识别服务
 * 基于 whisper.cpp，支持流式音频转录
 */
export class WhisperService {
    private modelPath: string = '';
    private isInitialized: boolean = false;
    private modelName: string = 'base'; // default: whisper-base

    constructor(modelName: string = 'base') {
        this.modelName = modelName;
    }

    /**
     * 初始化 Whisper 服务，下载模型（如果需要）
     */
    public async initialize(): Promise<void> {
        if (this.isInitialized) {
            return;
        }

        console.log(`[WhisperService] Initializing with model: ${this.modelName}`);

        // nodejs-whisper 会自动下载模型到 ~/.whisper-node/
        // 第一次运行时可能需要几分钟下载
        this.isInitialized = true;
        console.log(`[WhisperService] Initialization complete`);
    }

    /**
     * 转录音频文件
     * @param audioPath - 音频文件路径 (WAV, 16kHz, mono)
     * @returns 转录文本
     */
    public async transcribe(audioPath: string): Promise<string> {
        if (!this.isInitialized) {
            await this.initialize();
        }

        try {
            console.log(`[WhisperService] Transcribing: ${audioPath}`);

            const result = await nodewhisper(audioPath, {
                modelName: this.modelName,
                autoDownloadModelName: this.modelName, // 自动下载模型
                whisperOptions: {
                    language: 'zh',  // 中文优先
                    wordTimestamps: false,
                }
            });

            // nodejs-whisper 返回的是数组，取第一个结果
            const transcript = Array.isArray(result) ? result[0] : result;
            console.log(`[WhisperService] Result: ${transcript}`);

            return transcript || '';
        } catch (error) {
            console.error('[WhisperService] Transcription error:', error);
            throw error;
        }
    }

    /**
     * 设置模型
     * @param modelName - 模型名称: 'tiny', 'base', 'small', 'medium', 'large'
     */
    public setModel(modelName: string) {
        this.modelName = modelName;
        this.isInitialized = false; // 需要重新初始化
    }

    /**
     * 获取当前模型信息
     */
    public getModelInfo() {
        return {
            name: this.modelName,
            initialized: this.isInitialized,
        };
    }
}

// 导出单例
export const whisperService = new WhisperService('base');
