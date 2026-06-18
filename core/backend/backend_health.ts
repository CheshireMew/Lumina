import axios from "axios";
import net from "net";

import type { ServiceConfig } from "./types";

export class BackendHealthProbe {
    constructor(private readonly host: string = "127.0.0.1") {}

    public async checkServiceHealth(service: ServiceConfig): Promise<boolean> {
        try {
            const url = `http://${this.host}:${service.port}/runtime/health`;
            const response = await axios.get(url, {
                timeout: 3000,
                validateStatus: () => true,
            });
            return response.status === 200;
        } catch {
            return false;
        }
    }

    public isPortInUse(port: number): Promise<boolean> {
        return new Promise((resolve) => {
            const socket = new net.Socket();
            socket.setTimeout(500);
            socket.on("connect", () => {
                socket.destroy();
                resolve(true);
            });
            socket.on("timeout", () => {
                socket.destroy();
                resolve(false);
            });
            socket.on("error", (err: NodeJS.ErrnoException) => {
                socket.destroy();
                if (err.code === "ECONNREFUSED") {
                    resolve(false);
                } else {
                    resolve(true);
                }
            });
            socket.connect(port, this.host);
        });
    }

    public canBindPort(port: number): Promise<boolean> {
        return new Promise((resolve) => {
            const server = net.createServer();
            server.once("error", () => {
                resolve(false);
            });
            server.once("listening", () => {
                server.close(() => resolve(true));
            });
            server.listen(port, this.host);
        });
    }

    public async findBindablePort(
        preferredPort: number,
        searchLimit: number = 100,
    ): Promise<number> {
        for (let offset = 0; offset < searchLimit; offset++) {
            const candidate = preferredPort + offset;
            if (await this.canBindPort(candidate)) {
                return candidate;
            }
        }

        throw new Error(
            `No bindable port found from ${preferredPort} to ${preferredPort + searchLimit - 1}`,
        );
    }

    public async waitForServiceReady(
        service: ServiceConfig,
        maxRetries: number = 120,
    ): Promise<void> {
        for (let i = 0; i < maxRetries; i++) {
            if (await this.checkServiceHealth(service)) {
                service.ready = true;
                console.log(`[${service.name}] Health check passed`);
                return;
            }
            await new Promise((resolve) => setTimeout(resolve, 250));
        }
        console.error(`[${service.name}] Failed to start within timeout`);
        throw new Error(`${service.name} failed to start`);
    }
}
