import { CharacterProfile } from "@core/llm/types";

import { jsonRequestOptions, requestJson } from "./client";

export interface CharacterAvatarModel {
    name: string;
    path: string;
    type: string;
    thumbnail?: string | null;
    availability?: string;
}

export const fetchCharacterConfig = (baseUrl: string) =>
    requestJson<CharacterProfile>(`${baseUrl}/settings/character/config`);

export const listCharacterModels = (baseUrl: string) =>
    requestJson<{ models: CharacterAvatarModel[] }>(
        `${baseUrl}/settings/character/models`,
    );

export const updateCharacterConfig = (
    baseUrl: string,
    character: CharacterProfile,
) =>
    requestJson<CharacterProfile>(
        `${baseUrl}/settings/character/config`,
        jsonRequestOptions("POST", character),
    );
