import { describe, expect, it, vi } from "vitest";

import { SentenceSplitter } from "@core/voice/sentence_splitter";

describe("SentenceSplitter", () => {
    it("keeps short comma fragments together and emits complete sentences", () => {
        vi.useFakeTimers();
        const sentences: string[] = [];
        const splitter = new SentenceSplitter((sentence) => sentences.push(sentence));

        splitter.feedToken("你好，");
        expect(sentences).toEqual([]);
        splitter.feedToken("今天我们去海边散步吧。");

        expect(sentences).toEqual(["你好，今天我们去海边散步吧。"]);
        vi.useRealTimers();
    });

    it("uses a long soft boundary to start synthesis without waiting for timeout", () => {
        vi.useFakeTimers();
        const sentences: string[] = [];
        const splitter = new SentenceSplitter((sentence) => sentences.push(sentence));

        splitter.feedToken("这是一段已经足够长的语音内容，");

        expect(sentences).toHaveLength(1);
        vi.useRealTimers();
    });
});
