import { MutableRefObject } from "react";

export interface FaceTrackingData {
  headPan: number;
  headTilt: number;
  headRoll: number;
  eyeBlinkLeft: number;
  eyeBlinkRight: number;
  jawOpen: number;
  mouthSmile: number;
}

/**
 * Standard Interface for ALL Avatar Renderers.
 * (Live2D, VRM, Static Image, etc.)
 */
export interface IAvatarRenderer {
  /**
   * Start "Speaking" animation (Lip-sync).
   * @param audioUrl URL of the audio playing (for analysis) or just trigger.
   */
  speak?(audioUrl: string): Promise<void>;

  /**
   * Set a specific emotion or expression.
   * @param emotionId  Standardized ID: 'joy', 'sad', 'angry', 'neutral'
   */
  setEmotion(emotionId: string): void;

  /**
   * Trigger a full body motion.
   * @param group Motion group name
   * @param index Motion index
   */
  motion?(group: string, index?: number): void;

  /**
   * Stop all current expressions/motions immediately.
   */
  stopExpression(): void;

  /**
   * Make avatar look at specific coordinates (0..1)
   */
  lookAt?(x: number, y: number): void;

  /**
   * Get the underlying canvas element
   */
  getCanvas?(): HTMLCanvasElement | null;

  /**
   * Apply face tracking BlendShapes (VTuber Mode).
   * @param data Face tracking data from MediaPipe
   */
  setBlendShapes?(data: FaceTrackingData): void;
}

export type AvatarRendererRef = IAvatarRenderer;
