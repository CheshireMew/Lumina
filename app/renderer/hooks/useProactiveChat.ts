import { useEffect, useRef } from "react";
import { CharacterProfile, Message } from "@core/llm/types";

interface UseProactiveChatProps {
  activeCharacterId: string;
  isProcessing: boolean;
  isStreaming: boolean;
  characters: CharacterProfile[];
  conversationHistory: Message[];
  userName: string;
  dynamicInstructionRef: React.MutableRefObject<string>;
  currentSystemPromptRef: React.MutableRefObject<string>;
  onSend: (
    text: string,
    options?: {
      temperature?: number;
      topP?: number;
      presencePenalty?: number;
      frequencyPenalty?: number;
      enableThinking?: boolean;
    }
  ) => Promise<void>;
  backendUrl?: string;
}

import { API_CONFIG } from "../config";

export const useProactiveChat = ({
  activeCharacterId,
  isProcessing,
  isStreaming,
  characters,
  conversationHistory,
  userName,
  dynamicInstructionRef,
  currentSystemPromptRef,
  onSend,
  backendUrl = API_CONFIG.BASE_URL,
}: UseProactiveChatProps) => {
  const isProactiveProcessing = useRef(false);
  const lastProcessedInteractionRef = useRef<string>("");

  // We use a ref for the callback to avoid effect dependencies changing too often
  const onSendRef = useRef(onSend);
  useEffect(() => {
    onSendRef.current = onSend;
  }, [onSend]);

  useEffect(() => {
    if (!activeCharacterId) return;

    const syncState = async () => {
      if (isProactiveProcessing.current) return;

      // Only check if we are NOT currently processing a message/talking
      if (!isProcessing && !isStreaming) {
        try {
          const res = await fetch(
            `${backendUrl}/galgame/${activeCharacterId}/state`
          );
          if (res.ok) {
            const stateData = await res.json();

            // ⚡ Sync Prompts from Character-Specific Endpoint (More Reliable)
            if (stateData.dynamic_instruction) {
              dynamicInstructionRef.current = stateData.dynamic_instruction;
            }
            if (stateData.system_prompt) {
              currentSystemPromptRef.current = stateData.system_prompt;
              (window as any).llm.setSystemPrompt(stateData.system_prompt);
            }

            // Check for 'pending_interaction'
            if (stateData.pending_interaction) {
              console.log(
                "[ProactiveChat] ⚡ Proactive Trigger Detected from Backend!",
                stateData.pending_interaction
              );

              // 1. 先上锁，防止下一次轮询进入
              if (isProactiveProcessing.current) return;

              // ⚡ Duplicate Check: Prevent handling same interaction twice
              const interactionTs =
                stateData.pending_interaction.timestamp || "unknown";
              if (lastProcessedInteractionRef.current === interactionTs) {
                console.log(
                  "[ProactiveChat] Skipping duplicate proactive interaction:",
                  interactionTs
                );
                return;
              }
              lastProcessedInteractionRef.current = interactionTs;

              isProactiveProcessing.current = true;

              // 2. 只有在成功清除后台标记后，才让 AI 说话
              try {
                await fetch(`${backendUrl}/soul/mutate?clear_pending=true`, {
                  method: "POST",
                });
              } catch (clearErr) {
                console.error(
                  "[ProactiveChat] Failed to clear pending state, aborting interaction to avoid loop."
                );
                isProactiveProcessing.current = false;
                return;
              }

              // ⚡ 获取关系信息
              const relationship = stateData.relationship || {};
              const level = relationship.level || 0;
              const currentStageLabel =
                relationship.current_stage_label || "Stranger";
              const charName =
                characters.find((c) => c.id === activeCharacterId)?.name ||
                "AI";

              // ⚡ Build Rich Prompt with History + Inspiration
              // 1. Get recent conversation history
              const recentHistory = conversationHistory
                .filter(
                  (m) =>
                    !m.content.trim().startsWith("(Private System Instruction")
                ) // 🛡️ Prevent recursion!
                .slice(-5)
                .map(
                  (m) =>
                    `${
                      m.role === "user" ? userName : charName
                    }: ${m.content.substring(0, 100)}...`
                )
                .join("\n");

              // 2. Fetch random inspiration from memories (SurrealDB)
              let inspirationText = "";
              try {
                const inspirationRes = await fetch(
                  `${backendUrl}/memory/inspiration?character_id=${activeCharacterId}&limit=3`
                );
                if (inspirationRes.ok) {
                  const inspirations = await inspirationRes.json();
                  if (inspirations.length > 0) {
                    // ⚡ Support both SQLite (content) and SurrealDB (context) formats
                    inspirationText = inspirations
                      .map((i: any) => {
                        if (i.context) return `- ${i.context}`; // SurrealDB
                        if (i.content) return `- ${i.content}`; // SQLite
                        // Fallback for edge format: Subject VERB Object
                        if (i.subject && i.relation && i.object)
                          return `- ${i.subject} ${i.relation} ${i.object}`;
                        return "";
                      })
                      .filter((s: string) => s !== "")
                      .join("\n");

                    console.log(
                      `[ProactiveChat] 🎲 Loaded ${inspirations.length} inspirations for proactive chat`
                    );
                  }
                }
              } catch (e) {
                console.warn(
                  "[ProactiveChat] Failed to fetch inspiration, proceeding without"
                );
              }

              // 3. Build enhanced instruction with time and relationship info
              const nowStr = new Date().toLocaleString();
              const dynamicInstruction = dynamicInstructionRef.current || "";
              const reason = stateData.pending_interaction.reason || "";
              const eventData = stateData.pending_interaction.data || {};

              let instruction = "";

              if (reason === "bilibili_danmaku") {
                // 🎥 Live Stream Mode
                const viewerName = eventData.user || "Viewer";
                const danmakuContent = eventData.content || "";

                instruction = `(Private System Instruction - DO NOT EXPOSE THIS TO USER)
[SYSTEM NOTICE]
Current Time: ${nowStr}
Context: You are currently LIVE STREAMING on Bilibili.
Event: 🔴 New Danmaku Received.

User [${viewerName}] said: "${danmakuContent}"

${dynamicInstruction}

GUIDELINES:
- You are a VTuber/Streamer.
- Respond directly to ${viewerName}'s comment.
- Keep it short, engaging, and in-character.
- If it's a gift, thank them excitedly!
- Do not mention you are an AI.`;
              } else {
                // 💤 Idle Mode (Standard Proactive)
                instruction = `(Private System Instruction - DO NOT EXPOSE THIS TO USER)
[SYSTEM NOTICE]
Current Time: ${nowStr}
Relationship: Lv.${level} (${currentStageLabel})
Task:对方已经沉默了很久，Continue a conversation naturally.

${dynamicInstruction}

${inspirationText ? `## Related Topics (Memory)\n${inspirationText}\n` : ""}
GUIDELINES:
- Use the [Related Topics] as a topic starter IF they seem interesting, or just continue the conversation.
- Keep it natural, casual, and brief.
- Context: You are ${charName}. Don't mention you are an AI.
- Based on your personality and the silence, initiate a brand new natural conversation topic. Do NOT repeat previous greetings.`;
              }

              // ⚡ 获取主动对话专用的参数 (Separate params for Proactive)
              let proactiveParams: any = {};
              try {
                const paramsRes = await fetch(
                  `${backendUrl}/llm-mgmt/params/proactive`
                );
                if (paramsRes.ok) {
                  proactiveParams = await paramsRes.json();
                  console.log(
                    "[ProactiveChat] ⚙️ Applying Proactive LLM Params:",
                    proactiveParams
                  );
                }
              } catch (e) {
                console.warn(
                  "[ProactiveChat] Failed to fetch proactive params, using defaults"
                );
              }

              // Use Ref to call handleSend
              await onSendRef.current(instruction, {
                temperature: proactiveParams.temperature,
                topP: proactiveParams.top_p,
                presencePenalty: proactiveParams.presence_penalty,
                frequencyPenalty: proactiveParams.frequency_penalty,
              });

              // 释放锁（在 handleSend 完成后）
              isProactiveProcessing.current = false;
            }
          }
        } catch (e) {
          // silent fail for network issues
          isProactiveProcessing.current = false;
        }
      }
    };

    // ⚡ Run immediately on mount/change
    syncState();

    const interval = setInterval(syncState, 5000); // Check every 5 seconds
    return () => clearInterval(interval);
  }, [
    activeCharacterId,
    isProcessing,
    isStreaming,
    characters,
    conversationHistory,
    userName,
    backendUrl,
  ]); // Added dependencies for safety
};
