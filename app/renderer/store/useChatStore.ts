import { create } from "zustand";
import type { Message } from "@core/llm/types";
import { CHAT_MESSAGE_LIMIT } from "../../shared/productDefaults";

export type { Message } from "@core/llm/types";

interface ChatState {
    // State
    messages: Message[];
    isConnected: boolean;
    isProcessing: boolean;
    isStreaming: boolean;
    sessionId: number;
    generation: number;
    activeTurnIds: string[];
    currentEmotion: string;

    // Actions
    addMessage: (msg: Message) => void;
    upsertMessage: (msg: Message) => void;
    updateMessage: (id: string, patch: Partial<Message>) => void;
    mergeHistory: (messages: Message[]) => void;
    setConnection: (status: boolean) => void;
    startTurn: (turnId: string) => void;
    finishTurn: (turnId: string) => void;
    setSession: (id: number, generation: number) => void;
    setEmotion: (emotion: string) => void;
    clearHistory: () => void;
    resetState: () => void;
}

const retainRecentMessages = (messages: Message[]) =>
    messages.slice(-CHAT_MESSAGE_LIMIT);

export const useChatStore = create<ChatState>((set) => ({
    messages: [],
    isConnected: false,
    isProcessing: false,
    isStreaming: false,
    sessionId: 0,
    generation: 0,
    activeTurnIds: [],
    currentEmotion: "neutral",

    addMessage: (msg) =>
        set((state) => ({ messages: retainRecentMessages([...state.messages, msg]) })),

    upsertMessage: (msg) =>
        set((state) => {
            const index = state.messages.findIndex((item) => item.id === msg.id);
            if (index < 0) {
                return { messages: retainRecentMessages([...state.messages, msg]) };
            }
            const messages = [...state.messages];
            messages[index] = { ...messages[index], ...msg };
            return { messages };
        }),

    updateMessage: (id, patch) =>
        set((state) => {
            const index = state.messages.findIndex((message) => message.id === id);
            if (index < 0) return state;
            const current = state.messages[index];
            const changed = Object.entries(patch).some(
                ([key, value]) => current[key as keyof Message] !== value,
            );
            if (!changed) return state;
            const messages = state.messages.slice();
            messages[index] = { ...current, ...patch };
            return { messages };
        }),

    mergeHistory: (history) =>
        set((state) => {
            const merged = new Map<string, Message>();
            for (const message of history) merged.set(message.id, message);
            for (const message of state.messages) merged.set(message.id, message);
            return {
                messages: retainRecentMessages(
                    [...merged.values()].sort(
                        (left, right) => left.timestamp - right.timestamp,
                    ),
                ),
            };
        }),

    setConnection: (status) => set({ isConnected: status }),

    startTurn: (turnId) =>
        set((state) => {
            const activeTurnIds = state.activeTurnIds.includes(turnId)
                ? state.activeTurnIds
                : [...state.activeTurnIds, turnId];
            return { activeTurnIds, isProcessing: true, isStreaming: true };
        }),

    finishTurn: (turnId) =>
        set((state) => {
            const activeTurnIds = state.activeTurnIds.filter((id) => id !== turnId);
            return {
                activeTurnIds,
                isProcessing: activeTurnIds.length > 0,
                isStreaming: activeTurnIds.length > 0,
            };
        }),

    setSession: (id, generation) => set({ sessionId: id, generation }),

    setEmotion: (emotion) => set({ currentEmotion: emotion }),

    clearHistory: () => set({ messages: [], activeTurnIds: [], isProcessing: false, isStreaming: false }),

    resetState: () =>
        set({
            messages: [],
            isProcessing: false,
            isStreaming: false,
            sessionId: 0,
            generation: 0,
            activeTurnIds: [],
            currentEmotion: "neutral",
        }),
}));
