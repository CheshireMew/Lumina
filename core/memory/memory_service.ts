
import { Message } from '../llm/types';

const MEMORY_SERVER_URL = 'http://127.0.0.1:8001';

export class MemoryService {
    private static instance: MemoryService;
    private isConfigured: boolean = false;
    private currentCharacterId: string = 'hiyori';  // Default character

    private constructor() { }

    public static getInstance(): MemoryService {
        if (!MemoryService.instance) {
            MemoryService.instance = new MemoryService();
        }
        return MemoryService.instance;
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
    public async configure(apiKey: string, baseUrl: string, model: string, characterId?: string): Promise<boolean> {
        if (characterId) {
            this.currentCharacterId = characterId;
        }
        console.log(`[MemoryService] Configuring for character: ${this.currentCharacterId}`);
        console.log(`[MemoryService] Model: ${model}, BaseURL: ${baseUrl}`);
        try {
            const response = await fetch(`${MEMORY_SERVER_URL}/configure`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_key: apiKey,
                    base_url: baseUrl,
                    model: model,
                    character_id: this.currentCharacterId  // Include character ID
                })
            });

            if (response.ok) {
                this.isConfigured = true;
                const data = await response.json();
                console.log('[MemoryService] Configured successfully. Server Response:', data);
                return true;
            } else {
                const errorText = await response.text();
                console.error('[MemoryService] Configuration failed. Status:', response.status, 'Body:', errorText);
                return false;
            }
        } catch (error) {
            console.error('[MemoryService] Configuration network error:', error);
            return false;
        }
    }

    /**
     * Search for relevant memories based on query
     */
    public async search(query: string, limit: number = 10, userName: string = 'User', charName: string = 'AI'): Promise<string> {
        if (!this.isConfigured) {
            console.warn('[MemoryService] Search skipped: Not configured.');
            return '';
        }

        console.log(`[MemoryService] Searching memory. Query: "${query}", Limit: ${limit}`);
        try {
            const payload = {
                user_id: "user",
                character_id: this.currentCharacterId,
                query: query,
                limit: limit
            };
            console.log('[MemoryService] Search Payload:', JSON.stringify(payload));

            const response = await fetch(`${MEMORY_SERVER_URL}/search/hybrid`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const data = await response.json();
                console.log('[MemoryService] Search Response Raw Data:', data);

                let results: any[] = [];
                if (Array.isArray(data)) {
                    results = data;
                } else if (data.results && Array.isArray(data.results)) {
                    results = data.results;
                }

                console.log(`[MemoryService] Parsed ${results.length} memories.`);

                // Format results into a string with full metadata
                if (results.length > 0) {
                    const formatted = results.map((res: any) => {
                        // Basic info - handle both old (timestamp) and new (created_at) formats
                        let dateStr = 'Unknown';
                        const tsField = res.timestamp || res.created_at;
                        if (tsField) {
                            const date = new Date(tsField);
                            if (!isNaN(date.getTime())) {
                                dateStr = date.toISOString().split('T')[0];
                            }
                        }
                        const scoreStr = (res.score ?? res.hybrid_score ?? 0).toFixed(2);
                        
                        // Extract metadata - handle both old (payload nested) and new (flat) formats
                        const emotion = res.emotion || res.payload?.emotion || 'neutral';
                        const importance = res.importance || res.payload?.importance || 1;
                        
                        // Determine memory owner using current session names
                        const source = res.source || res.payload?.source || 'unknown';
                        const memoryOwner = source === 'user' ? userName : charName;
                        
                        // Get text content - handle both 'text' (SurrealDB alias) and 'content' (formatted)
                        const textContent = res.text || res.content || res.payload?.text || '(No content)';
                        
                        // Format: [Date] Content
                        return `- [${dateStr}] ${textContent}`;
                    }).join('\n');
                    console.log('[MemoryService] Formatted Memory Context:', formatted);
                    return formatted;
                }

                return '';
            } else {
                const errorText = await response.text();
                console.error('[MemoryService] Search failed. Status:', response.status, 'Body:', errorText);
            }
        } catch (error) {
            console.error('[MemoryService] Search network error:', error);
        }
        return '';
    }

    /**
     * Add a conversation turn to memory
     */
    public async add(messages: Message[], userName: string = 'User', charName: string = 'AI'): Promise<void> {
        if (!this.isConfigured || messages.length === 0) return;

        try {
            console.log(`[MemoryService] Adding to memory for character: ${this.currentCharacterId}`);
            console.log(`[MemoryService] Names - User: ${userName}, Char: ${charName}`);
            const payload = {
                user_id: "user",
                character_id: this.currentCharacterId,
                user_name: userName,
                char_name: charName,
                messages: messages
            };

            await fetch(`${MEMORY_SERVER_URL}/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            console.log('[MemoryService] Add request sent successfully.');
        } catch (error) {
            console.error('[MemoryService] Add error:', error);
        }
    }

    /**
     * Archive/Consolidate a batch of history messages.
     * Use this when pruning old conversation history.
     */
    public async consolidateHistory(messages: Message[], userName: string, charName: string): Promise<void> {
        if (!this.isConfigured || messages.length === 0) return;

        try {
            console.log(`[MemoryService] Consolidating ${messages.length} messages...`);
            const payload = {
                user_id: "user",
                character_id: this.currentCharacterId,
                user_name: userName,
                char_name: charName,
                messages: messages
            };

            // Using a new endpoint for bulk consolidation/archiving
            await fetch(`${MEMORY_SERVER_URL}/consolidate_history`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            console.log('[MemoryService] Consolidation request sent.');
        } catch (error) {
            console.error('[MemoryService] Consolidation error:', error);
        }
    }

    /**
     * Reset memory
     */
    public async reset(): Promise<void> {
        if (!this.isConfigured) return;

        try {
            console.log('[MemoryService] Requesting memory reset...');
            await fetch(`${MEMORY_SERVER_URL}/reset`, { method: 'DELETE' });
            console.log('[MemoryService] Memory reset successfully.');
        } catch (error) {
            console.error('[MemoryService] Reset error:', error);
        }
    }



    /**
     * Trigger Deep Dreaming (Level 2 Consolidation) on Idle.
     */
    public async triggerDeepDreaming(userName: string, charName: string): Promise<void> {
        if (!this.isConfigured) return;

        try {
            console.log(`[MemoryService] 🌙 Triggering Deep Dreaming for ${charName}...`);
            const payload = {
                user_id: "user",
                character_id: this.currentCharacterId,
                user_name: userName,
                char_name: charName
            };

            await fetch(`${MEMORY_SERVER_URL}/dream_on_idle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            console.log('[MemoryService] Dream request sent.');
        } catch (error) {
            console.error('[MemoryService] Dream trigger error:', error);
        }
    }

}

export const memoryService = MemoryService.getInstance();
