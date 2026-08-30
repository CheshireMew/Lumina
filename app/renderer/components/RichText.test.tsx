import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RichText } from "./RichText";

describe("RichText", () => {
    const openExternal = vi.fn();
    const writeText = vi.fn().mockResolvedValue(undefined);

    beforeEach(() => {
        vi.clearAllMocks();
        Object.defineProperty(window, "app", {
            configurable: true,
            value: { openExternal },
        });
        Object.defineProperty(navigator, "clipboard", {
            configurable: true,
            value: { writeText },
        });
    });

    it("renders structured replies and keeps links in the system browser", async () => {
        render(
            <RichText content={"# 标题\n- 列表项\n**重点** [官网](https://example.com)\n```ts\nconst answer = 42;\n```"} />,
        );

        expect(screen.getByText("标题")).toBeInTheDocument();
        expect(screen.getByRole("listitem")).toHaveTextContent("列表项");
        expect(screen.getByText("重点").tagName).toBe("STRONG");
        fireEvent.click(screen.getByRole("link", { name: "官网" }));
        expect(openExternal).toHaveBeenCalledWith("https://example.com");

        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "复制代码" }));
        });
        expect(writeText).toHaveBeenCalledWith("const answer = 42;");
    });
});
