import { describe, expect, it } from "vitest";

import {
    finalizeAssistantContent,
    formatAssistantDisplay,
} from "./chatContent";

describe("chatContent", () => {
    it("removes protocol markup from display content", () => {
        expect(
            formatAssistantDisplay("[happy]\n<|assistant|>Hello there"),
        ).toBe("Hello there");
    });

    it("normalizes stored assistant content with the same contract", () => {
        expect(
            finalizeAssistantContent("  (thinking)  <|assistant|>Need more detail  "),
        ).toBe("Need more detail");
    });
});
