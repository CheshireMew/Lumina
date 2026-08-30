export interface AudioStreamItem {
    stream: ReadableStream<Uint8Array>;
    contentType: string;
}

type MediaSourceSupport = Pick<typeof MediaSource, "isTypeSupported">;

export const canStreamAudioWithMediaSource = (
    contentType: string,
    mediaSource: MediaSourceSupport | undefined = globalThis.MediaSource,
): boolean => {
    if (!mediaSource || contentType.includes("wav")) return false;
    return (
        mediaSource.isTypeSupported(contentType) ||
        (contentType.includes("ogg") &&
            mediaSource.isTypeSupported('audio/ogg; codecs="opus"'))
    );
};

class AudioPlaybackResources {
    private audio: HTMLAudioElement | null = null;
    private mediaSource: MediaSource | null = null;
    private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

    begin(audio: HTMLAudioElement, mediaSource: MediaSource | null = null): void {
        this.clear();
        this.audio = audio;
        this.mediaSource = mediaSource;
    }

    isCurrent(audio: HTMLAudioElement, mediaSource?: MediaSource): boolean {
        return (
            this.audio === audio &&
            (mediaSource === undefined || this.mediaSource === mediaSource)
        );
    }

    trackReader(reader: ReadableStreamDefaultReader<Uint8Array>): void {
        this.reader = reader;
    }

    releaseReader(reader: ReadableStreamDefaultReader<Uint8Array>): void {
        if (this.reader === reader) this.reader = null;
        reader.releaseLock();
    }

    release(audio: HTMLAudioElement, mediaSource?: MediaSource): void {
        this.detachAudio(audio);
        if (this.audio === audio) this.audio = null;
        if (mediaSource && this.mediaSource === mediaSource) {
            this.closeMediaSource(mediaSource);
            this.mediaSource = null;
        }
    }

    clear(): void {
        const reader = this.reader;
        this.reader = null;
        if (reader) {
            void reader.cancel("Audio playback cleared").catch((error) => {
                console.warn("[AudioQueue] Failed to cancel stream reader:", error);
            });
        }

        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.detachAudio(this.audio);
            this.audio = null;
        }
        if (this.mediaSource) {
            this.closeMediaSource(this.mediaSource);
            this.mediaSource = null;
        }
    }

    private detachAudio(audio: HTMLAudioElement): void {
        if (!audio.src) return;
        const sourceUrl = audio.src;
        audio.removeAttribute("src");
        audio.load();
        window.setTimeout(() => URL.revokeObjectURL(sourceUrl), 1000);
    }

    private closeMediaSource(mediaSource: MediaSource): void {
        try {
            if (mediaSource.readyState !== "open") return;
            while (mediaSource.sourceBuffers.length > 0) {
                mediaSource.removeSourceBuffer(mediaSource.sourceBuffers[0]);
            }
            mediaSource.endOfStream();
        } catch (error) {
            console.warn("[AudioQueue] Failed to cleanup MediaSource:", error);
        }
    }
}

export class AudioStreamPlayer {
    private readonly resources = new AudioPlaybackResources();

    play({ stream, contentType }: AudioStreamItem): Promise<void> {
        if (!stream || typeof stream.getReader !== "function") {
            return Promise.reject(new Error("Audio stream is invalid"));
        }

        if (this.shouldUseMediaSource(contentType)) {
            return this.playMediaSource(stream, this.mediaSourceType(contentType));
        }
        return this.playBlob(stream, contentType);
    }

    clear(): void {
        this.resources.clear();
    }

    private shouldUseMediaSource(contentType: string): boolean {
        return canStreamAudioWithMediaSource(contentType);
    }

    private mediaSourceType(contentType: string): string {
        if (!MediaSource.isTypeSupported(contentType) && contentType.includes("ogg")) {
            return 'audio/ogg; codecs="opus"';
        }
        return contentType;
    }

    private playBlob(
        stream: ReadableStream<Uint8Array>,
        contentType: string,
    ): Promise<void> {
        return new Promise((resolve, reject) => {
            const audio = new Audio();
            this.resources.begin(audio);
            const finish = (callback: () => void) => {
                this.resources.release(audio);
                callback();
            };
            audio.onended = () => finish(resolve);
            audio.onerror = (error) => finish(() => reject(error));

            void (async () => {
                const reader = stream.getReader();
                this.resources.trackReader(reader);
                const chunks: BlobPart[] = [];
                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        if (value) chunks.push(value as BlobPart);
                    }
                } finally {
                    this.resources.releaseReader(reader);
                }
                if (!this.resources.isCurrent(audio)) {
                    resolve();
                    return;
                }
                audio.src = URL.createObjectURL(new Blob(chunks, { type: contentType }));
                await audio.play();
            })().catch((error) => finish(() => reject(error)));
        });
    }

    private playMediaSource(
        stream: ReadableStream<Uint8Array>,
        contentType: string,
    ): Promise<void> {
        return new Promise((resolve, reject) => {
            const mediaSource = new MediaSource();
            const audio = new Audio();
            audio.src = URL.createObjectURL(mediaSource);
            this.resources.begin(audio, mediaSource);
            const finish = (callback: () => void) => {
                this.resources.release(audio, mediaSource);
                callback();
            };
            audio.onended = () => finish(resolve);
            audio.onerror = (error) => finish(() => reject(error));

            mediaSource.addEventListener("sourceopen", () => {
                void this.feedMediaSource(
                    stream,
                    contentType,
                    audio,
                    mediaSource,
                ).catch((error) => finish(() => reject(error)));
            }, { once: true });
        });
    }

    private async feedMediaSource(
        stream: ReadableStream<Uint8Array>,
        contentType: string,
        audio: HTMLAudioElement,
        mediaSource: MediaSource,
    ): Promise<void> {
        if (!this.resources.isCurrent(audio, mediaSource)) return;
        if (!MediaSource.isTypeSupported(contentType)) {
            throw new Error(`Browser does not support ${contentType} MediaSource`);
        }

        const sourceBuffer = mediaSource.addSourceBuffer(contentType);
        const reader = stream.getReader();
        this.resources.trackReader(reader);
        const chunks: Uint8Array[] = [];
        let reading = true;
        const finishStreamWhenReady = () => {
            if (
                !reading &&
                chunks.length === 0 &&
                !sourceBuffer.updating &&
                mediaSource.readyState === "open"
            ) {
                mediaSource.endOfStream();
            }
        };
        const appendNext = () => {
            if (
                chunks.length === 0 ||
                sourceBuffer.updating ||
                mediaSource.sourceBuffers.length === 0
            ) {
                finishStreamWhenReady();
                return;
            }
            sourceBuffer.appendBuffer(chunks.shift()! as BufferSource);
        };
        sourceBuffer.addEventListener("updateend", appendNext);
        void audio.play().catch((error) => {
            console.warn("[AudioQueue] Auto-play failed:", error);
        });

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                if (value) {
                    chunks.push(value);
                    appendNext();
                }
            }
        } finally {
            reading = false;
            this.resources.releaseReader(reader);
            finishStreamWhenReady();
        }
    }
}
