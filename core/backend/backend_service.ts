import axios from "axios";

import { BackendHealthProbe } from "./backend_health";
import { BackendServiceLauncher } from "./backend_launcher";
import { BackendPortConfigStore } from "./backend_ports";
import {
    BackendPorts,
    DEFAULT_BACKEND_PORTS,
    ServiceConfig,
} from "./types";
import { BackendWebSocketLocator } from "./backend_ws";

export class BackendService {
    private services: ServiceConfig[] = [
        { name: "core", port: 0, type: "python" },
    ];

    private ports: BackendPorts = { ...DEFAULT_BACKEND_PORTS };
    private readonly host = "127.0.0.1";
    private isShuttingDown = false;
    private readonly portStore = new BackendPortConfigStore();
    private readonly health = new BackendHealthProbe(this.host);
    private readonly launcher = new BackendServiceLauncher();
    private readonly wsLocator = new BackendWebSocketLocator(this.host);

    public async start(): Promise<void> {
        console.log("[BackendManager] Starting all services...");
        this.ports = this.portStore.load();
        this.portStore.applyToServices(this.services, this.ports);
        await this.resolveLaunchPorts();

        await Promise.all(
            this.services.map((service) => this.startService(service)),
        );

        const failedServices = this.services.filter((service) => !service.ready);
        if (failedServices.length > 0) {
            throw new Error(
                `Backend services not ready: ${failedServices
                    .map((service) => `${service.name}:${service.port}`)
                    .join(", ")}`,
            );
        }

        console.log("[BackendManager] All services started successfully.");
    }

    private async resolveLaunchPorts(): Promise<void> {
        for (const service of this.services) {
            if (await this.health.checkServiceHealth(service)) {
                continue;
            }

            if (await this.health.canBindPort(service.port)) {
                continue;
            }

            const previousPort = service.port;
            const nextPort = await this.health.findBindablePort(previousPort + 1);
            service.port = nextPort;

            if (service.name === "core") {
                this.ports.memory_port = nextPort;
            }

            console.warn(
                `[BackendManager] Port ${previousPort} for ${service.name} is not bindable. Using ${nextPort} for this session.`,
            );
        }
    }

    private async startService(service: ServiceConfig): Promise<void> {
        const isPortOpen = await this.health.isPortInUse(service.port);
        const isHealthy = await this.health.checkServiceHealth(service);

        if (isPortOpen) {
            if (isHealthy) {
                console.log(
                    `[BackendManager] Service ${service.name} is already active (Port ${service.port}). Skipping spawn.`,
                );
                service.ready = true;
                return;
            }

            console.warn(
                `[BackendManager] Port ${service.port} (${service.name}) is occupied but unresponsive to /runtime/health. Skipping spawn to avoid conflict.`,
            );
            service.ready = false;
            return;
        }

        if (service.process) {
            console.log(
                `[BackendManager] Service ${service.name} already running internally`,
            );
            return;
        }

        service.process = this.launcher.launch(service, this.ports, (code) => {
            this.handleServiceExit(service, code);
        });

        await this.health.waitForServiceReady(service);
    }

    private handleServiceExit(service: ServiceConfig, code: number | null): void {
        console.log(`[${service.name}] Process exited with code ${code}`);
        service.process = null;
        service.ready = false;

        if (this.isShuttingDown || code === 0 || code === null) {
            return;
        }

        const now = Date.now();
        if (service.lastExitTime && now - service.lastExitTime > 60000) {
            service.restartCount = 0;
        }

        service.restartCount = (service.restartCount || 0) + 1;
        service.lastExitTime = now;

        if (service.restartCount > 5) {
            console.error(
                `[${service.name}] Crashing too frequently (${service.restartCount} times in <60s). Giving up.`,
            );
            return;
        }

        const delay = Math.min(
            1000 * Math.pow(2, service.restartCount),
            30000,
        );
        console.log(
            `[${service.name}] Auto-restarting in ${delay}ms... (Attempt ${service.restartCount})`,
        );

        setTimeout(() => {
            if (!this.isShuttingDown) {
                this.startService(service).catch((e) =>
                    console.error(`[${service.name}] Restart failed:`, e),
                );
            }
        }, delay);
    }

    public stop(): void {
        this.isShuttingDown = true;
        console.log("[BackendManager] Stopping all services...");
        this.services.forEach((service) => {
            if (!service.process) {
                return;
            }

            try {
                if (service.process.pid) {
                    process.kill(service.process.pid);
                }
            } catch {
                /* ignore */
            }
            service.process = null;
            service.ready = false;
        });
    }

    public async getWebSocketURL(): Promise<string> {
        return this.wsLocator.getSttWebSocketURL(this.ports);
    }

    public getServicePorts(): Record<string, number> {
        const ports: Record<string, number> = {};
        this.services.forEach((service) => {
            ports[service.name] = service.port;
        });

        if (!ports.memory && this.ports.memory_port) {
            ports.memory = this.ports.memory_port;
        }
        if (!ports.stt && this.ports.stt_port) {
            ports.stt = this.ports.stt_port;
        }
        if (!ports.tts && this.ports.tts_port) {
            ports.tts = this.ports.tts_port;
        }

        return ports;
    }

    public async refreshPortsFromAPI(): Promise<boolean> {
        try {
            const basePort = this.ports.memory_port || 8010;
            const response = await axios.get(
                `http://${this.host}:${basePort}/runtime/network`,
                { timeout: 3000 },
            );

            if (response.data) {
                const apiPorts = response.data;
                this.ports = {
                    ...this.ports,
                    memory_port: apiPorts.memory_port,
                    stt_port: apiPorts.stt_port,
                    tts_port: apiPorts.tts_port,
                };

                this.services.forEach((service) => {
                    if (service.name === "core") {
                        service.port = apiPorts.memory_port;
                    }
                });

                console.log(
                    "[BackendManager] Ports refreshed from API:",
                    this.ports,
                );
                return true;
            }
        } catch (e) {
            console.warn(
                "[BackendManager] API port refresh failed, using file config:",
                e,
            );
        }
        return false;
    }
}

export const backendService = new BackendService();
