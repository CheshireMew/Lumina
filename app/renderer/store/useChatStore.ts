import { create } from "zustand";

export interface Message {
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: number;
}

interface ChatState {
    // State
    messages: Message[];
    isConnected: boolean;
    isProcessing: boolean;
    isStreaming: boolean;
    sessionId: number;
    currentEmotion: string;

    // Actions
    addMessage: (msg: Message) => void;
    setConnection: (status: boolean) => void;
    setProcessing: (status: boolean) => void;
    setStreaming: (status: boolean) => void;
    setSessionId: (id: number) => void;
    setEmotion: (emotion: string) => void;
    clearHistory: () => void;
    resetState: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
    messages: [],
    isConnected: false,
    isProcessing: false,
    isStreaming: false,
    sessionId: 0,
    currentEmotion: "neutral",

    addMessage: (msg) =>
        set((state) => ({ messages: [...state.messages, msg] })),

    setConnection: (status) => set({ isConnected: status }),

    setProcessing: (status) => set({ isProcessing: status }),

    setStreaming: (status) => set({ isStreaming: status }),

    setSessionId: (id) => set({ sessionId: id }),

    setEmotion: (emotion) => set({ currentEmotion: emotion }),

    clearHistory: () => set({ messages: [] }),

    resetState: () =>
        set({
            messages: [],
            isProcessing: false,
            isStreaming: false,
            sessionId: 0,
            currentEmotion: "neutral",
        }),
}));
