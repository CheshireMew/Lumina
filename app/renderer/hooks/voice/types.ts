export interface WhisperModelInfo {
    id: string;
    name: string;
    description?: string;
    type?: string;
    active?: boolean;
    download_status?: "idle" | "downloading" | "completed" | "failed";
}

export interface VoiceOption {
    name: string;
    gender: string;
}

export interface AudioDevice {
    index: number;
    name: string;
    channels?: number;
    host_api?: string;
}
