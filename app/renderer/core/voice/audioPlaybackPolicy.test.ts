import { describe, expect, it, vi } from "vitest";

import { canStreamAudioWithMediaSource } from "@core/voice/audio_playback";

describe("audio playback policy", () => {
    it("streams MP3 when Chromium advertises MediaSource support", () => {
        const support = {
            isTypeSupported: vi.fn((contentType: string) => contentType === "audio/mpeg"),
        };

        expect(canStreamAudioWithMediaSource("audio/mpeg", support)).toBe(true);
        expect(canStreamAudioWithMediaSource("audio/wav", support)).toBe(false);
    });
});
