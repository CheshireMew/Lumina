import { promises as fs } from 'fs';
import path from 'path';
import { app } from 'electron';

/**
 * AudioStreamBuffer - 音频流缓冲器
 * 用于累积音频数据并将其保存为 WAV 文件供 Whisper 转录
 */
export class AudioStreamBuffer {
    private buffer: Buffer[] = [];
    private sampleRate: number;
    private channels: number;
    private readonly tempDir: string;

    constructor(sampleRate: number = 16000, channels: number = 1) {
        this.sampleRate = sampleRate;
        this.channels = channels;
        this.tempDir = path.join(app.getPath('userData'), 'audio_temp');
    }

    /**
     * 初始化临时目录
     */
    public async initialize() {
        try {
            await fs.mkdir(this.tempDir, { recursive: true });
        } catch (error) {
            console.error('[AudioStreamBuffer] Failed to create temp dir:', error);
        }
    }

    /**
     * 添加音频数据块
     * @param chunk - PCM 音频数据 (Float32Array)
     */
    public appendChunk(chunk: Float32Array) {
        // 将 Float32Array 转换为 Int16 PCM
        const int16Buffer = this.float32ToInt16(chunk);
        this.buffer.push(int16Buffer);
    }

    /**
     * 获取当前缓冲区长度（秒）
     */
    public getDuration(): number {
        const totalSamples = this.buffer.reduce((sum, buf) => sum + buf.length / 2, 0);
        return totalSamples / this.sampleRate;
    }

    /**
     * 清空缓冲区
     */
    public clear() {
        this.buffer = [];
    }

    /**
     * 将缓冲区数据保存为 WAV 文件
     * @returns WAV 文件路径
     */
    public async saveAsWav(): Promise<string> {
        const filename = `audio_${Date.now()}.wav`;
        const filepath = path.join(this.tempDir, filename);

        // 合并所有 buffer
        const pcmData = Buffer.concat(this.buffer);

        // 构建 WAV 文件头
        const wavHeader = this.createWavHeader(pcmData.length);
        const wavFile = Buffer.concat([wavHeader, pcmData]);

        await fs.writeFile(filepath, wavFile);
        console.log(`[AudioStreamBuffer] Saved WAV: ${filepath} (${this.getDuration().toFixed(2)}s)`);

        return filepath;
    }

    /**
     * Float32Array 转 Int16 PCM
     */
    private float32ToInt16(float32Array: Float32Array): Buffer {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return Buffer.from(int16Array.buffer);
    }

    /**
     * 创建 WAV 文件头
     */
    private createWavHeader(dataLength: number): Buffer {
        const header = Buffer.alloc(44);

        // "RIFF" chunk descriptor
        header.write('RIFF', 0);
        header.writeUInt32LE(36 + dataLength, 4);
        header.write('WAVE', 8);

        // "fmt " sub-chunk
        header.write('fmt ', 12);
        header.writeUInt32LE(16, 16); // Subchunk1Size (16 for PCM)
        header.writeUInt16LE(1, 20);  // AudioFormat (1 for PCM)
        header.writeUInt16LE(this.channels, 22);
        header.writeUInt32LE(this.sampleRate, 24);
        header.writeUInt32LE(this.sampleRate * this.channels * 2, 28); // ByteRate
        header.writeUInt16LE(this.channels * 2, 32); // BlockAlign
        header.writeUInt16LE(16, 34); // BitsPerSample

        // "data" sub-chunk
        header.write('data', 36);
        header.writeUInt32LE(dataLength, 40);

        return header;
    }

    /**
     * 清理临时文件
     */
    public async cleanup(filepath: string) {
        try {
            await fs.unlink(filepath);
            console.log(`[AudioStreamBuffer] Cleaned up: ${filepath}`);
        } catch (error) {
            console.error('[AudioStreamBuffer] Cleanup error:', error);
        }
    }
}
