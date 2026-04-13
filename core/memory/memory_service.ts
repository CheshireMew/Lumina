import { Message } from "../llm/types";

type MemorySearchResult = {
  content?: string;
  created_at?: string;
  payload?: {
    text?: string;
  };
  text?: string;
  timestamp?: string;
};

function formatMemoryDate(result: MemorySearchResult): string {
  const tsField = result.timestamp || result.created_at;
  if (!tsField) {
    return "Unknown";
  }

  const date = new Date(tsField);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return date.toISOString().split("T")[0];
}

function getMemoryText(result: MemorySearchResult): string {
  return result.text || result.content || result.payload?.text || "(No content)";
}

function formatMemorySummary(results: MemorySearchResult[]): string {
  return results
    .map((result) => `- [${formatMemoryDate(result)}] ${getMemoryText(result)}`)
    .join("\n");
}

export class MemoryService {
  private static instance: MemoryService;
  private isConfigured: boolean = false;
  private currentCharacterId: string = "hiyori"; // Default character
  private baseUrl: string = "http://127.0.0.1:8010"; // Default, can be overridden

  private constructor() {}

  public static getInstance(): MemoryService {
    if (!MemoryService.instance) {
      MemoryService.instance = new MemoryService();
    }
    return MemoryService.instance;
  }

  public setBaseUrl(url: string) {
    // Remove trailing slash if present
    this.baseUrl = url.replace(/\/$/, "");
    console.log(`[MemoryService] Base URL updated to: ${this.baseUrl}`);
  }

  private buildRootUrl(path: string): string {
    return `${this.baseUrl}/${path.replace(/^\/+/, "")}`;
  }

  private buildMemoryUrl(path: string): string {
    return this.buildRootUrl(`memory/${path}`);
  }

  /**
   * Set the current character for memory operations
   */
  public setCharacter(characterId: string): void {
    console.log(`[MemoryService] Switching to character: ${characterId}`);
    this.currentCharacterId = characterId;
    // Mark as unconfigured to force re-configuration
    this.isConfigured = false;
  }

  /**
   * Get current character ID
   */
  public getCurrentCharacter(): string {
    return this.currentCharacterId;
  }

  /**
   * Configure the memory server with LLM credentials
   */
  public async configure(
    apiKey: string,
    baseUrl: string,
    model: string,
    characterId?: string,
    providerType: "free" | "custom" = "custom"
  ): Promise<boolean> {
    if (characterId) {
      this.currentCharacterId = characterId;
    }
    console.log(
      `[MemoryService] Configuring for character: ${this.currentCharacterId}`
    );
    console.log(`[MemoryService] Model: ${model}, BaseURL: ${baseUrl}`);
    try {
      const response = await fetch(this.buildRootUrl("configure"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKey,
          base_url: baseUrl,
          model: model,
          provider_type: providerType,
          character_id: this.currentCharacterId, // Include character ID
        }),
      });

      if (response.ok) {
        this.isConfigured = true;
        const data = await response.json();
        console.log(
          "[MemoryService] Configured successfully. Server Response:",
          data
        );
        return true;
      } else {
        const errorText = await response.text();
        console.error(
          "[MemoryService] Configuration failed. Status:",
          response.status,
          "Body:",
          errorText
        );
        return false;
      }
    } catch (error) {
      console.error("[MemoryService] Configuration network error:", error);
      return false;
    }
  }

  /**
   * Search for relevant memories based on query
   */
  public async search(
    query: string,
    limit: number = 10,
    userName: string = "User",
    charName: string = "AI"
  ): Promise<string> {
    if (!this.isConfigured) {
      console.warn("[MemoryService] Search skipped: Not configured.");
      return "";
    }

    console.log(
      `[MemoryService] Searching memory. Query: "${query}", Limit: ${limit}`
    );
    try {
      const payload = {
        user_id: "user",
        character_id: this.currentCharacterId,
        query: query,
        limit: limit,
      };
      console.log("[MemoryService] Search Payload:", JSON.stringify(payload));

      const response = await fetch(this.buildMemoryUrl("search/hybrid"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        console.log("[MemoryService] Search Response Raw Data:", data);

        let results: MemorySearchResult[] = [];
        if (Array.isArray(data)) {
          results = data;
        } else if (data.results && Array.isArray(data.results)) {
          results = data.results;
        }

        console.log(`[MemoryService] Parsed ${results.length} memories.`);

        // Format results into a string with full metadata
        if (results.length > 0) {
          const formatted = formatMemorySummary(results);
          console.log("[MemoryService] Formatted Memory Context:", formatted);
          return formatted;
        }

        return "";
      } else {
        const errorText = await response.text();
        console.error(
          "[MemoryService] Search failed. Status:",
          response.status,
          "Body:",
          errorText
        );
      }
    } catch (error) {
      console.error("[MemoryService] Search network error:", error);
    }
    return "";
  }

  /**
   * Add a conversation turn to memory
   */
  public async add(
    messages: Message[],
    userName: string = "User",
    charName: string = "AI"
  ): Promise<void> {
    if (!this.isConfigured || messages.length === 0) return;

    try {
      console.log(
        `[MemoryService] Adding to memory for character: ${this.currentCharacterId}`
      );
      console.log(
        `[MemoryService] Names - User: ${userName}, Char: ${charName}`
      );
      const payload = {
        user_id: "user",
        character_id: this.currentCharacterId,
        user_name: userName,
        char_name: charName,
        messages: messages,
      };

      await fetch(this.buildMemoryUrl("add"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      console.log("[MemoryService] Add request sent successfully.");
    } catch (error) {
      console.error("[MemoryService] Add error:", error);
    }
  }

  /**
   * Reset memory
   */
  public async reset(): Promise<void> {
    if (!this.isConfigured) return;

    try {
      console.log("[MemoryService] Requesting context reset...");
      await fetch(this.buildMemoryUrl("context/clear"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "default_user",
          character_id: this.currentCharacterId,
        }),
      });
      console.log("[MemoryService] Context reset successfully.");
    } catch (error) {
      console.error("[MemoryService] Reset error:", error);
    }
  }

}

export const memoryService = MemoryService.getInstance();
