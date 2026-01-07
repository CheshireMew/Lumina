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
        longTermMemory?: string,
        userName: string = 'User',
        charName: string = 'Assistant'
    ): Promise<string> {
        if (!this.chatModel) {
            throw new Error("Chat model not initialized");
        }

        try {
            // ✅ DeepSeek 缓存优化结构：
            // 1. 历史对话（可缓存前缀）
            // 2. 当前用户消息
            // 3. System Prompt + 记忆 + 摘要（合并为一条 SystemMessage）
            
            const messages: BaseMessage[] = [];

            // 1️⃣ 历史对话作为可缓存前缀（最前面，最稳定）
            // 应用滑动窗口：只保留最近的 contextWindow 轮对话
            const maxHistoryMessages = contextWindow * 2;
            const recentHistory = conversationHistory.slice(-maxHistoryMessages);

            // 将历史转换为 LangChain 消息（使用真实用户名和角色名，避免出戏）
            for (const msg of recentHistory) {
                if (msg.role === 'user') {
                    messages.push(new HumanMessage({ content: msg.content, name: userName }));
                } else if (msg.role === 'assistant') {
                    messages.push(new AIMessage({ content: msg.content, name: charName }));
                }
            }

            // 2️⃣ 当前用户消息（纯消息，不附加上下文）
            messages.push(new HumanMessage({ content: userMessage, name: userName }));

            // 3️⃣ 动态 System Prompt（放最后，包含所有动态上下文）
            let dynamicSystemPrompt = this.systemPrompt;

            // 附加长期记忆
            if (longTermMemory) {
                dynamicSystemPrompt += `\n\n## 相关记忆（来自过往对话）\n${longTermMemory}\n\n请利用这些记忆提供个性化的回复，但不要明确提及你在阅读记忆，除非相关。`;
            }

            // 附加对话摘要
            if (summary) {
                dynamicSystemPrompt += `\n\n## 之前的对话摘要\n${summary}`;
            }

            messages.push(new SystemMessage(dynamicSystemPrompt));

            // ========== [DEBUG] 详细的请求内容打印 ==========
            console.log('\n\n' + '═'.repeat(80));
            console.log('📤 发送给 DeepSeek 的完整请求内容');
            console.log('═'.repeat(80));
            
            console.log(`\n📋 请求配置:`);
            console.log(`   - 用户名: "${userName}"`);
            console.log(`   - 角色名: "${charName}"`);
            console.log(`   - 消息总数: ${messages.length}`);
            console.log(`   - Context Window: ${contextWindow} 轮`);
            console.log(`   - 历史对话: ${recentHistory.length} 条`);
            
            console.log(`\n📨 消息结构详情:\n`);
            
            messages.forEach((msg, index) => {
                let roleIcon = '';
                let roleText = '';
                let msgName = '';
                
                if (msg._getType() === 'human') {
                    roleIcon = '👤';
                    roleText = 'User';
                    msgName = (msg as any).name || 'Unknown';
                } else if (msg._getType() === 'ai') {
                    roleIcon = '🤖';
                    roleText = 'Assistant';
                    msgName = (msg as any).name || 'Unknown';
                } else if (msg._getType() === 'system') {
                    roleIcon = '⚙️';
                    roleText = 'System';
                    msgName = 'System';
                }
                
                const content = msg.content.toString();
                const preview = content.substring(0, 100);
                
                console.log(`[${index + 1}] ${roleIcon} ${roleText} (name: "${msgName}")`);
                console.log(`    Preview: ${preview}${content.length > 100 ? '...' : ''}`);
                console.log(`    Length: ${content.length} chars\n`);
            });
            
            // 打印 API 格式
            const apiMessages = messages.map(msg => {
                let role = '';
                if (msg._getType() === 'human') role = 'user';
                else if (msg._getType() === 'ai') role = 'assistant';
                else if (msg._getType() === 'system') role = 'system';
                
                const apiMsg: any = {
                    role,
                    content: msg.content.toString()
                };
                
                const msgName = (msg as any).name;
                if (msgName) apiMsg.name = msgName;
                
                return apiMsg;
            });
            
            console.log('═'.repeat(80));
            console.log('📡 实际 API 请求格式 (JSON):');
            console.log('═'.repeat(80));
            console.log(JSON.stringify({
                model: 'deepseek-chat',
                messages: apiMessages,
                stream: true,
                temperature: 0.7
            }, null, 2));
            
            console.log('\n' + '═'.repeat(80));
            console.log('💾 完整 System Prompt 内容:');
            console.log('═'.repeat(80));
            console.log(dynamicSystemPrompt);
            
            console.log('\n' + '═'.repeat(80));
            console.log('🔍 缓存分析:');
            console.log('═'.repeat(80));
            
            const historyTokenEstimate = recentHistory.reduce((sum, msg) => 
                sum + Math.ceil(msg.content.length / 4), 0
            );
            const currentTokenEstimate = Math.ceil(userMessage.length / 4);
            const systemTokenEstimate = Math.ceil(dynamicSystemPrompt.length / 4);
            const totalTokens = historyTokenEstimate + currentTokenEstimate + systemTokenEstimate;
            
            console.log(`\n1️⃣ 历史对话 (可缓存): ~${historyTokenEstimate} tokens`);
            console.log(`2️⃣ 当前消息: ~${currentTokenEstimate} tokens`);
            console.log(`3️⃣ System Prompt: ~${systemTokenEstimate} tokens`);
            console.log(`\n   总计: ~${totalTokens} tokens`);
            console.log(`   可缓存比例: ${((historyTokenEstimate / totalTokens) * 100).toFixed(1)}%`);
            console.log(`   💰 预估节省: 40-60% (第2轮起)\n`);
            
            console.log('═'.repeat(80) + '\n');
            // ========== [DEBUG END] ==========

            console.log(`[LLMService] Sending ${messages.length} messages (context window: ${contextWindow} turns)`);

            // 4️⃣ 流式请求
            const stream = await this.chatModel.stream(messages);

            let fullResponse = '';
            for await (const chunk of stream) {
                const content = chunk.content as string;
                if (content) {
                    fullResponse += content;
                    onToken(content);
                }
            }

            // [DEBUG] Log Response content
            console.log(`\n--- [LLM Output from ${charName}] ---`);
            console.log(fullResponse.substring(0, 500) + (fullResponse.length > 500 ? '...' : ''));
            console.log('--------------------\n');

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
