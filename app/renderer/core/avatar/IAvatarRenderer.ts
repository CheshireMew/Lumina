export interface IAvatarRenderer {
  /**
   * Initialize the renderer within the container
   */
  initialize(container: HTMLElement): Promise<void>;

  /**
   * Cleanup resources
   */
  destroy(): void;

  /**
   * Speak audio with optional visual phonemes (visemes)
   */
  speak(audioUrl: string, visemes?: number[]): Promise<void>;

  /**
   * Set emotional state
   * @param emotion e.g. "happy", "sad", "angry"
   * @param intensity 0.0 to 1.0
   */
  setExpression(emotion: string, intensity?: number): void;

  /**
   * Make avatar look at specific coordinates (0..1)
   */
  lookAt(x: number, y: number): void;

  /**
   * Get the rendering canvas
   */
  getCanvas(): HTMLCanvasElement | null;
}
