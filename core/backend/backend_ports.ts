import fs from "fs";
import path from "path";
import { app } from "electron";

import {
    BackendPorts,
    CONFIGURED_BACKEND_PORTS,
    ServiceConfig,
} from "./types";

export class BackendPortConfigStore {
    public load(): BackendPorts {
        try {
            const configPath = this.resolveConfigPath();
            this.ensurePackagedConfig(configPath);

            if (fs.existsSync(configPath)) {
                try {
                    const data = JSON.parse(fs.readFileSync(configPath, "utf-8"));
                    console.log("[BackendManager] Loaded ports from:", configPath);
                    return this.normalizePorts(data);
                } catch (e) {
                    console.error("[BackendManager] Failed to parse ports.json:", e);
                }
            } else {
                console.log(
                    "[BackendManager] ports.json not found. Generating defaults...",
                );
                this.writeDefaults(configPath);
            }
        } catch (e) {
            console.error("Failed to load ports config:", e);
        }

        return { ...CONFIGURED_BACKEND_PORTS };
    }

    private normalizePorts(data: Partial<BackendPorts>): BackendPorts {
        const ports = { ...CONFIGURED_BACKEND_PORTS };

        for (const key of Object.keys(ports) as Array<keyof BackendPorts>) {
            const value = data[key];
            if (typeof value === "number") {
                ports[key] = value;
            }
        }

        return ports;
    }

    public applyToServices(services: ServiceConfig[], ports: BackendPorts): void {
        this.updatePort(services, "core", ports.core_port);
        this.updatePort(services, "stt", ports.stt_port);
        this.updatePort(services, "tts", ports.tts_port);

        console.log(
            "[BackendManager] Services Configured:",
            services.map((service) => `${service.name}:${service.port}`),
        );
    }

    private resolveConfigPath(): string {
        if (!app.isPackaged) {
            return path.join(process.cwd(), "config", "ports.json");
        }

        return path.join(app.getPath("userData"), "config", "ports.json");
    }

    private ensurePackagedConfig(configPath: string): void {
        if (!app.isPackaged || fs.existsSync(configPath)) {
            return;
        }

        const templatePath = path.join(
            process.resourcesPath,
            "config",
            "ports.json",
        );
        if (!fs.existsSync(templatePath)) {
            return;
        }

        try {
            const dir = path.dirname(configPath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            fs.copyFileSync(templatePath, configPath);
            console.log("[BackendManager] Initialized ports.json from template.");
        } catch (e) {
            console.error("Failed to copy ports template:", e);
        }
    }

    private writeDefaults(configPath: string): void {
        try {
            const dir = path.dirname(configPath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            fs.writeFileSync(
                configPath,
                JSON.stringify(CONFIGURED_BACKEND_PORTS, null, 2),
            );
            console.log("[BackendManager] Generated ports.json");
        } catch (e) {
            console.error("Failed to write ports.json defaults:", e);
        }
    }

    private updatePort(
        services: ServiceConfig[],
        name: string,
        port: number,
    ): void {
        const service = services.find((item) => item.name === name);
        if (service && port) {
            service.port = port;
        }
    }
}
