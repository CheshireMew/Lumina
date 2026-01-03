import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";

export class LLMService {
    private chatModel: ChatOpenAI | null = null;
    private systemPrompt: string = "You are Lumina, a cute and helpful AI companion. You are chatting with your user.";

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
}

export const llmService = new LLMService();
