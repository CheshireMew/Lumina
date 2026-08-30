import { describe, expect, it } from "vitest";

import type { RuntimeCapabilitySnapshot } from "./useRuntimeCapabilities";
import { runtimeCapabilityRefreshDelay } from "./useRuntimeCapabilities";

const capability = (status: RuntimeCapabilitySnapshot["status"]) => ({
    capability: "stt",
    status,
}) as RuntimeCapabilitySnapshot;

describe("runtime capability refresh policy", () => {
    it("backs off for stable ready and intentionally offline workers", () => {
        expect(runtimeCapabilityRefreshDelay([
            capability("ready"),
            capability("offline"),
        ])).toBe(60000);
    });

    it("polls briefly while a worker is starting", () => {
        expect(runtimeCapabilityRefreshDelay([capability("starting")])).toBe(3000);
    });
});
