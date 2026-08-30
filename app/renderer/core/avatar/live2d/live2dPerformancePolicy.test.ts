import { describe, expect, it } from "vitest";

import {
    LIVE2D_ACTIVE_FRAME_RATE,
    LIVE2D_IDLE_FRAME_RATE,
    resolveLive2DResolution,
} from "./live2dPerformancePolicy";

describe("Live2D performance policy", () => {
    it("caps high-DPI rendering without disabling density-aware output", () => {
        expect(resolveLive2DResolution(false, 2.5)).toBe(1);
        expect(resolveLive2DResolution(true, 1.25)).toBe(1.25);
        expect(resolveLive2DResolution(true, 2.5)).toBe(1.5);
    });

    it("uses a lower idle frame rate than the interaction frame rate", () => {
        expect(LIVE2D_IDLE_FRAME_RATE).toBeLessThan(LIVE2D_ACTIVE_FRAME_RATE);
    });
});
