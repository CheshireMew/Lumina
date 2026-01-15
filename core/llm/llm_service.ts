import { Message } from "./types";
import axios from "axios";
import { app } from "electron";

export class LLMService {
    private backendUrl: string = "http://127.0.0.1:8010"; // Default to Memory Server Port
    private systemPrompt: string = "";

    /**
     * Initialize Service.
     * Args are kept for backward compatibility with main.ts but mostly ignored.
     * The Backend manages the actual Provider API Keys.
     */
    public init(
        apiKey: string,
        baseUrl: string = "http://127.0.0.1:8010",
        modelName: string = "default",
        temperature: number = 0.7
    ) {
        if (
            baseUrl &&
            !baseUrl.includes("api.deepseek") &&
            !baseUrl.includes("api.openai")
        ) {
            // If passing a local URL, assume it's our backend
            this.backendUrl = baseUrl;
        }
        // We ignore apiKey and modelName here as they are managed by Python Backend
        console.log(
            `[LLMService] Initialized Proxy to Backend: ${this.backendUrl}`
        );
    }

    public setSystemPrompt(prompt: string) {
        this.systemPrompt = prompt;
    }

    public async chatStreamWithHistory(
        conversationHistory: Message[],
        userMessage: string,
        contextWindow: number,
        onToken: (token: string, type?: "content" | "reasoning") => void,
        summary?: string,
        longTermMemory?: string,
        userName: string = "User",
        charName: string = "Assistant",
        role: "user" | "system" = "user",
        dynamicInstruction?: string,
        enableThinking: boolean = false,
        temperature?: number,
        topP?: number,
        presencePenalty?: number,
        frequencyPenalty?: number,
        characterId?: string,
        userId?: string
    ): Promise<string> {
        // [Phase 20] Construct Payload
        let payload: any = {};
        const messages: any[] = [];

        const useServerSideContext = !!(characterId && userId && userMessage);

        if (useServerSideContext) {
            // --- Server-Side Context Mode ---
            payload = {
                user_input: userMessage,
                user_id: userId,
                character_id: characterId,
                user_name: userName,
                char_name: charName,
                long_term_memory: longTermMemory || "", // Optional override
                // Note: dynamicInstruction is not explicitly passed to Python ChatRequest in this mode yet?
                // If dynamicInstruction exists, we should probably append it to user_input or handle via separate logic.
                // But 'proactive' chat uses dynamicInstruction.
                // Let's append to input for now:
            };
            if (dynamicInstruction) {
                payload.user_input = `${payload.user_input}\n\n(System Instruction: ${dynamicInstruction})`;
            }
        } else {
            // --- Legacy Mode (Client Managed History) ---
            // 1. Construct Messages List

            // A. History
            const maxHistoryMessages = contextWindow * 2;
            const recentHistory = conversationHistory.slice(
                -maxHistoryMessages
            );

            recentHistory.forEach((msg) => {
                messages.push({
                    role:
                        msg.role === "user"
                            ? "user"
                            : msg.role === "assistant"
                            ? "assistant"
                            : "system",
                    content: msg.content,
                });
            });

            // B. Context?
            // Python ChatService handles System Prompt injection.
            // Python ChatService handles longTermMemory injection if passed.

            // C. Current User Message
            messages.push({
                role: role === "system" ? "system" : "user",
                content: userMessage,
            });

            // Additional Context (Summary, Dynamic Instructions)
            // We append them to the LAST 'user' message or send as separate fields?
            // ChatService in Python takes 'long_term_memory'.
            // It doesn't explicitly take 'dynamicInstruction'.
            // Let's bundle dynamicInstruction into user message or add to messages list as system.

            if (summary) {
                // Prepend summary? Or let backend handle?
                // Let's inject as system message at top of history
                messages.unshift({
                    role: "system",
                    content: `## Previous Summary\n${summary}`,
                });
            }

            if (dynamicInstruction) {
                messages.push({
                    role: "system",
                    content: dynamicInstruction,
                });
            }

            payload = {
                messages: messages,
                user_name: userName,
                char_name: charName,
                long_term_memory: longTermMemory || "",
            };
        }

        console.log(
            `[LLMService] Proxying Chat to ${this.backendUrl}/lumina/chat/completions`
        );

        try {
            const response = await fetch(
                `${this.backendUrl}/lumina/chat/completions`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                }
            );

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Backend Error ${response.status}: ${errText}`);
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullResponse = "";

            if (!reader) throw new Error("No response body");

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.slice(6).trim();
                        if (dataStr === "[DONE]") continue;
                        if (dataStr === "[START]") continue;

                        try {
                            const json = JSON.parse(dataStr);
                            if (json.content) {
                                onToken(json.content, "content");
                                fullResponse += json.content;
                            }
                        } catch (e) {
                            // Maybe raw text?
                            console.warn("Failed to parse SSE JSON:", dataStr);
                        }
                    }
                }
            }

            return fullResponse;
        } catch (error) {
            console.error("Chat Proxy Error:", error);
            const errMsg = `System Error: ${
                error instanceof Error ? error.message : String(error)
            }`;
            onToken(errMsg, "content");
            return errMsg;
        }
    }

    // Legacy / stub methods
    public async chat(message: string): Promise<string> {
        return "Use stream";
    }
    public async chatStream(message: string, onToken: any): Promise<string> {
        return "Use history";
    }
    public async updateSummary(
        currentSummary: string,
        newMessages: Message[]
    ): Promise<string> {
        console.log("[LLMService] Requesting Summary Update...");

        const conversationText = newMessages
            .map((m) => `${m.role}: ${m.content}`)
            .join("\n");

        const prompt = `
Please update the following summary with the new conversation. Keep it concise.
    
Current Summary:
${currentSummary || "None"}

New Conversation:
${conversationText}

Updated Summary:
    `.trim();

        const payload = {
            messages: [
                {
                    role: "system",
                    content:
                        "You are a helpful assistant that summarizes conversations.",
                },
                { role: "user", content: prompt },
            ],
            user_name: "System",
            char_name: "Summarizer",
            long_term_memory: "",
        };

        try {
            const response = await fetch(
                `${this.backendUrl}/lumina/chat/completions`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                }
            );

            if (!response.ok) {
                throw new Error(`Summary Backend Error ${response.status}`);
            }

            // The backend returns SSE stream for chat completions
            // We need to consume it to get the full text.
            // Reusing logic from chatStreamWithHistory or simplifying?
            // Since it's a stream, we must read stream.

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullResponse = "";

            if (!reader) throw new Error("No response body");

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.slice(6).trim();
                        if (dataStr === "[DONE]") continue;
                        if (dataStr === "[START]") continue;
                        try {
                            const json = JSON.parse(dataStr);
                            if (json.content) fullResponse += json.content;
                        } catch (e) {}
                    }
                }
            }
            return fullResponse.trim();
        } catch (e) {
            console.error("[LLMService] Update Summary Failed:", e);
            return currentSummary; // Fallback: return old summary
        }
    }
}

export const llmService = new LLMService();
