import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage, SystemMessage, AIMessage, BaseMessage } from "@langchain/core/messages";
import { Message } from './types';

export class LLMService {
    private chatModel: ChatOpenAI | null = null;
    private systemPrompt: string = ""; // Set dynamically by App.tsx based on active character

    constructor(apiKey?: string, baseUrl?: string, modelName?: string) {
        if (apiKey) {
            this.init(apiKey, baseUrl, modelName);
        }
    }

    public init(apiKey: string, baseUrl: string = 'https://api.deepseek.com/v1', modelName: string = 'deepseek-chat') {
        console.log(`Initializing LLM Service with BaseURL: ${baseUrl}, Model: ${modelName}, KeyLength: ${apiKey?.length}`);
        this.chatModel = new ChatOpenAI({
            apiKey: apiKey, // Explicitly pass as apiKey
            openAIApiKey: apiKey, // Backwards usage
            configuration: {
                baseURL: baseUrl,
            },
            modelName: modelName,
            temperature: 0.7,
        });
    }

    public async chat(message: string): Promise<string> {
        if (!this.chatModel) {
            console.warn('LLM Service not initialized, returning mock response.');
            return "Please configure your API Key in settings first! (LLM not initialized)";
        }

        try {
            const response = await this.chatModel.invoke([
                new SystemMessage(this.systemPrompt),
                new HumanMessage(message),
            ]);

            return response.content as string;
        } catch (error) {
            console.error("LLM Chat Error:", error);
            return `Error: ${error instanceof Error ? error.message : String(error)}`;
        }
    }

    public setSystemPrompt(prompt: string) {
        this.systemPrompt = prompt;
    }

    /**
     * 流式聊天：逐 token 返回 AI 回复
     * @param message 用户消息
     * @param onToken 每收到一个 token 时的回调
     * @returns Promise<string> 完整回复
     */
    public async chatStream(
        message: string,
        onToken: (token: string) => void
    ): Promise<string> {
        if (!this.chatModel) {
            console.warn('LLM Service not initialized');
            const errorMsg = "Please configure your API Key in settings first!";
            onToken(errorMsg);
            return errorMsg;
        }

        try {
            const stream = await this.chatModel.stream([
                new SystemMessage(this.systemPrompt),
                new HumanMessage(message),
            ]);

            let fullResponse = '';
            for await (const chunk of stream) {
                const content = chunk.content as string;
                if (content) {
                    fullResponse += content;
                    onToken(content); // 实时回调
                }
            }

            return fullResponse;
        } catch (error) {
            console.error("LLM Stream Error:", error);
            const errorMsg = `Error: ${error instanceof Error ? error.message : String(error)}`;
            onToken(errorMsg);
            return errorMsg;
        }
    }

    /**
     * 带历史记录的流式聊天
     * @param conversationHistory 完整对话历史
     * @param userMessage 用户当前消息
     * @param contextWindow 保留轮数
     * @param onToken Token 回调
     * @param summary 可选的历史摘要
     * @returns Promise<string> 完整回复
     */
    public async chatStreamWithHistory(
        conversationHistory: Message[],
        userMessage: string,
        contextWindow: number,
        onToken: (token: string) => void,
        summary?: string,
        longTermMemory?: string
    ): Promise<string> {
        if (!this.chatModel) {
            throw new Error("Chat model not initialized");
        }

        try {
            // 1. 构建消息数组
            const messages: BaseMessage[] = [];

            // 2. 添加系统提示
            messages.push(new SystemMessage(this.systemPrompt));

            // 3. Long-term Memory Injection
            if (longTermMemory) {
                const memoryPrompt = `\n\nRELEVANT MEMORIES FROM PAST CONVERSATIONS:\n${longTermMemory}\n\nUse these memories to provide a personalized response, but do not explicitly mention that you are reading from memory unless relevant.`;
                messages.push(new SystemMessage(memoryPrompt));
            }

            // 4. 如果有摘要，作为系统消息注入
            if (summary) {
                messages.push(new SystemMessage(`Previous conversation summary: ${summary}`));
            }

            // 4. 应用滑动窗口：只保留最近的 contextWindow 轮对话
            // 每轮 = 1条用户消息 + 1条助手回复 = 2条消息
            const maxHistoryMessages = contextWindow * 2;
            const recentHistory = conversationHistory.slice(-maxHistoryMessages);

            // 5. 将历史转换为 LangChain 消息
            for (const msg of recentHistory) {
                if (msg.role === 'user') {
                    messages.push(new HumanMessage(msg.content));
                } else if (msg.role === 'assistant') {
                    messages.push(new AIMessage(msg.content));
                }
                // 忽略 'system' 类型的历史消息
            }

            // 6. 添加当前用户消息
            messages.push(new HumanMessage(userMessage));

            console.log(`[LLMService] Sending ${messages.length} messages (context window: ${contextWindow} turns)`);

            // 7. 流式请求
            const stream = await this.chatModel.stream(messages);

            let fullResponse = '';
            for await (const chunk of stream) {
                const content = chunk.content as string;
                if (content) {
                    fullResponse += content;
                    onToken(content);
                }
            }

            return fullResponse;
        } catch (error) {
            console.error("LLM Stream With History Error:", error);
            const errorMsg = `Error: ${error instanceof Error ? error.message : String(error)}`;
            onToken(errorMsg);
            return errorMsg;
        }
    }

    /**
     * 生成对话摘要
     * @param messages 要摘要的对话历史
     * @returns Promise<string> 摘要内容
     */
    public async generateSummary(messages: Message[]): Promise<string> {
        if (!this.chatModel || messages.length === 0) {
            return '';
        }

        try {
            // 构建摘要提示
            let conversationText = '';
            for (const msg of messages) {
                const roleLabel = msg.role === 'user' ? '用户' : 'Lumina';
                conversationText += `${roleLabel}：${msg.content}\n`;
            }

            const summaryPrompt = `请将以下对话总结为一段简短的摘要（100字以内），保留关键信息和上下文：\n\n${conversationText}\n\n摘要：`;

            const response = await this.chatModel.invoke([
                new SystemMessage("你是一个专业的对话摘要助手，能够简洁准确地概括对话内容。"),
                new HumanMessage(summaryPrompt)
            ]);

            return response.content as string;
        } catch (error) {
            console.error("Summary Generation Error:", error);
            return '';
        }
    }

    /**
     * 更新摘要：合并旧摘要和新对话
     * @param currentSummary 当前摘要
     * @param newMessages 需要合并的新对话
     * @returns Promise<string> 更新后的摘要
     */
    public async updateSummary(currentSummary: string, newMessages: Message[]): Promise<string> {
        if (!this.chatModel || newMessages.length === 0) {
            return currentSummary;
        }

        try {
            let conversationText = '';
            for (const msg of newMessages) {
                const roleLabel = msg.role === 'user' ? '用户' : 'Lumina';
                conversationText += `${roleLabel}：${msg.content}\n`;
            }

            const summaryPrompt = `这是之前的对话摘要：
"${currentSummary}"

这是随后发生的对话：
${conversationText}

请更新摘要，包含之前的关键信息和新的对话内容，保持在150字以内：`;

            const response = await this.chatModel.invoke([
                new SystemMessage("你是一个专业的对话摘要助手。"),
                new HumanMessage(summaryPrompt)
            ]);

            return response.content as string;
        } catch (error) {
            console.error("Summary Update Error:", error);
            return currentSummary;
        }
    }
}

export const llmService = new LLMService();
