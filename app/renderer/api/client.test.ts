import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiRequestError, requestJson } from "./client";

describe("requestJson", () => {
    afterEach(() => vi.unstubAllGlobals());

    it("does not expose raw internal errors from a failed service", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
            JSON.stringify({ detail: "Traceback: secret provider internals" }),
            { status: 500, headers: { "Content-Type": "application/json" } },
        )));

        await expect(requestJson("http://service.invalid/test")).rejects.toMatchObject({
            name: "ApiRequestError",
            message: "服务暂时不可用，请稍后重试。",
            code: "http_500",
        } satisfies Partial<ApiRequestError>);
    });

    it("keeps an explicit localized recovery message from a structured error", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
            JSON.stringify({
                detail: {
                    code: "voiceprint_profile_required",
                    message: "请先注册并启用至少一个声纹，再开启声纹过滤。",
                },
            }),
            { status: 409, headers: { "Content-Type": "application/json" } },
        )));

        await expect(requestJson("http://service.invalid/test")).rejects.toMatchObject({
            message: "请先注册并启用至少一个声纹，再开启声纹过滤。",
            code: "voiceprint_profile_required",
        });
    });
});
