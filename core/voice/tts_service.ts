/**
 * TTS Service - 调用后端 TTS API
 * 实现了 ITTSProvider 接口
 */

import { ITTSProvider, VoiceInfo } from "./types";

export class TTSService implements ITTSProvider {
  private baseUrl: string;
  private defaultVoice: string;
  private defaultEngine: string;

  constructor(
    baseUrl: string = "http://127.0.0.1:8766",
    defaultVoice: string = "zh-CN-XiaoxiaoNeural"
  ) {
    this.baseUrl = baseUrl;
    this.defaultVoice = defaultVoice;
    this.defaultEngine = "edge-tts";
  }

  private activeControllers = new Set<AbortController>();

  stop() {
    console.log("[TTSService] Stopping all active requests...");
    this.activeControllers.forEach((c) => c.abort());
    this.activeControllers.clear();
  }

  async synthesize(
    text: string,
    voice?: string,
    engine?: string
  ): Promise<import("./types").AudioResponse | null> {
    const requestVoice = voice || this.defaultVoice;
    const requestEngine = engine || this.defaultEngine;

    const controller = new AbortController();
    this.activeControllers.add(controller);

    try {
      console.log(
        `[TTS] Request: text="${text.substring(
          0,
          10
        )}...", voice=${requestVoice}, engine=${requestEngine}`
      );

      const response = await fetch(`${this.baseUrl}/tts/synthesize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          voice: requestVoice,
          engine: requestEngine,
          rate: "+0%", // Default rate
          pitch: "+0Hz", // Default pitch
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(
          `TTS API error: ${response.status} ${response.statusText}`
        );
      }

      const contentType = response.headers.get("content-type") || "audio/mpeg";
      console.log(
        `[TTS] Response: type=${contentType}, status=${response.status}`
      );

      if (!response.body) return null;

      return {
        stream: response.body,
        contentType,
      };
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        console.log("[TTS] Request aborted.");
        return null;
      }
      console.error("TTS synthesis failed:", error);
      throw error;
    } finally {
      this.activeControllers.delete(controller);
    }
  }

  async listVoices(engine: string = "edge-tts"): Promise<VoiceInfo[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/tts/voices?engine=${engine}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch voices");
      }
      const data = await response.json();

      if (engine === "gpt-sovits") {
        // GPT-SoVITS returns { voices: [...] }
        return data.voices || [];
      } else {
        // Edge TTS returns { chinese: [], english: [] }
        return [...(data.chinese || []), ...(data.english || [])];
      }
    } catch (error) {
      console.error("Failed to list voices:", error);
      return [];
    }
  }

  setDefaultVoice(voice: string) {
    this.defaultVoice = voice;
  }

  setEngine(engine: string) {
    this.defaultEngine = engine;
  }
}

export const ttsService = new TTSService();
