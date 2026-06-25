import { jsonRequestOptions, requestJson } from "./client";

export interface VoiceprintProfile {
    name: string;
    enabled: boolean;
    created_at?: string | number | null;
}

export const listSttModels = (sttBaseUrl: string) =>
    requestJson<any>(`${sttBaseUrl}/models/list`);

export const listAudioDevices = (sttBaseUrl: string) =>
    requestJson<any>(`${sttBaseUrl}/audio/devices`);

export const switchSttModel = (sttBaseUrl: string, modelName: string) =>
    requestJson<any>(
        `${sttBaseUrl}/models/switch`,
        jsonRequestOptions("POST", { model_name: modelName }),
    );

export const updateSttAudioConfig = (
    sttBaseUrl: string,
    payload: Record<string, unknown>,
) =>
    requestJson<any>(
        `${sttBaseUrl}/audio/config`,
        jsonRequestOptions("POST", payload),
    );

export const getVoiceprintStatus = (sttBaseUrl: string) =>
    requestJson<any>(`${sttBaseUrl}/voiceprint/status`);

export const getAudioStatus = (sttBaseUrl: string) =>
    requestJson<any>(`${sttBaseUrl}/audio/status`);

export const listVoiceprintProfiles = (apiBaseUrl: string) =>
    requestJson<{ profiles: VoiceprintProfile[] }>(
        `${apiBaseUrl}/capabilities/voiceprint/list`,
    );

export const toggleVoiceprintProfile = (
    apiBaseUrl: string,
    profileName: string,
    enabled: boolean,
) =>
    requestJson<any>(
        `${apiBaseUrl}/capabilities/voiceprint/toggle/${encodeURIComponent(profileName)}?enabled=${enabled}`,
        jsonRequestOptions("POST"),
    );

export const deleteVoiceprintProfile = (
    apiBaseUrl: string,
    profileName: string,
) =>
    requestJson<any>(
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

    return requestJson<any>(
        `${apiBaseUrl}/capabilities/voiceprint/upload?name=${encodeURIComponent(profileName)}`,
        {
            method: "POST",
            body: formData,
        },
    );
};

export const listTtsModels = (ttsBaseUrl: string) =>
    requestJson<any>(`${ttsBaseUrl}/models/list`);

export const listTtsVoices = (ttsBaseUrl: string) =>
    requestJson<any[]>(`${ttsBaseUrl}/voices`);
