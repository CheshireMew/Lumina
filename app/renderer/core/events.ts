import EventEmitter from "eventemitter3";
import { FaceTrackingData } from "./avatar/types";

// 1. Define Event Map
// Explicitly format payloads. Use 'undefined' for no payload.
export type AppEvents = {
  // --- Audio Layer ---
  "audio:vad.start": undefined; // User started speaking -> Interrupt trigger
  "audio:vad.end": undefined; // User stopped speaking
  "audio:transcription": string; // STT Final Text

  // --- Vision Layer ---
  "vision:analyzed": string; // Image description ready

  // --- Avatar Layer ---
  "avatar:face_tracking": FaceTrackingData;

  // --- Control Layer ---
  "core:interrupt": undefined; // Global Interrupt Signal
};

// 2. Typed Wrapper
class TypedEventBus {
  private emitter = new EventEmitter();

  /**
   * Subscribe to an event
   * @returns Unsubscribe function for convenience
   */
  on<K extends keyof AppEvents>(
    event: K,
    listener: (payload: AppEvents[K]) => void
  ): () => void {
    this.emitter.on(event, listener);
    return () => this.emitter.off(event, listener);
  }

  off<K extends keyof AppEvents>(
    event: K,
    listener: (payload: AppEvents[K]) => void
  ) {
    this.emitter.off(event, listener);
  }

  emit<K extends keyof AppEvents>(event: K, payload: AppEvents[K]) {
    this.emitter.emit(event, payload);
  }

  once<K extends keyof AppEvents>(
    event: K,
    listener: (payload: AppEvents[K]) => void
  ) {
    this.emitter.once(event, listener);
  }
}

// 3. Singleton Export
export const events = new TypedEventBus();
