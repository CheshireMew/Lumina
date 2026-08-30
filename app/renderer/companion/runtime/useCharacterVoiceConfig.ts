import { useEffect } from "react";
import { ttsService } from "@core/voice/tts_service";
import type { useCharacterProfile } from "../../hooks/useCharacterProfile";

type ActiveCharacter = ReturnType<
    typeof useCharacterProfile
>["activeCharacter"];

export function useCharacterVoiceConfig(activeCharacter: ActiveCharacter): void {
    useEffect(() => {
        if (!activeCharacter) return;
        ttsService.setDefaultVoice(activeCharacter.voiceConfig.voiceId);
        ttsService.setEngine(activeCharacter.voiceConfig.service);
        ttsService.setProsody(
            activeCharacter.voiceConfig.rate,
            activeCharacter.voiceConfig.pitch,
        );
    }, [activeCharacter]);
}
