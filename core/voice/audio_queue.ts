import { AudioResponse } from "./types";

interface QueueItem {
  stream: ReadableStream<Uint8Array>;
  contentType: string;
}

export class AudioQueue {
  private queue: QueueItem[] = [];
  private isPlaying: boolean = false;
  private currentAudio: HTMLAudioElement | null = null;
  private mediaSource: MediaSource | null = null;

  /**
   * 添加音频流到队列
   */
  enqueue(item: QueueItem) {
    this.queue.push(item);
    console.log(
      `[AudioQueue] Enqueued stream (${item.contentType}), queue length: ${this.queue.length}`
    );

    if (!this.isPlaying) {
      this.playNext();
    }
  }

  /**
   * 播放下一个流
   */
  private async playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      console.log("[AudioQueue] Queue empty, playback finished");
      return;
    }

    this.isPlaying = true;
    const item = this.queue.shift()!;

    try {
      await this.playStream(item);
    } catch (error) {
      console.error("[AudioQueue] Playback error:", error);
    }

    // 递归播放下一个
    this.playNext();
  }

  /**
   * 播放流 (WAV uses Blob, others use MSE)
   */
  private playStream(item: QueueItem): Promise<void> {
    const { stream, contentType } = item;

    console.log(`[AudioQueue] playStream called for ${contentType}`, stream);

    if (!stream) {
      console.error("[AudioQueue] Stream is null");
      return Promise.reject(new Error("Stream is null"));
    }

    if (typeof stream.getReader !== "function") {
      console.error("[AudioQueue] stream.getReader is not a function!", stream);
      return Promise.reject(new Error("Stream does not have getReader method"));
    }

    // WAV does not support MSE, use Blob
    if (
      contentType.includes("wav") ||
      contentType.includes("x-wav") ||
      contentType.includes("audio/wav")
    ) {
      return this.playBlob(stream, contentType);
    }

    // Try MSE for supported types (MP3, OGG, etc)
    // ⚡ Fix: Force Blob for MP3 ('audio/mpeg') to avoid MSE frame alignment issues causing "choppy" audio
    if (
      MediaSource.isTypeSupported(contentType) &&
      !contentType.includes("audio/mpeg")
    ) {
      return this.playMSE(stream, contentType);
    }

    // Specific checks for common types if generic check fails (e.g. missing codecs param)
    // OGG often needs codecs="opus" or "vorbis" to be explicitly supported in some browsers
    if (
      contentType.includes("ogg") &&
      MediaSource.isTypeSupported('audio/ogg; codecs="opus"')
    ) {
      return this.playMSE(stream, 'audio/ogg; codecs="opus"');
    }

    console.warn(
      `[AudioQueue] MSE does not support ${contentType}, falling back to Blob.`
    );
    return this.playBlob(stream, contentType);
  }

  /**
   * 使用 Blob 播放 (非流式，需下载完)
   */
  private async playBlob(
    stream: ReadableStream<Uint8Array>,
    contentType: string
  ): Promise<void> {
    return new Promise(async (resolve, reject) => {
      console.log(`[AudioQueue] Playing via Blob (Type: ${contentType})`);
      const audio = new Audio();
      this.currentAudio = audio;

      const cleanup = () => {
        if (audio.src) URL.revokeObjectURL(audio.src);
        this.currentAudio = null;
      };

      audio.onended = () => {
        console.log("[AudioQueue] Blob playback finished");
        cleanup();
        resolve();
      };

      audio.onerror = (e) => {
        console.error("[AudioQueue] Audio error:", e);
        cleanup();
        reject(e);
      };

      try {
        // Read stream to array buffer
        const reader = stream.getReader();
        const chunks: any[] = [];
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (value) chunks.push(value);
        }

        const blob = new Blob(chunks, { type: contentType });
        audio.src = URL.createObjectURL(blob);
        await audio.play();
      } catch (err) {
        console.error("[AudioQueue] Blob processing failed:", err);
        cleanup();
        reject(err);
      }
    });
  }

  /**
   * 使用 MediaSource 播放流
   */
  private playMSE(
    stream: ReadableStream<Uint8Array>,
    contentType: string
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      // ⚡ 关键修复：创建新 MediaSource 前，清理旧的
      if (this.mediaSource) {
        try {
          if (this.mediaSource.readyState === "open") {
            this.mediaSource.endOfStream();
          }
        } catch (e) {
          console.warn("[AudioQueue] Failed to cleanup old MediaSource:", e);
        }
      }
      if (this.currentAudio) {
        this.currentAudio.pause();
        if (this.currentAudio.src) {
          URL.revokeObjectURL(this.currentAudio.src);
        }
      }

      const mediaSource = new MediaSource();
      const audio = new Audio();
      audio.src = URL.createObjectURL(mediaSource);
      this.currentAudio = audio;
      this.mediaSource = mediaSource;

      const cleanup = () => {
        if (audio.src) {
          URL.revokeObjectURL(audio.src);
        }
        this.currentAudio = null;
        this.mediaSource = null;
      };

      audio.onended = () => {
        console.log("[AudioQueue] Stream playback finished");
        cleanup();
        resolve();
      };

      audio.onerror = (e) => {
        console.error("[AudioQueue] Audio error:", e);
        cleanup();
        reject(e);
      };

      mediaSource.addEventListener("sourceopen", async () => {
        console.log(`[AudioQueue] MediaSource opened for ${contentType}`);
        try {
          if (!MediaSource.isTypeSupported(contentType)) {
            throw new Error(
              `Browser does not support ${contentType} MediaSource`
            );
          }

          const sourceBuffer = mediaSource.addSourceBuffer(contentType);
          const reader = stream.getReader();
          const queue: Uint8Array[] = [];
          let isUpdating = false;

          const processQueue = async () => {
            while (queue.length > 0 && !sourceBuffer.updating) {
              // 检查 sourceBuffer 是否仍然有效
              if (
                !mediaSource.sourceBuffers ||
                !mediaSource.sourceBuffers.length
              ) {
                console.warn(
                  "[AudioQueue] SourceBuffer removed, stopping queue processing"
                );
                return;
              }

              const chunk = queue.shift()!;
              try {
                sourceBuffer.appendBuffer(chunk as BufferSource);
              } catch (e) {
                console.error("[AudioQueue] SourceBuffer append error:", e);
                // 如果 append 失败，清空队列避免累积
                // Note: This clears the local `queue` for the current stream, not `this.queue`.
                queue.length = 0; // Clear the local queue
                return;
              }
            }
          };
          sourceBuffer.addEventListener("updateend", () => {
            processQueue();
            if (
              queue.length === 0 &&
              isUpdating === false &&
              mediaSource.readyState === "open"
            ) {
              try {
                mediaSource.endOfStream();
              } catch (e) {}
            }
          });

          audio
            .play()
            .catch((e) => console.warn("[AudioQueue] Auto-play failed:", e));

          while (true) {
            isUpdating = true;
            const { done, value } = await reader.read();
            if (done) {
              isUpdating = false;
              if (!sourceBuffer.updating && mediaSource.readyState === "open") {
                mediaSource.endOfStream();
              }
              break;
            }

            if (value) {
              queue.push(value);
              processQueue();
            }
          }
        } catch (err) {
          console.error("[AudioQueue] Stream processing error:", err);
          cleanup();
          reject(err);
        }
      });
    });
  }

  /**
   * 清空队列并停止当前播放
   */
  clear() {
    console.log("[AudioQueue] Clearing queue");
    this.queue = [];

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;

      // ⚡ 关键修复：撤销 ObjectURL
      if (this.currentAudio.src) {
        URL.revokeObjectURL(this.currentAudio.src);
      }
      this.currentAudio = null;
    }

    // ⚡ 关键修复：正确关闭 MediaSource 并移除 SourceBuffer
    if (this.mediaSource) {
      try {
        if (this.mediaSource.readyState === "open") {
          // 移除所有 SourceBuffer
          while (this.mediaSource.sourceBuffers.length > 0) {
            this.mediaSource.removeSourceBuffer(
              this.mediaSource.sourceBuffers[0]
            );
          }
          this.mediaSource.endOfStream();
        }
      } catch (e) {
        console.warn("[AudioQueue] Failed to cleanup MediaSource:", e);
      }
      this.mediaSource = null;
    }

    this.isPlaying = false;
  }

  /**
   * 获取队列长度
   */
  get length(): number {
    return this.queue.length;
  }
}
