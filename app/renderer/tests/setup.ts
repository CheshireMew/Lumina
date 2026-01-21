import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock Electron window.lumina API
Object.defineProperty(window, "lumina", {
    value: {
        invoke: vi.fn(),
        send: vi.fn(),
        on: vi.fn(),
        removeListener: vi.fn(),
    },
    writable: true,
});
