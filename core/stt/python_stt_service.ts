import { spawn, ChildProcess } from "child_process";
import path from "path";
import fs from "fs";
import { app } from "electron";
import axios from "axios";
import net from "net";

interface ServiceConfig {
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

/**
 * Python Backend Service Manager
 * Manages multiple Python backend processes (STT, TTS, Memory) AND SurrealDB
 */
export class PythonSTTService {
    private services: ServiceConfig[] = [
        {
            name: "surreal",
            port: 0, // [Phase 19] Dynamic Load
            type: "binary",
        },
        { name: "memory", port: 0, type: "python" }, // Will load 8010
        { name: "stt", port: 0, type: "python" }, // Will load 8765
        { name: "tts", port: 0, type: "python" }, // Will load 8766
    ];

    private host: string = "127.0.0.1";
    private isShuttingDown: boolean = false;

    /**
     * Start all backend services
     */
    public async start(): Promise<void> {
        console.log("[BackendManager] Starting all services...");

        // Load Dynamic Ports
        this.loadPortsConfig();

        // Start SurrealDB first
        const surreal = this.services.find((s) => s.name === "surreal")!;
        await this.startService(surreal);

        // Start others concurrently
        const others = this.services.filter((s) => s.name !== "surreal");
        const startPromises = others.map((service) =>
            this.startService(service)
        );
        await Promise.all(startPromises);

        console.log("[BackendManager] All services started successfully.");
    }

    private async startService(service: ServiceConfig): Promise<void> {
        // 1. Check if service is already running (Active Port)
        const isPortOpen = await this.isPortInUse(service.port, this.host);
        const isHealthy = await this.checkServiceHealth(service);

        if (isPortOpen) {
            if (isHealthy) {
                console.log(
                    `[BackendManager] Service ${service.name} is already active (Port ${service.port}). Skipping spawn.`
                );
                service.ready = true;
                return;
            } else {
                console.warn(
                    `[BackendManager] ⚠️ Port ${service.port} (${service.name}) is occupied but unresponsive to /health. Skipping spawn to avoid conflict.`
                );
                // We assume it's running but stuck, or another app. We shouldn't conflict.
                service.ready = false;
                return;
            }
        }

        if (service.process) {
            console.log(
                `[BackendManager] Service ${service.name} already running internally`
            );
            return;
        }

        // ... (rest is same)

        let executable: string;
        let args: string[];
        let cwd: string;

        if (app.isPackaged) {
            if (service.type === "binary" && service.name === "surreal") {
                executable = path.join(
                    process.resourcesPath,
                    "bin",
                    "surreal.exe"
                );
                const dbPath = path.join(app.getPath("userData"), "lumina.db");
                // Ensure directory exists? userData always exists.
                // bind to localhost for security in packaged app
                args = [
                    "start",
                    "--log",
                    "info",
                    "--user",
                    "root",
                    "--pass",
                    "root",
                    "--bind",
                    "127.0.0.1:8001",
                    // "--allow-all", // REMOVED for Security: Enforce auth
                    `file:${dbPath}`,
                ];
                cwd = path.dirname(executable); // bin
                console.log(
                    "[BackendManager] Launching packaged SurrealDB:",
                    executable,
                    "DB:",
                    dbPath
                );
            } else {
                // Production: Launch compiled executable
                executable = path.join(
                    process.resourcesPath,
                    "bin",
                    "lumina_backend",
                    "lumina_backend.exe"
                );
                args = [service.name];
                cwd = path.join(process.resourcesPath, "bin", "lumina_backend");
                console.log(
                    `[BackendManager] Launching packaged ${service.name}:`,
                    executable
                );
            }
        } else {
            // Development
            if (service.type === "binary" && service.name === "surreal") {
                // In Dev, we prefer user to run it manually.
                // But if we wanted to auto-start, we'd need 'surreal' in PATH.
                // Let's TRY to find it, or just fail gracefully?
                // Current policy: "Detached Mode" is preferred.
                // If checkHealth failed above, it means it's NOT running.
                console.warn(
                    '[BackendManager] SurrealDB is NOT running on port 8001. Please start it manually: "surreal start ..."'
                );
                // We interrupt startup because app needs it?
                // Or we try to spawn 'surreal' from PATH?
                // Let's try to spawn it implies user has it installed.
                executable = "surreal"; // Hope it's in PATH
                // Use local file in project root for dev
                const dbPath = path.join(process.cwd(), "lumina_surreal.db");
                args = [
                    "start",
                    "--log",
                    "info",
                    "--user",
                    "root",
                    "--pass",
                    "root",
                    "--bind",
                    "127.0.0.1:8001",
                    // "--allow-all",
                    `file:${dbPath}`,
                ];
                cwd = process.cwd();
                console.log(
                    "[BackendManager] Attempting to auto-start SurrealDB in Dev..."
                );
            } else {
                const projectRoot = process.cwd();
                const launcherScript = path.join(
                    projectRoot,
                    "python_backend",
                    "backend_launcher.py"
                );
                // ⚡ Config: Use system python in dev mode, or allow ENV override
                executable = process.env.PYTHON_PATH || "python";
                args = [launcherScript, service.name];
                cwd = path.join(projectRoot, "python_backend");
                console.log(
                    `[BackendManager] Launching dev ${service.name}:`,
                    executable,
                    args,
                    "CWD:",
                    cwd
                );
            }
        }

        const child = spawn(executable!, args!, {
            cwd: cwd!,
            stdio: ["ignore", "pipe", "pipe"],
            shell: false,
            windowsHide: true,
            env: {
                ...process.env,
                LITE_MODE: app.isPackaged ? "true" : "false",
                LUMINA_DATA_PATH: app.getPath("userData"),
                LUMINA_ENV: app.isPackaged ? "production" : "development",
            },
        });

        service.process = child;

        // Logs
        child.stdout?.on("data", (data) => {
            console.log(`[${service.name}] ${data.toString().trim()}`);
            // Surreal doesn't respond to HTTP health check until started?
        });

        child.stderr?.on("data", (data) => {
            console.error(`[${service.name}] ERR: ${data.toString().trim()}`);
        });

        child.on("error", (err) => {
            console.error(`[${service.name}] Failed to spawn:`, err);
            if (service.name === "surreal" && !app.isPackaged) {
                console.error(
                    "[BackendManager] Please install SurrealDB or ensure it is in PATH, or start it manually."
                );
            }
        });

        child.on("exit", (code) => {
            console.log(`[${service.name}] Process exited with code ${code}`);
            service.process = null;
            service.ready = false;

            if (this.isShuttingDown) return;

            if (code !== 0 && code !== null) {
                const now = Date.now();
                // Reset count if last exit was long ago (stable for > 60s)
                if (
                    service.lastExitTime &&
                    now - service.lastExitTime > 60000
                ) {
                    service.restartCount = 0;
                }

                service.restartCount = (service.restartCount || 0) + 1;
                service.lastExitTime = now;

                if (service.restartCount > 5) {
                    console.error(
                        `[${service.name}] 🚨 Crashing too frequently (${service.restartCount} times in <60s). Giving up.`
                    );
                    return;
                }

                const delay = Math.min(
                    1000 * Math.pow(2, service.restartCount),
                    30000
                );
                console.log(
                    `[${service.name}] 🔄 Auto-restarting in ${delay}ms... (Attempt ${service.restartCount})`
                );

                setTimeout(() => {
                    if (!this.isShuttingDown)
                        this.startService(service).catch((e) =>
                            console.error(
                                `[${service.name}] Restart failed:`,
                                e
                            )
                        );
                }, delay);
            }
        });

        // Wait for ready
        await this.waitForServiceReady(service);
    }

    private async checkServiceHealth(service: ServiceConfig): Promise<boolean> {
        try {
            const url = `http://${this.host}:${service.port}/health`;
            await axios.get(url, { timeout: 3000, validateStatus: () => true });
            return true;
        } catch (error) {
            return false;
        }
    }

    private isPortInUse(port: number, host: string): Promise<boolean> {
        return new Promise((resolve) => {
            const socket = new net.Socket();
            socket.setTimeout(500); // Fast check
            socket.on("connect", () => {
                socket.destroy();
                resolve(true); // Port is open
            });
            socket.on("timeout", () => {
                socket.destroy();
                resolve(false); // Timeout usually means firewall or weird state or closed
            });
            socket.on("error", (err: any) => {
                socket.destroy();
                if (err.code === "ECONNREFUSED") {
                    resolve(false);
                } else {
                    resolve(true); // E.g. access denied
                }
            });
            socket.connect(port, host);
        });
    }

    private async waitForServiceReady(
        service: ServiceConfig,
        maxRetries: number = 30
    ): Promise<void> {
        for (let i = 0; i < maxRetries; i++) {
            if (await this.checkServiceHealth(service)) {
                service.ready = true;
                console.log(`[${service.name}] Health check passed`);
                return;
            }
            await new Promise((resolve) => setTimeout(resolve, 1000));
        }
        console.error(`[${service.name}] Failed to start within timeout`);
        throw new Error(`${service.name} failed to start`);
    }

    public stop(): void {
        this.isShuttingDown = true;
        console.log("[BackendManager] Stopping all services...");
        this.services.forEach((service) => {
            if (service.process) {
                try {
                    process.kill(service.process.pid!);
                } catch (e) {
                    /* ignore */
                }
                service.process = null;
                service.ready = false;
            }
        });
    }

    public getWebSocketURL(): string {
        const stt = this.services.find((s) => s.name === "stt");
        const port = stt ? stt.port : 8765;
        return `ws://${this.host}:${port}/ws/stt`;
    }

    public getServicePorts(): Record<string, number> {
        const ports: Record<string, number> = {};
        this.services.forEach((s) => {
            ports[s.name] = s.port;
        });
        return ports;
    }

    private loadPortsConfig() {
        try {
            // In Dev, config is at config/ports.json relative to CWD
            // In Prod, usually resources/config/ports.json or user data
            let configPath = path.join(process.cwd(), "config", "ports.json");

            if (!fs.existsSync(configPath) && app.isPackaged) {
                // If packaged and not in CWD, check resources
                // But strict config means we should look in UserData if we want it writable,
                // or resources if read-only. Ports usually static in prod unless multiple instances.
                // Let's stick to reading from resources/config if packaged.
                configPath = path.join(
                    process.resourcesPath,
                    "config",
                    "ports.json"
                );
            }

            // [Phase 19] Single Source of Truth: Auto-generate if missing
            if (!fs.existsSync(configPath)) {
                console.log(
                    "[BackendManager] ports.json not found. Generating defaults..."
                );
                const defaults = {
                    surreal_port: 8001,
                    memory_port: 8010,
                    stt_port: 8765,
                    tts_port: 8766,
                };
                // Ensure dir exists
                const dir = path.dirname(configPath);
                if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

                fs.writeFileSync(configPath, JSON.stringify(defaults, null, 2));
            }

            // Load strictly
            if (fs.existsSync(configPath)) {
                const data = fs.readFileSync(configPath, "utf-8");
                const ports = JSON.parse(data);

                const updatePort = (name: string, port: number) => {
                    const svc = this.services.find((s) => s.name === name);
                    if (svc && port) svc.port = port;
                };

                if (ports.memory_port) updatePort("memory", ports.memory_port);
                if (ports.stt_port) updatePort("stt", ports.stt_port);
                if (ports.tts_port) updatePort("tts", ports.tts_port);
                if (ports.surreal_port)
                    updatePort("surreal", ports.surreal_port);

                console.log("[BackendManager] Loaded dynamic ports:", ports);
            }
        } catch (e) {
            console.error(
                "[BackendManager] Failed to load/generate ports.json:",
                e
            );
            // Fallback/Crash? For now log error.
            // If ports are 0, services will fail to start or check health correctly.
            // We can fallback to hardcoded safety net here if critical?
            // But user asked for Strict.
        }
    }
}

export const pythonSTTService = new PythonSTTService();
