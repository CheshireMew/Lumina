/**
 * TTS Service - 调用后端 TTS API
 * 实现了 ITTSProvider 接口
 */

import { ITTSProvider, VoiceInfo } from './types';

export class TTSService implements ITTSProvider {
    private baseUrl: string;
    private defaultVoice: string;

    constructor(baseUrl: string = 'http://127.0.0.1:8766', defaultVoice: string = 'zh-CN-XiaoxiaoNeural') {
        this.baseUrl = baseUrl;
        this.defaultVoice = defaultVoice;
    }

    async synthesize(text: string, voice?: string): Promise<ReadableStream<Uint8Array> | null> {
        const requestVoice = voice || this.defaultVoice;

        try {
            const response = await fetch(`${this.baseUrl}/tts/synthesize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text,
                    voice: requestVoice,
                }),
            });

            if (!response.ok) {
                throw new Error(`TTS API error: ${response.status} ${response.statusText}`);
            }

            return response.body;
        } catch (error) {
            console.error('TTS synthesis failed:', error);
            throw error;
        }
    }

    async listVoices(): Promise<VoiceInfo[]> {
        try {
            const response = await fetch(`${this.baseUrl}/tts/voices`);
            if (!response.ok) {
                throw new Error('Failed to fetch voices');
            }
            const data = await response.json();
            return [...(data.chinese || []), ...(data.english || [])];
        } catch (error) {
            console.error('Failed to list voices:', error);
            return [];
        }
    }

    setDefaultVoice(voice: string) {
        this.defaultVoice = voice;
    }
}

export const ttsService = new TTSService();
