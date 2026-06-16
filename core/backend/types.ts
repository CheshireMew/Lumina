import type { ChildProcess } from "child_process";

export interface ServiceConfig {
    name: string;
    port: number;
    type: "python" | "binary";
    binaryPath?: string;
    args?: string[];
    process?: ChildProcess | null;
    ready?: boolean;
    restartCount?: number;
    lastExitTime?: number;
}

export interface BackendPorts {
    memory_port: number;
    stt_port: number;
    tts_port: number;
    [key: string]: number;
}

export const DEFAULT_BACKEND_PORTS: BackendPorts = {
    memory_port: 8010,
    stt_port: 8765,
    tts_port: 8766,
};
