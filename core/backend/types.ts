import type { ChildProcess } from "child_process";
import configuredPorts from "../../config/ports.json";

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
    vision_port: number;
    [key: string]: number;
}

export const CONFIGURED_BACKEND_PORTS: BackendPorts = configuredPorts;
