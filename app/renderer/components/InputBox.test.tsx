import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InputBox from "./InputBox";

const { analyzeMock } = vi.hoisted(() => ({ analyzeMock: vi.fn() }));

vi.mock("../hooks/useVisionUpload", () => ({
    useVisionUpload: () => ({ isAnalyzing: false, analyze: analyzeMock }),
}));

vi.mock("../hooks/useVoiceInputSession", () => ({
    useVoiceInputSession: () => ({
        vadStatus: "idle",
        voiceError: "",
        transcript: "",
        setVoiceError: vi.fn(),
    }),
}));

const baseProps = {
    embedded: true,
    chatMode: "text" as const,
    onToggleChatMode: vi.fn(),
    visionBaseUrl: "http://127.0.0.1:8005",
};

describe("InputBox", () => {
    beforeEach(() => vi.clearAllMocks());

    it("keeps text when the runtime rejects a send", () => {
        const onSend = vi.fn(() => false);
        render(<InputBox {...baseProps} onSend={onSend} />);
        const input = screen.getByPlaceholderText("和 Lumina 说点什么…");

        fireEvent.change(input, { target: { value: "第二条消息" } });
        fireEvent.keyDown(input, { key: "Enter" });

        expect(onSend).toHaveBeenCalledWith("第二条消息");
        expect(input).toHaveValue("第二条消息");
    });

    it("clears text only after the runtime accepts a send", () => {
        const onSend = vi.fn(() => true);
        render(<InputBox {...baseProps} onSend={onSend} />);
        const input = screen.getByPlaceholderText("和 Lumina 说点什么…");

        fireEvent.change(input, { target: { value: "可以发送" } });
        fireEvent.keyDown(input, { key: "Enter" });

        expect(onSend).toHaveBeenCalledWith("可以发送");
        expect(input).toHaveValue("");
    });

    it("explains why image upload is unavailable", () => {
        render(
            <InputBox
                {...baseProps}
                onSend={vi.fn()}
                visionCapabilityState="failed"
                visionCapabilityError="请配置支持图片的模型"
            />,
        );

        expect(screen.getByTitle("请配置支持图片的模型")).toBeDisabled();
    });

    it("keeps Shift+Enter available for a line break", () => {
        const onSend = vi.fn();
        render(<InputBox {...baseProps} onSend={onSend} />);
        const input = screen.getByLabelText("消息输入");

        fireEvent.change(input, { target: { value: "第一行" } });
        fireEvent.keyDown(input, { key: "Enter", shiftKey: true });

        expect(onSend).not.toHaveBeenCalled();
        expect(input).toHaveValue("第一行");
    });

    it("shows an explicit stop action while a reply is running", () => {
        const onInterrupt = vi.fn();
        render(
            <InputBox
                {...baseProps}
                onSend={vi.fn()}
                isProcessing
                disabled
                onInterrupt={onInterrupt}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: "停止生成" }));
        expect(onInterrupt).toHaveBeenCalledTimes(1);
    });

    it("shows an attached image without inserting analysis into the visible text", async () => {
        analyzeMock.mockResolvedValueOnce("画面中是一只猫");
        const { container } = render(<InputBox {...baseProps} onSend={vi.fn()} />);
        const file = new File(["image"], "cat.png", { type: "image/png" });

        fireEvent.change(container.querySelector('input[type="file"]')!, {
            target: { files: [file] },
        });

        expect(await screen.findByText("cat.png")).toBeInTheDocument();
        expect(screen.getByLabelText("消息输入")).toHaveValue("");
        fireEvent.click(screen.getByRole("button", { name: "移除图片" }));
        expect(screen.queryByText("cat.png")).not.toBeInTheDocument();
    });

    it("sends image analysis as hidden request context", async () => {
        analyzeMock.mockResolvedValueOnce("画面中是一只猫");
        const onSend = vi.fn(() => true);
        const { container } = render(<InputBox {...baseProps} onSend={onSend} />);
        const file = new File(["image"], "cat.png", { type: "image/png" });

        fireEvent.change(container.querySelector('input[type="file"]')!, {
            target: { files: [file] },
        });
        await screen.findByText("cat.png");
        fireEvent.change(screen.getByLabelText("消息输入"), {
            target: { value: "帮我看看" },
        });
        fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

        await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1));
        expect(onSend).toHaveBeenCalledWith(expect.objectContaining({
            displayText: "帮我看看",
            requestText: expect.stringContaining("画面中是一只猫"),
            attachments: [expect.objectContaining({ name: "cat.png" })],
        }));
    });
});
