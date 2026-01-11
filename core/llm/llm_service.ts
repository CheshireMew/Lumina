import { ChatOpenAI } from "@langchain/openai";
import {
  HumanMessage,
  SystemMessage,
  AIMessage,
  BaseMessage,
} from "@langchain/core/messages";
import { Message } from "./types";

export class LLMService {
  private chatModel: ChatOpenAI | null = null;
  private systemPrompt: string = "";
  private _apiKey: string = "";
  private _baseUrl: string = "";
  private _modelName: string = "";
  private _temperature: number = 0.7;
  private _topP: number = 1.0;
  private _presencePenalty: number = 0.0;
  private _frequencyPenalty: number = 0.0;

  constructor(
    apiKey?: string,
    baseUrl?: string,
    modelName?: string,
    temperature: number = 0.7,
    topP: number = 1.0,
    presencePenalty: number = 0.0,
    frequencyPenalty: number = 0.0
  ) {
    if (apiKey) {
      this.init(
        apiKey,
        baseUrl,
        modelName,
        temperature,
        topP,
        presencePenalty,
        frequencyPenalty
      );
    }
  }

  public init(
    apiKey: string,
    baseUrl: string = "https://api.deepseek.com/v1",
    modelName: string = "deepseek-chat",
    temperature: number = 0.7,
    topP: number = 1.0,
    presencePenalty: number = 0.0,
    frequencyPenalty: number = 0.0
  ) {
    // ⚡ Force IPv4 for local backend to avoid Node.js resolving 'localhost' to '::1'
    if (baseUrl.includes("localhost")) {
      baseUrl = baseUrl.replace("localhost", "127.0.0.1");
      console.log(`[LLMService] Sanitized BaseURL to IPv4: ${baseUrl}`);
    }

    this._apiKey = apiKey;
    this._baseUrl = baseUrl;
    this._modelName = modelName;
    this._temperature = temperature;
    this._topP = topP;
    this._presencePenalty = presencePenalty;
    this._frequencyPenalty = frequencyPenalty;

    console.log(
      `Initializing LLM Service with BaseURL: ${baseUrl}, Model: ${modelName}, Temp: ${temperature}, KeyLength: ${apiKey?.length}`
    );
    this.chatModel = new ChatOpenAI({
      apiKey: apiKey, // Explicitly pass as apiKey
      openAIApiKey: apiKey, // Backwards usage
      configuration: {
        baseURL: baseUrl,
      },
      modelName: modelName,
      temperature: temperature,
      topP: topP,
      presencePenalty: presencePenalty,
      frequencyPenalty: frequencyPenalty,
    });
  }

  public async chat(message: string): Promise<string> {
    if (!this.chatModel) {
      console.warn("LLM Service not initialized, returning mock response.");
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
      console.warn("LLM Service not initialized");
      const errorMsg = "Please configure your API Key in settings first!";
      onToken(errorMsg);
      return errorMsg;
    }

    try {
      const stream = await this.chatModel.stream([
        new SystemMessage(this.systemPrompt),
        new HumanMessage(message),
      ]);

      let fullResponse = "";
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
      const errorMsg = `Error: ${
        error instanceof Error ? error.message : String(error)
      }`;
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
    onToken: (token: string, type?: "content" | "reasoning") => void,
    summary?: string,
    longTermMemory?: string,
    userName: string = "User",
    charName: string = "Assistant",
    role: "user" | "system" = "user",
    dynamicInstruction?: string,
    enableThinking: boolean = false, // ✅ NEW: Thinking Mode Toggle
    temperature?: number,
    topP?: number,
    presencePenalty?: number,
    frequencyPenalty?: number
  ): Promise<string> {
    if (!this.chatModel) {
      throw new Error("Chat model not initialized");
    }

    try {
      // 1️⃣ Construct Messages using LangChain Types (Universal Format)
      const messages: BaseMessage[] = [];

      // A. Static System Prompt (Top Priority)
      if (this.systemPrompt) {
        messages.push(new SystemMessage(this.systemPrompt));
      }

      // B. Conversation History
      const maxHistoryMessages = contextWindow * 2;
      const recentHistory = conversationHistory.slice(-maxHistoryMessages);

      for (const msg of recentHistory) {
        if (msg.role === "user") {
          messages.push(
            new HumanMessage({ content: msg.content, name: userName })
          );
        } else if (msg.role === "assistant") {
          messages.push(
            new AIMessage({ content: msg.content, name: charName })
          );
        }
      }

      // C. Dynamic Context (Memory + Summary + Dynamic Instruction)
      // Placed right before the current message
      let dynamicContext = "";
      if (longTermMemory && longTermMemory.trim().length > 0) {
        dynamicContext += `\n\n## 相关记忆\n${longTermMemory}`;
      }
      if (summary) {
        dynamicContext += `\n\n## 之前的对话摘要\n${summary}`;
      }
      if (dynamicInstruction) {
        dynamicContext += `\n\n${dynamicInstruction}`;
      }

      if (dynamicContext.trim().length > 0) {
        // Add as a separate System Message
        messages.push(new SystemMessage(dynamicContext.trim()));
      }

      // D. Current User Message
      if (role === "system") {
        messages.push(new SystemMessage(userMessage));
      } else {
        messages.push(
          new HumanMessage({ content: userMessage, name: userName })
        );
      }

      // ========== [DEBUG] Detailed Request Logging (Restored) ==========
      console.log("\n\n" + "═".repeat(80));
      console.log("📤 [LLMService] Full Request Context");
      console.log("═".repeat(80));

      console.log(`\n📋 Configuration:`);
      console.log(`   - User: "${userName}"`);
      console.log(`   - Bot: "${charName}"`);
      console.log(
        `   - Model: "${
          enableThinking ? "deepseek-reasoner" : this._modelName || "default"
        }"`
      );
      console.log(`   - Context Window: ${contextWindow} turns`);
      console.log(`   - History Count: ${recentHistory.length} msgs`);

      console.log(`\n📨 Message Structure:\n`);

      messages.forEach((msg, index) => {
        let roleIcon = "";
        let roleText = "";
        let msgName = "";

        if (msg._getType() === "human") {
          roleIcon = "👤";
          roleText = "User";
          msgName = (msg as any).name || "Unknown";
        } else if (msg._getType() === "ai") {
          roleIcon = "🤖";
          roleText = "Assistant";
          msgName = (msg as any).name || "Unknown";
        } else if (msg._getType() === "system") {
          roleIcon = "⚙️";
          roleText = "System";
          msgName = "System";
        }

        const content = msg.content.toString();
        const preview = content.substring(0, 100).replace(/\n/g, " ");

        console.log(`[${index}] ${roleIcon} ${roleText} (name: "${msgName}")`);
        console.log(
          `    Preview: ${preview}${content.length > 100 ? "..." : ""}`
        );
        console.log(`    Length: ${content.length} chars\n`);
      });

      console.log("═".repeat(80));
      console.log("📡 API Request Preview (JSON):");
      console.log("═".repeat(80));

      const apiMessages = messages.map((msg) => {
        let role = "";
        if (msg._getType() === "human") role = "user";
        else if (msg._getType() === "ai") role = "assistant";
        else if (msg._getType() === "system") role = "system";
        return {
          role,
          content: msg.content.toString(),
          name: (msg as any).name,
        };
      });

      console.log(
        JSON.stringify(
          {
            model: enableThinking
              ? "deepseek-reasoner"
              : this._modelName || "unknown",
            messages: apiMessages,
            stream: true,
          },
          null,
          2
        )
      );

      console.log("\n" + "═".repeat(80));
      console.log("🔍 Token Estimation (approx):");
      console.log("═".repeat(80));

      const historyTokenEstimate = recentHistory.reduce(
        (sum, msg) => sum + Math.ceil(msg.content.length / 3.5),
        0
      );
      const currentTokenEstimate = Math.ceil(userMessage.length / 3.5);
      // Estimate system tokens from all system messages
      const systemMsgs = messages.filter((m) => m._getType() === "system");
      const systemTokenEstimate = systemMsgs.reduce(
        (sum, m) => sum + Math.ceil(m.content.toString().length / 3.5),
        0
      );
      const totalTokens =
        historyTokenEstimate + currentTokenEstimate + systemTokenEstimate;

      console.log(`1️⃣ History: ~${historyTokenEstimate} tokens`);
      console.log(`2️⃣ Current: ~${currentTokenEstimate} tokens`);
      console.log(`3️⃣ System: ~${systemTokenEstimate} tokens`);
      console.log(`\n   Total: ~${totalTokens} tokens`);

      console.log("═".repeat(80));

      let fullResponse = "";

      // 🔄 BRANCH: Thinking Mode vs Standard Mode
      if (enableThinking) {
        // === Path A: Direct Fetch for DeepSeek Thinking ===
        const apiKey = this._apiKey;
        const baseUrl = this._baseUrl;
        const modelName = "deepseek-reasoner";

        // Convert LangChain messages to Raw API format
        const apiMessages = messages.map((m) => {
          const role =
            m._getType() === "human"
              ? "user"
              : m._getType() === "ai"
              ? "assistant"
              : "system";
          return { role, content: m.content.toString(), name: (m as any).name };
        });

        console.log(`[LLMService] 🧠 Thinking Mode Active (${modelName})`);

        const response = await fetch(`${baseUrl}/chat/completions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model: modelName,
            messages: apiMessages,
            stream: true,
            temperature: temperature ?? this._temperature,
            top_p: topP ?? this._topP,
            presence_penalty: presencePenalty ?? this._presencePenalty,
            frequency_penalty: frequencyPenalty ?? this._frequencyPenalty,
          }),
        });

        if (!response.ok) {
          const err = await response.text();
          throw new Error(`DeepSeek API Error: ${response.status} ${err}`);
        }
        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (!line.startsWith("data: ") || line.trim() === "data: [DONE]")
              continue;
            try {
              const data = JSON.parse(line.slice(6));
              const delta = data.choices[0]?.delta;
              if (delta) {
                if (delta.reasoning_content) {
                  onToken(delta.reasoning_content, "reasoning");
                }
                if (delta.content) {
                  fullResponse += delta.content;
                  onToken(delta.content, "content");
                }
              }
            } catch (e) {}
          }
        }
      } else {
        // === Path B: Standard LangChain Stream ===
        console.log(
          `[LLMService] 💬 Standard Mode (${this._modelName || "default"})`
        );
        const stream = await this.chatModel.stream(messages);

        for await (const chunk of stream) {
          const content = chunk.content as string;
          if (content) {
            fullResponse += content;
            onToken(content, "content");
          }
        }
      }

      console.log(
        `\n--- [LLM Output] ---\n${fullResponse.substring(
          0,
          200
        )}...\n--------------------\n`
      );
      return fullResponse;
    } catch (error) {
      console.error("LLM Stream With History Error:", error);
      const errorMsg = `Error: ${
        error instanceof Error ? error.message : String(error)
      }`;
      onToken(errorMsg, "content");
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
      return "";
    }

    try {
      // 构建摘要提示
      let conversationText = "";
      for (const msg of messages) {
        const roleLabel = msg.role === "user" ? "用户" : "Lumina";
        conversationText += `${roleLabel}：${msg.content}\n`;
      }

      const summaryPrompt = `请将以下对话总结为一段简短的摘要（100字以内），保留关键信息和上下文：\n\n${conversationText}\n\n摘要：`;

      const response = await this.chatModel.invoke([
        new SystemMessage(
          "你是一个专业的对话摘要助手，能够简洁准确地概括对话内容。"
        ),
        new HumanMessage(summaryPrompt),
      ]);

      return response.content as string;
    } catch (error) {
      console.error("Summary Generation Error:", error);
      return "";
    }
  }

  /**
   * 更新摘要：合并旧摘要和新对话
   * @param currentSummary 当前摘要
   * @param newMessages 需要合并的新对话
   * @returns Promise<string> 更新后的摘要
   */
  public async updateSummary(
    currentSummary: string,
    newMessages: Message[]
  ): Promise<string> {
    if (!this.chatModel || newMessages.length === 0) {
      return currentSummary;
    }

    try {
      let conversationText = "";
      for (const msg of newMessages) {
        const roleLabel = msg.role === "user" ? "用户" : "Lumina";
        conversationText += `${roleLabel}：${msg.content}\n`;
      }

      const summaryPrompt = `这是之前的对话摘要：
"${currentSummary}"

这是随后发生的对话：
${conversationText}

请更新摘要，包含之前的关键信息和新的对话内容，保持在150字以内：`;

      const response = await this.chatModel.invoke([
        new SystemMessage("你是一个专业的对话摘要助手。"),
        new HumanMessage(summaryPrompt),
      ]);

      return response.content as string;
    } catch (error) {
      console.error("Summary Update Error:", error);
      return currentSummary;
    }
  }
}

export const llmService = new LLMService();
