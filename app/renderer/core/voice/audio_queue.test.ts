import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AudioQueue } from "@core/voice/audio_queue";

class AudioStub {
    static instances: AudioStub[] = [];

    src = "";
    currentTime = 0;
    onended: (() => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    pause = vi.fn();
    load = vi.fn();
    play = vi.fn(async () => undefined);

    constructor() {
        AudioStub.instances.push(this);
    }

    removeAttribute(name: string) {
        if (name === "src") this.src = "";
    }
}

describe("AudioQueue", () => {
    beforeEach(() => {
        AudioStub.instances = [];
        vi.stubGlobal("Audio", AudioStub);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("cancels an active stream and empties queued audio on clear", async () => {
        const cancel = vi.fn();
        const activeStream = new ReadableStream<Uint8Array>({
            pull: () => new Promise<void>(() => undefined),
            cancel,
        });
        const queuedStream = new ReadableStream<Uint8Array>();
        const queue = new AudioQueue();

        queue.enqueue({ stream: activeStream, contentType: "audio/wav" });
        queue.enqueue({ stream: queuedStream, contentType: "audio/wav" });
        await Promise.resolve();

        expect(queue.length).toBe(1);
        queue.clear();

        await vi.waitFor(() => expect(cancel).toHaveBeenCalledOnce());
        expect(queue.length).toBe(0);
        expect(AudioStub.instances[0].pause).toHaveBeenCalledOnce();
    });
});
