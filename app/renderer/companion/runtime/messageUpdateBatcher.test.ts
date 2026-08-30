import { describe, expect, it, vi } from "vitest";

import { FrameMessageUpdateBatcher } from "./messageUpdateBatcher";

describe("FrameMessageUpdateBatcher", () => {
    it("coalesces a token burst into one final update per animation frame", () => {
        const scheduled: { current: FrameRequestCallback | null } = { current: null };
        const requestFrame = vi.fn((callback: FrameRequestCallback) => {
            scheduled.current = callback;
            return 7;
        });
        const cancelFrame = vi.fn();
        const commit = vi.fn();
        const batcher = new FrameMessageUpdateBatcher(
            commit,
            requestFrame,
            cancelFrame,
        );

        let raw = "";
        for (let index = 0; index < 300; index++) {
            raw += "字";
            batcher.queue("turn-1", { raw, reasoning: "" });
        }

        expect(requestFrame).toHaveBeenCalledTimes(1);
        expect(commit).not.toHaveBeenCalled();
        expect(scheduled.current).not.toBeNull();
        scheduled.current!(16);
        expect(commit).toHaveBeenCalledTimes(1);
        expect(commit).toHaveBeenCalledWith("turn-1", {
            raw: "字".repeat(300),
            reasoning: "",
        });
    });
});
