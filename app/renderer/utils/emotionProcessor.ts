import { CharacterProfile } from "@core/llm/types";
import emotionMapRaw from "../emotion_map.json";

type Live2DMotionRef = {
    motion?: (group: string, index?: number) => void;
};

const emotionMap =
    emotionMapRaw as unknown as Record<string, { group: string; index: number }>;

export interface EmotionProcessorOptions {
    activeCharacter: CharacterProfile | undefined;
    live2dRef: React.RefObject<Live2DMotionRef>;
}

/**
 * Parses text for emotion tags [emotion] or (emotion) and triggers:
 * 1. Live2D Motions
 */
export const processEmotions = (
    text: string,
    {
        activeCharacter,
        live2dRef,
    }: EmotionProcessorOptions,
) => {
    console.log("[EmotionProcessor] Processing text chars=", text.length);

    // Regex to find all [emotion] tags (and fallback to parens)
    // [Fix] Use Unicode Escapes for full-width brackets to avoid encoding issues
    // \uff08 = （, \uff09 = ）
    const matches = text.matchAll(
        /(?:\[([^\]]+)\])|(?:[\(\uff08]([^)\uff09]+)[\)\uff09])/g,
    );
    const matchesArray = Array.from(matches);
    console.log(
        "[EmotionProcessor] Found emotion tag matches:",
        matchesArray.length,
    );

    for (const match of matchesArray) {
        // match[1] is [content], match[2] is (content)
        const emotionContent = (match[1] || match[2] || "")
            .trim()
            .toLowerCase();
        let emotionFound = false;

        if (activeCharacter && activeCharacter.soulEvolutionEnabled === false) {
            console.log(
                "[EmotionProcessor] Soul evolution disabled. Triggering visual emotion only.",
            );
        }

        for (const [key, motion] of Object.entries(emotionMap)) {
            if (emotionContent.includes(key)) {
                console.log(
                    `[EmotionProcessor] Triggering motion group=${motion.group} index=${motion.index}`,
                );
                if (live2dRef.current) {
                    live2dRef.current.motion?.(motion.group, motion.index);
                } else {
                    console.warn(
                        "[EmotionProcessor] ⚠️ live2dRef.current is null!",
                    );
                }
                emotionFound = true;
                break; // Trigger only one emotion per tag
            }
        }
        if (!emotionFound) {
            console.log("[EmotionProcessor] No emotion mapping found");
        }
    }
};
