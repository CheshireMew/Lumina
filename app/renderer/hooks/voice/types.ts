export interface WhisperModelInfo {
    name: string;
    desc?: string;
    size?: string;
    engine?: string;
    download_status: "idle" | "downloading" | "completed" | "failed";
}

export interface VoiceOption {
    name: string;
    gender: string;
}

export interface AudioDevice {
    index: number;
    name: string;
    channels: number;
}
