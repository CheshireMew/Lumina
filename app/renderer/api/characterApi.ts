import { CharacterProfile } from "@core/llm/types";
import type { components } from "../types/api-schema";

import { jsonRequestOptions, requestJson } from "./client";

type CharacterConfigDto = components["schemas"]["CharacterConfig"];
export type CharacterAvatarModel = components["schemas"]["CharacterAvatarModel"];
type CharacterModelListResponse = components["schemas"]["CharacterModelListResponse"];

const normalizeCharacter = (value: CharacterConfigDto): CharacterProfile => {
    const avatar = value.avatar;
    const behavior = avatar?.behavior;
    const parameters = behavior?.parameters;
    const voiceConfig = value.voiceConfig;
    if (!avatar || !behavior || !parameters || !voiceConfig) {
        throw new Error("Backend returned an incomplete character configuration");
    }

    return {
        id: value.id,
        name: value.name,
        displayName: value.displayName ?? value.name,
        description: value.description,
        systemPrompt: value.systemPrompt,
        avatar: {
            type: "live2d",
            model: avatar.model,
            modelUrl: avatar.modelUrl,
            cubismCoreUrl: avatar.cubismCoreUrl,
            rendererRuntimeUrl: avatar.rendererRuntimeUrl,
            behavior: { ...behavior, parameters },
        },
        voiceConfig,
        heartbeatEnabled: value.heartbeatEnabled,
        proactiveChatEnabled: value.proactiveChatEnabled,
        soulEvolutionEnabled: value.soulEvolutionEnabled,
        proactiveThresholdMinutes: value.proactiveThresholdMinutes,
        metadata: value.metadata || {},
    };
};

const toCharacterDto = (character: CharacterProfile): CharacterConfigDto => ({
    ...character,
    displayName: character.displayName ?? character.name,
    description: character.description || "",
    systemPrompt: character.systemPrompt || "",
    avatar: character.avatar,
    voiceConfig: character.voiceConfig,
    heartbeatEnabled: character.heartbeatEnabled ?? true,
    proactiveChatEnabled: character.proactiveChatEnabled ?? true,
    soulEvolutionEnabled: character.soulEvolutionEnabled ?? true,
    proactiveThresholdMinutes: character.proactiveThresholdMinutes ?? 15,
    metadata: character.metadata || {},
});

export const fetchCharacterConfig = async (baseUrl: string) =>
    normalizeCharacter(
        await requestJson<CharacterConfigDto>(`${baseUrl}/settings/character/config`),
    );

export const listCharacterModels = (baseUrl: string) =>
    requestJson<CharacterModelListResponse>(
        `${baseUrl}/settings/character/models`,
    );

export const updateCharacterConfig = (
    baseUrl: string,
    character: CharacterProfile,
) =>
    requestJson<CharacterConfigDto>(
        `${baseUrl}/settings/character/config`,
        jsonRequestOptions("POST", toCharacterDto(character)),
    ).then(normalizeCharacter);
