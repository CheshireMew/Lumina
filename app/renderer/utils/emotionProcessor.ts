import { CharacterProfile } from "@core/llm/types";
import { Live2DViewerRef } from "../live2d-view/Live2DViewer";
import emotionMapRaw from "../emotion_map.json";

const emotionMap: Record<string, { group: string; index: number }> =
  emotionMapRaw;

import { API_CONFIG } from "../config";

export interface EmotionProcessorOptions {
  activeCharacter: CharacterProfile | undefined;
  live2dRef: React.RefObject<Live2DViewerRef>;
  backendUrl?: string; // Optional, defaults to config base url
}

/**
 * Parses text for emotion tags [emotion] or (emotion) and triggers:
 * 1. Live2D Motions
 * 2. Soul Mutations (Intimacy/Energy)
 */
export const processEmotions = (
  text: string,
  {
    activeCharacter,
    live2dRef,
    backendUrl = API_CONFIG.BASE_URL,
  }: EmotionProcessorOptions
) => {
  console.log("[EmotionProcessor] Processing text:", text);

  // Regex to find all [emotion] tags (and fallback to parens)
  const matches = text.matchAll(/(?:\[([^\]]+)\])|(?:[\(（]([^)）]+)[\)）])/g);
  const matchesArray = Array.from(matches);
  console.log(
    "[EmotionProcessor] Found emotion tag matches:",
    matchesArray.length
  );

  for (const match of matchesArray) {
    // match[1] is [content], match[2] is (content)
    const emotionContent = (match[1] || match[2] || "").trim().toLowerCase();
    console.log(
      "[EmotionProcessor] Processing emotion content:",
      emotionContent
    );

    // ⚡ Check Soul Evolution (Internal State Update) Mode
    let emotionFound = false;

    // ⚡ Logic Separation: Check soulEvolutionEnabled
    if (activeCharacter && activeCharacter.soulEvolutionEnabled === false) {
      console.log(
        "[EmotionProcessor] 🛑 Soul Evolution DISABLED. Skipping state mutation."
      );
      // Still trigger Live2D motions (visuals are fun), just don't mutate stats.
    } else {
      // Define mutation effects
      // [sad]/[angry] -> Energy -1
      // [happy]/[love] -> Intimacy +1
      // [shy]/[hopeful] -> Intimacy +0.5
      let d_energy = 0;
      let d_intimacy = 0;

      if (
        emotionContent.includes("sad") ||
        emotionContent.includes("angry") ||
        emotionContent.includes("depress") ||
        emotionContent.includes("cry")
      ) {
        d_energy = -1;
        d_intimacy = -1; // Negative emotions decrease intimacy
      } else if (
        emotionContent.includes("happy") ||
        emotionContent.includes("love") ||
        emotionContent.includes("joy") ||
        emotionContent.includes("excite")
      ) {
        d_intimacy = 0.5;
        d_energy = 0.2;
      } else if (
        emotionContent.includes("shy") ||
        emotionContent.includes("hope")
      ) {
        d_intimacy = 0.2;
        d_energy = -0.5;
      }

      // Call Backend Mutation API if there is a change
      if (d_energy !== 0 || d_intimacy !== 0) {
        console.log(
          `[EmotionProcessor] 🧬 Mutating Soul: Energy ${d_energy}, Intimacy ${d_intimacy}`
        );
        // Fire and forget, don't block UI
        fetch(
          `${backendUrl}/soul/mutate?pleasure=0&arousal=0&dominance=0&intimacy=${d_intimacy}&energy=${d_energy}`,
          {
            method: "POST",
          }
        ).catch((e) =>
          console.error("[EmotionProcessor] Failed to mutate soul:", e)
        );
      }
    }

    for (const [key, motion] of Object.entries(emotionMap)) {
      if (emotionContent.includes(key)) {
        console.log(
          `[EmotionProcessor] ✅ Triggering emotion: "${key}" -> Motion: ${motion.group} index ${motion.index}`
        );
        if (live2dRef.current) {
          live2dRef.current.motion(motion.group, motion.index);
        } else {
          console.warn("[EmotionProcessor] ⚠️ live2dRef.current is null!");
        }
        emotionFound = true;
        break; // Trigger only one emotion per tag
      }
    }
    if (!emotionFound) {
      console.log(
        `[EmotionProcessor] ❌ No emotion mapping found for: "${emotionContent}"`
      );
    }
  }
};
