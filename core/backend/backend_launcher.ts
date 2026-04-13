import { ChildProcess, spawn } from "child_process";
import fs from "node:fs";
import path from "path";
import { app } from "electron";

import type { BackendPorts, ServiceConfig } from "./types";

interface LaunchSpec {
    executable: string;
    args: string[];
    cwd: string;
}

export class BackendServiceLauncher {
    public launch(
        service: ServiceConfig,
        ports: BackendPorts,
        onExit: (code: number | null) => void,
    ): ChildProcess {
        const spec = this.buildLaunchSpec(service);
        const verboseChildLogs = Boolean(process.env.VITE_DEV_SERVER_URL);
        const child = spawn(spec.executable, spec.args, {
            cwd: spec.cwd,
            stdio: verboseChildLogs
                ? ["ignore", "pipe", "pipe"]
                : "ignore",
            shell: false,
            windowsHide: true,
            env: {
                ...process.env,
                LITE_MODE: app.isPackaged ? "true" : "false",
                LUMINA_DATA_PATH: app.isPackaged
                    ? app.getPath("userData")
                    : path.join(process.cwd(), "Lumina_Data"),
                LUMINA_ENV: app.isPackaged ? "production" : "development",
                LUMINA_MEMORY_PORT: (ports.memory_port || 8010).toString(),
                LUMINA_STT_PORT: (ports.stt_port || 8765).toString(),
                LUMINA_TTS_PORT: (ports.tts_port || 8766).toString(),
                LUMINA_SURREAL_PORT: (ports.surreal_port || 8001).toString(),
            },
        });

        if (verboseChildLogs) {
            child.stdout?.on("data", (data) => {
                console.log(`[${service.name}] ${data.toString().trim()}`);
            });

            child.stderr?.on("data", (data) => {
                console.error(`[${service.name}] ERR: ${data.toString().trim()}`);
            });
        }

        child.on("error", (err) => {
            console.error(`[${service.name}] Failed to spawn:`, err);
            if (service.name === "surreal" && !app.isPackaged) {
                console.error(
                    "[BackendManager] Please install SurrealDB or ensure it is in PATH, or start it manually.",
                );
            }
        });

        child.on("exit", onExit);
        return child;
    }

    private buildLaunchSpec(service: ServiceConfig): LaunchSpec {
        if (app.isPackaged) {
            return this.buildPackagedLaunchSpec(service);
        }
        if (!process.env.VITE_DEV_SERVER_URL) {
            const localBinarySpec = this.buildLocalBinaryLaunchSpec(service);
            if (localBinarySpec) {
                return localBinarySpec;
            }
        }
        return this.buildDevelopmentLaunchSpec(service);
    }

    private buildLocalBinaryLaunchSpec(
        service: ServiceConfig,
    ): LaunchSpec | null {
        if (service.type === "binary" && service.name === "surreal") {
            return null;
        }

        const executable = path.join(
            process.cwd(),
            "dist_backend",
            "lumina_backend",
            "lumina_backend.exe",
        );

        if (!fs.existsSync(executable)) {
            console.warn(
                "[BackendManager] Local backend binary not found. Falling back to Python source startup:",
                executable,
            );
            return null;
        }

        console.log(
            `[BackendManager] Launching local binary ${service.name}:`,
            executable,
        );
        return {
            executable,
            args: [service.name],
            cwd: path.dirname(executable),
        };
    }

    private buildPackagedLaunchSpec(service: ServiceConfig): LaunchSpec {
        if (service.type === "binary" && service.name === "surreal") {
            const executable = path.join(
                process.resourcesPath,
                "bin",
                "surreal.exe",
            );
            const dbPath = path.join(app.getPath("userData"), "lumina.db");
            console.log(
                "[BackendManager] Launching packaged SurrealDB:",
                executable,
                "DB:",
                dbPath,
            );
            return {
                executable,
                args: [
                    "start",
                    "--log",
                    "info",
                    "--user",
                    "root",
                    "--pass",
                    "root",
                    "--bind",
                    "127.0.0.1:8001",
                    `file:${dbPath}`,
                ],
                cwd: path.dirname(executable),
            };
        }

        const executable = path.join(
            process.resourcesPath,
            "bin",
            "lumina_backend",
            "lumina_backend.exe",
        );
        console.log(`[BackendManager] Launching packaged ${service.name}:`, executable);
        return {
            executable,
            args: [service.name],
            cwd: path.join(process.resourcesPath, "bin", "lumina_backend"),
        };
    }

    private buildDevelopmentLaunchSpec(service: ServiceConfig): LaunchSpec {
        if (service.type === "binary" && service.name === "surreal") {
            console.warn(
                '[BackendManager] SurrealDB is NOT running on port 8001. Please start it manually: "surreal start ..."',
            );
            const dbPath = path.join(process.cwd(), "lumina_surreal.db");
            console.log(
                "[BackendManager] Attempting to auto-start SurrealDB in Dev...",
            );
            return {
                executable: "surreal",
                args: [
                    "start",
                    "--log",
                    "info",
                    "--user",
                    "root",
                    "--pass",
                    "root",
                    "--bind",
                    "127.0.0.1:8001",
                    `file:${dbPath}`,
                ],
                cwd: process.cwd(),
            };
        }

        const projectRoot = process.cwd();
        const launcherScript = path.join(
            projectRoot,
            "python_backend",
            "backend_launcher.py",
        );
        const executable = process.env.PYTHON_PATH || "python";
        const args = [launcherScript, service.name];
        const cwd = path.join(projectRoot, "python_backend");
        console.log(
            `[BackendManager] Launching dev ${service.name}:`,
            executable,
            args,
            "CWD:",
            cwd,
        );
        return { executable, args, cwd };
    }
}
