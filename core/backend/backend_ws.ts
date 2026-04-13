import axios from "axios";

import type { BackendPorts } from "./types";

export class BackendWebSocketLocator {
    constructor(private readonly host: string = "127.0.0.1") {}

    public async getSttWebSocketURL(ports: BackendPorts): Promise<string> {
        const basePort = ports.memory_port || 8010;
        await axios.get(`http://${this.host}:${basePort}/stt/models/list`, {
            timeout: 5000,
        });
        const response = await axios.get(
            `http://${this.host}:${basePort}/runtime/capabilities/stt`,
            { timeout: 3000 },
        );
        if (!response.data?.stream_url) {
            throw new Error("STT runtime session unavailable");
        }
        return response.data.stream_url;
    }
}
