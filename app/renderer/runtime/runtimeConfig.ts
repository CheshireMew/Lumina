import { BackendState } from "../platform/electron";
import configuredPorts from "../../../config/ports.json";

export interface RuntimeConfig {
    apiBaseUrl: string;
    sttBaseUrl: string;
    ttsBaseUrl: string;
    visionBaseUrl: string;
}

export const buildRuntimeConfig = (backendState: BackendState): RuntimeConfig => {
    const apiPort = backendState.ports.memory || configuredPorts.memory_port;
    const apiBaseUrl = `http://127.0.0.1:${apiPort}`;

    return {
        apiBaseUrl,
        sttBaseUrl: `${apiBaseUrl}/capabilities/stt`,
        ttsBaseUrl: `${apiBaseUrl}/capabilities/tts`,
        visionBaseUrl: `${apiBaseUrl}/capabilities/vision`,
    };
};
