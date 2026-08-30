import axios from "axios";

import type { BackendPorts } from "./types";

export class BackendWebSocketLocator {
    constructor(private readonly host: string = "127.0.0.1") {}

    public async getSttWebSocketURL(ports: BackendPorts): Promise<string> {
        const basePort = ports.core_port;
        const response = await axios.get(
            `http://${this.host}:${basePort}/runtime/capabilities/stt`,
            { timeout: 3000 },
        );
        if (response.data?.status !== "ready" || !response.data?.stream_url) {
            throw new Error("语音识别服务尚未就绪，请稍后重试");
        }
        return response.data.stream_url;
    }
}
