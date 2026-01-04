export class AudioQueue {
    private queue: ReadableStream<Uint8Array>[] = [];
    private isPlaying: boolean = false;
    private currentAudio: HTMLAudioElement | null = null;
    private mediaSource: MediaSource | null = null;

    /**
     * 添加音频流到队列
     */
    enqueue(stream: ReadableStream<Uint8Array>) {
        this.queue.push(stream);
        console.log(`[AudioQueue] Enqueued stream, queue length: ${this.queue.length}`);

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
            console.log('[AudioQueue] Queue empty, playback finished');
            return;
        }

        this.isPlaying = true;
        const stream = this.queue.shift()!;

        try {
            await this.playStream(stream);
        } catch (error) {
            console.error('[AudioQueue] Playback error:', error);
        }

        // 递归播放下一个
        this.playNext();
    }

    /**
     * 使用 MediaSource 播放流
     */
    private playStream(stream: ReadableStream<Uint8Array>): Promise<void> {
        return new Promise((resolve, reject) => {
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
                console.log('[AudioQueue] Stream playback finished');
                cleanup();
                resolve();
            };

            audio.onerror = (e) => {
                console.error('[AudioQueue] Audio error:', e);
                cleanup();
                reject(e);
            };

            mediaSource.addEventListener('sourceopen', async () => {
                console.log('[AudioQueue] MediaSource opened');
                try {
                    // Create SourceBuffer for MP3
                    // Note: 'audio/mpeg' support varies, but is standard in modern browsers.
                    // If fails, might need 'audio/mp3' or codec check.
                    if (!MediaSource.isTypeSupported('audio/mpeg')) {
                        throw new Error('Browser does not support audio/mpeg MediaSource');
                    }

                    const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
                    const reader = stream.getReader();
                    const queue: Uint8Array[] = [];
                    let isUpdating = false;

                    // Function to process the buffer queue with SourceBuffer
                    const processQueue = () => {
                        if (queue.length > 0 && !sourceBuffer.updating) {
                            try {
                                const chunk = queue.shift()!;
                                console.log(`[AudioQueue] Appending buffer of size: ${chunk.byteLength}`);
                                sourceBuffer.appendBuffer(chunk as BufferSource);
                            } catch (e) {
                                console.error('[AudioQueue] SourceBuffer append error:', e);
                            }
                        }
                    };

                    sourceBuffer.addEventListener('updateend', () => {
                        processQueue();
                        if (queue.length === 0 && isUpdating === false && mediaSource.readyState === 'open') {
                            try {
                                console.log('[AudioQueue] End of stream signaled');
                                mediaSource.endOfStream();
                            } catch (e) {
                                // Sometimes endOfStream fails if called too early or late, usually safe to ignore if playback is fine
                                // console.warn('[AudioQueue] endOfStream warning', e);
                            }
                        }
                    });

                    // Start playing as soon as we have data?
                    // Audio usually waits for enough buffer.
                    audio.play().catch(e => console.warn('[AudioQueue] Auto-play failed:', e));

                    // Pump the stream
                    while (true) {
                        isUpdating = true;
                        const { done, value } = await reader.read();
                        if (done) {
                            console.log('[AudioQueue] Stream reader done');
                            isUpdating = false;
                            // If buffer is not updating, we can end. 
                            // If it IS updating, 'updateend' will trigger endOfStream logic.
                            if (!sourceBuffer.updating && mediaSource.readyState === 'open') {
                                mediaSource.endOfStream();
                            }
                            break;
                        }

                        if (value) {
                            console.log(`[AudioQueue] Received chunk of size: ${value.byteLength}`);
                            queue.push(value);
                            processQueue();
                        }
                    }

                } catch (err) {
                    console.error('[AudioQueue] Stream processing error:', err);
                    // Ensure we reject to move to next item
                    // But if audio is playing, maybe wait? 
                    // Usually err here means streaming failed.
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
        console.log('[AudioQueue] Clearing queue');
        this.queue = [];

        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }

        // Also cleanup MediaSource if active
        if (this.mediaSource && this.mediaSource.readyState === 'open') {
            try {
                // this.mediaSource.endOfStream(); // Not needed if pausing audio
            } catch (e) { }
        }
        this.mediaSource = null;

        this.isPlaying = false;
    }

    /**
     * 获取队列长度
     */
    get length(): number {
        return this.queue.length;
    }
}
