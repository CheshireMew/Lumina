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

            // ⚡ Sync Prompts
            if (stateData.dynamic_instruction) {
              dynamicInstructionRef.current = stateData.dynamic_instruction;
            }
            if (stateData.system_prompt) {
              currentSystemPromptRef.current = stateData.system_prompt;
              window.llm.setSystemPrompt(stateData.system_prompt);
            }

            // Check for 'pending_interaction'
            if (stateData.pending_interaction) {
              console.log(
                "[ProactiveChat] ⚡ Proactive Trigger Detected!",
                stateData.pending_interaction
              );

              // 1. Lock
              if (isProactiveProcessing.current) return;

              // 2. Dedup
              const interactionTs =
                stateData.pending_interaction.timestamp || "unknown";
              if (lastProcessedInteractionRef.current === interactionTs) {
                console.log(
                  "[ProactiveChat] Skipping duplicate interaction:",
                  interactionTs
                );
                return;
              }
              lastProcessedInteractionRef.current = interactionTs;

              // 3. Mark Processing & Clear Backend
              isProactiveProcessing.current = true;
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

              // ⚡ Context Extraction
              const relationship = stateData.relationship || {};
              const level = relationship.level || 0;
              const currentStageLabel =
                relationship.current_stage_label || "Stranger";
              const charName =
                characters.find((c) => c.id === activeCharacterId)?.name ||
                "AI";

              // ⚡ Inspiration (Random Memories)
              let inspirationText = "";
              try {
                const inspirationRes = await fetch(
                  `${backendUrl}/memory/inspiration?character_id=${activeCharacterId}&limit=3`
                );
                if (inspirationRes.ok) {
                  const inspirations = await inspirationRes.json();
                  if (inspirations.length > 0) {
                    inspirationText = inspirations
                      .map((i: any) => {
                        // Simplify inspiration text extraction
                        return i.content ? `- ${i.content}` : "";
                      })
                      .filter((s: string) => s !== "")
                      .join("\n");
                    console.log(
                      `[ProactiveChat] 🎲 Loaded ${inspirations.length} inspirations`
                    );
                  }
                }
              } catch (e) {
                console.warn("[ProactiveChat] Failed to load inspiration", e);
              }

              // ⚡ Build Instruction
              const nowStr = new Date().toLocaleString();
              const dynamicInstruction = dynamicInstructionRef.current || "";
              const reason = stateData.pending_interaction.reason || "";
              const eventData = stateData.pending_interaction.data || {};

              let instruction = "";

              if (reason === "bilibili") {
                // 🎥 Live Stream Mode (Bilibili Danmaku)
                // Note: 'reason' was 'bilibili_danmaku' in snippet, checking convention.
                // Backend mcp_host.py sets reason="bilibili" (see mcp_host.py view earlier)

                // Parse message from format "[Bilibili] User: Content"
                // Actually mcp_host.py sends full msg string in eventData?
                // Wait, mcp_host.py: self.soul_client.set_pending_interaction(full_msg, "bilibili")
                // So eventData might be just string? Or dict?
                // SoulManager.set_pending_interaction(self, trigger_data, reason="manual")
                // -> self.profile["state"]["galgame"]["pending_interaction"] = { "reason": reason, "timestamp": iso, "data": trigger_data }
                // So trigger_data is the full string "[Bilibili] User: Content".

                const rawMsg =
                  typeof eventData === "string"
                    ? eventData
                    : JSON.stringify(eventData);

                instruction = `(Private System Instruction - DO NOT EXPOSE THIS TO USER)
[SYSTEM NOTICE]
Current Time: ${nowStr}
Context: You are currently LIVE STREAMING on Bilibili.
Event: 🔴 New Danmaku Received.

Content: "${rawMsg}"

${dynamicInstruction}

GUIDELINES:
- You are a VTuber/Streamer.
- Respond directly to the comment.
- Keep it short, engaging, and in-character.
- If it's a gift, thank them excitedly!
- Do not mention you are an AI.`;
              } else {
                // 💤 Idle Mode (Standard Proactive)
                instruction = `(Private System Instruction - DO NOT EXPOSE THIS TO USER)
[SYSTEM NOTICE]
Current Time: ${nowStr}
Relationship: Lv.${level} (${currentStageLabel})
Reason: ${reason} (Silence or Trigger)

${dynamicInstruction}

${inspirationText ? `## Related Topics (Memory)\n${inspirationText}\n` : ""}

GUIDELINES:
- Use the [Related Topics] as a topic starter IF they seem interesting, or just continue the conversation.
- Keep it natural, casual, and brief.
- Context: You are ${charName}. Don't mention you are an AI.
- Based on your personality and the silence, initiate a brand new natural conversation topic. Do NOT repeat previous greetings.`;
              }

              // ⚡ Fetch Proactive Params
              let proactiveParams: any = {};
              try {
                const paramsRes = await fetch(
                  `${backendUrl}/llm-mgmt/params/proactive`
                );
                if (paramsRes.ok) {
                  proactiveParams = await paramsRes.json();
                }
              } catch (e) {
                console.warn("[ProactiveChat] Failed to fetch params", e);
              }

              // ⚡ Execution
              try {
                await onSendRef.current(instruction, {
                  temperature: proactiveParams.temperature,
                  topP: proactiveParams.top_p,
                  presencePenalty: proactiveParams.presence_penalty,
                  frequencyPenalty: proactiveParams.frequency_penalty,
                });
              } finally {
                isProactiveProcessing.current = false;
              }

              return;
            }
          }
        } catch (e) {
          // console.error("[ProactiveChat] Sync failed", e);
        }
      }
    };

    // Poll every 1s for Signals
    const timer = setInterval(syncState, 1000);
    return () => clearInterval(timer);
  }, [activeCharacterId, isProcessing, isStreaming, backendUrl, onSend]);
};
