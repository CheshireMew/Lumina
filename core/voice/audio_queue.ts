import {
    AudioStreamPlayer,
    type AudioStreamItem,
} from "./audio_playback";

export class AudioQueue {
    private queue: AudioStreamItem[] = [];
    private isPlaying = false;
    private playbackGeneration = 0;
    private cancelCurrentPlayback: (() => void) | null = null;
    private readonly player = new AudioStreamPlayer();

    enqueue(item: AudioStreamItem): void {
        this.queue.push(item);
        if (!this.isPlaying) void this.playNext();
    }

    clear(): void {
        this.queue = [];
        this.playbackGeneration += 1;
        this.cancelCurrentPlayback?.();
        this.cancelCurrentPlayback = null;
        this.player.clear();
        this.isPlaying = false;
    }

    get length(): number {
        return this.queue.length;
    }

    private async playNext(): Promise<void> {
        const item = this.queue.shift();
        if (!item) {
            this.isPlaying = false;
            return;
        }

        this.isPlaying = true;
        const generation = this.playbackGeneration;
        try {
            await this.makeCancellable(this.player.play(item));
        } catch (error) {
            console.error("[AudioQueue] Playback error:", error);
        }
        if (generation === this.playbackGeneration) void this.playNext();
    }

    private makeCancellable(playback: Promise<void>): Promise<void> {
        return new Promise((resolve, reject) => {
            let settled = false;
            const settle = (callback: () => void) => {
                if (settled) return;
                settled = true;
                if (this.cancelCurrentPlayback === cancel) {
                    this.cancelCurrentPlayback = null;
                }
                callback();
            };
            const cancel = () => settle(resolve);
            this.cancelCurrentPlayback = cancel;
            playback.then(
                () => settle(resolve),
                (error) => settle(() => reject(error)),
            );
        });
    }
}
