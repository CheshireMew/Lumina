/**
 * TTS Service - 调用后端 TTS API
 * 实现了 ITTSProvider 接口
 */

import { ITTSProvider, VoiceInfo } from "./types";

export class TTSService implements ITTSProvider {
  private baseUrl: string;
  private defaultVoice: string;
  private defaultEngine: string;
  private defaultRate: string;
  private defaultPitch: string;
  private readonly maxConcurrentRequests: number;
  private activeRequestCount = 0;
  private generation = 0;
  private waiters: Array<{
    generation: number;
    resolve: (acquired: boolean) => void;
  }> = [];

  constructor(
    baseUrl: string = "",
    defaultVoice: string = "",
    maxConcurrentRequests: number = 2,
  ) {
    this.baseUrl = baseUrl;
    this.defaultVoice = defaultVoice;
    this.defaultEngine = "";
    this.defaultRate = "";
    this.defaultPitch = "";
    this.maxConcurrentRequests = Math.max(1, maxConcurrentRequests);
  }

  private activeControllers = new Set<AbortController>();

  stop() {
    console.log("[TTSService] Stopping all active requests...");
    this.activeControllers.forEach((c) => c.abort());
    this.activeControllers.clear();
    this.generation++;
    const waiters = this.waiters;
    this.waiters = [];
    waiters.forEach(({ resolve }) => resolve(false));
  }

  private acquireSlot(generation: number): Promise<boolean> {
    if (generation !== this.generation) return Promise.resolve(false);
    if (this.activeRequestCount < this.maxConcurrentRequests) {
      this.activeRequestCount++;
      return Promise.resolve(true);
    }
    return new Promise((resolve) => this.waiters.push({ generation, resolve }));
  }

  private releaseSlot() {
    this.activeRequestCount = Math.max(0, this.activeRequestCount - 1);
    while (this.waiters.length > 0) {
      const waiter = this.waiters.shift()!;
      if (waiter.generation !== this.generation) {
        waiter.resolve(false);
        continue;
      }
      this.activeRequestCount++;
      waiter.resolve(true);
      break;
    }
  }

  async synthesize(
    text: string,
    voice?: string,
    engine?: string
  ): Promise<import("./types").AudioResponse | null> {
    const requestVoice = voice || this.defaultVoice;
    const requestEngine = engine || this.defaultEngine;
    const requestGeneration = this.generation;
    const acquired = await this.acquireSlot(requestGeneration);
    if (!acquired) return null;

    const controller = new AbortController();
    this.activeControllers.add(controller);
    let timedOut = false;
    const timeoutId = globalThis.setTimeout(() => {
      timedOut = true;
      controller.abort(new DOMException("TTS request timed out", "TimeoutError"));
    }, 60_000);

    try {
      if (!this.baseUrl) {
        throw new Error("TTS base URL has not been initialized.");
      }

      console.log(
        `[TTS] Request: text="${text.substring(
          0,
          10
        )}...", voice=${requestVoice}, engine=${requestEngine}`
      );

      const response = await fetch(`${this.baseUrl}/synthesize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          ...(requestVoice ? { voice: requestVoice } : {}),
          ...(requestEngine ? { engine: requestEngine } : {}),
          ...(this.defaultRate ? { rate: this.defaultRate } : {}),
          ...(this.defaultPitch ? { pitch: this.defaultPitch } : {}),
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
      if (timedOut) {
        throw new Error("TTS request timed out after 60 seconds.");
      }
      if (error instanceof Error && error.name === "AbortError") {
        console.log("[TTS] Request aborted.");
        return null;
      }
      console.error("TTS synthesis failed:", error);
      throw error;
    } finally {
      globalThis.clearTimeout(timeoutId);
      this.activeControllers.delete(controller);
      this.releaseSlot();
    }
  }

  async listVoices(engine: string = this.defaultEngine): Promise<VoiceInfo[]> {
    try {
      if (!this.baseUrl) {
        throw new Error("TTS base URL has not been initialized.");
      }

      const query = engine ? `?engine=${encodeURIComponent(engine)}` : "";
      const response = await fetch(`${this.baseUrl}/voices${query}`);
      if (!response.ok) {
        throw new Error("Failed to fetch voices");
      }
      const data = await response.json();
      if (Array.isArray(data)) {
        return data;
      }
      if (Array.isArray(data.voices)) {
        return data.voices;
      }
      return [...(data.chinese || []), ...(data.english || [])];
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

  setProsody(rate: string, pitch: string) {
    this.defaultRate = rate;
    this.defaultPitch = pitch;
  }

  setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/$/, "");
  }
}

export const ttsService = new TTSService();
