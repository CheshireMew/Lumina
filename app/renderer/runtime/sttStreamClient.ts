import { getSttWebSocketUrl } from "../platform/electron";

export const connectSttStream = async () => {
    const wsUrl = await getSttWebSocketUrl();
    if (!wsUrl) {
        throw new Error("Missing STT WebSocket URL");
    }

    console.info("[STTStream] Connecting STT WebSocket", {
        url: wsUrl.replace(/\?.*$/, "?token=<redacted>"),
    });
    return new WebSocket(wsUrl);
};
