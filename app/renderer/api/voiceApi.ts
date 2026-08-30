import { jsonRequestOptions, requestJson } from "./client";
import type { components } from "../types/api-schema";

type SttModelListResponse = components["schemas"]["SttModelListResponse"];
type AudioDeviceListResponse = components["schemas"]["AudioDeviceListResponse"];
type OperationStatusResponse = components["schemas"]["OperationStatusResponse"];
type UnifiedAudioConfig = components["schemas"]["UnifiedAudioConfig"];
type VoiceprintStatusResponse = components["schemas"]["VoiceprintStatusResponse"];
type AudioStatusResponse = components["schemas"]["AudioStatusResponse"];
type TtsModelListResponse = components["schemas"]["TtsModelListResponse"];
type TtsVoiceInfo = components["schemas"]["TtsVoiceInfo"];

export interface VoiceprintProfile {
    name: string;
    enabled: boolean;
    created_at?: string | number | null;
}

export const listSttModels = (sttBaseUrl: string) =>
    requestJson<SttModelListResponse>(`${sttBaseUrl}/models/list`);

export const listAudioDevices = (sttBaseUrl: string) =>
    requestJson<AudioDeviceListResponse>(`${sttBaseUrl}/audio/devices`);

export const switchSttModel = (sttBaseUrl: string, modelName: string) =>
    requestJson<OperationStatusResponse>(
        `${sttBaseUrl}/models/switch`,
        jsonRequestOptions("POST", { model_name: modelName }),
    );

export const updateSttAudioConfig = (
    sttBaseUrl: string,
    payload: UnifiedAudioConfig,
) =>
    requestJson<OperationStatusResponse>(
        `${sttBaseUrl}/audio/config`,
        jsonRequestOptions("POST", payload),
    );

export const getVoiceprintStatus = (sttBaseUrl: string) =>
    requestJson<VoiceprintStatusResponse>(`${sttBaseUrl}/voiceprint/status`);

export const getAudioStatus = (sttBaseUrl: string) =>
    requestJson<AudioStatusResponse>(`${sttBaseUrl}/audio/status`);

export const listVoiceprintProfiles = (apiBaseUrl: string) =>
    requestJson<{ profiles: VoiceprintProfile[] }>(
        `${apiBaseUrl}/capabilities/voiceprint/list`,
    );

export const toggleVoiceprintProfile = (
    apiBaseUrl: string,
    profileName: string,
    enabled: boolean,
) =>
    requestJson<OperationStatusResponse>(
        `${apiBaseUrl}/capabilities/voiceprint/toggle/${encodeURIComponent(profileName)}?enabled=${enabled}`,
        jsonRequestOptions("POST"),
    );

export const deleteVoiceprintProfile = (
    apiBaseUrl: string,
    profileName: string,
) =>
    requestJson<OperationStatusResponse>(
        `${apiBaseUrl}/capabilities/voiceprint/${encodeURIComponent(profileName)}`,
        jsonRequestOptions("DELETE"),
    );

export const uploadVoiceprintProfile = (
    apiBaseUrl: string,
    profileName: string,
    file: File,
) => {
    const formData = new FormData();
    formData.append("file", file);

    return requestJson<OperationStatusResponse>(
        `${apiBaseUrl}/capabilities/voiceprint/upload?name=${encodeURIComponent(profileName)}`,
        {
            method: "POST",
            body: formData,
        },
    );
};

export const listTtsModels = (ttsBaseUrl: string) =>
    requestJson<TtsModelListResponse>(`${ttsBaseUrl}/models/list`);

export const listTtsVoices = (ttsBaseUrl: string, engine: string) =>
    requestJson<TtsVoiceInfo[]>(
        `${ttsBaseUrl}/voices?engine=${encodeURIComponent(engine)}`,
    );
