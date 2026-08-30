import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { retryBackendMock, openLogsMock } = vi.hoisted(() => ({
    retryBackendMock: vi.fn(),
    openLogsMock: vi.fn(),
}));

vi.mock("../platform/electron", () => ({
    retryBackend: retryBackendMock,
    openLogs: openLogsMock,
}));

import { StartupStatus } from "./StartupStatus";

describe("StartupStatus", () => {
    const writeText = vi.fn().mockResolvedValue(undefined);

    beforeEach(() => {
        vi.clearAllMocks();
        retryBackendMock.mockResolvedValue({ status: "ready", ports: {} });
        openLogsMock.mockResolvedValue("D:/logs");
        Object.defineProperty(navigator, "clipboard", {
            configurable: true,
            value: { writeText },
        });
    });

    it("keeps startup failure details visible and exposes recovery actions", async () => {
        render(
            <StartupStatus
                backendState={{
                    status: "error",
                    ports: {},
                    errorMessage: "核心服务端口启动失败，日志中有完整原因。",
                }}
                isSettingsLoaded
            />,
        );

        expect(screen.getByText("后端启动失败")).toBeInTheDocument();
        expect(screen.getByText("核心服务端口启动失败，日志中有完整原因。")).toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: "重新启动" }));
        await waitFor(() => expect(retryBackendMock).toHaveBeenCalledTimes(1));
        fireEvent.click(screen.getByRole("button", { name: "复制详情" }));
        await waitFor(() => expect(writeText).toHaveBeenCalledWith("核心服务端口启动失败，日志中有完整原因。"));
        fireEvent.click(screen.getByRole("button", { name: "打开日志" }));
        await waitFor(() => expect(openLogsMock).toHaveBeenCalledTimes(1));
    });
});
