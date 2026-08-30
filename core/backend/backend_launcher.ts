import { ChildProcess, spawn } from "child_process";
import path from "path";
import { app } from "electron";

import type { BackendPorts, ServiceConfig } from "./types";

interface LaunchSpec {
    executable: string;
    args: string[];
    cwd: string;
    appRoot: string;
    resourcesDir: string;
    assetsDir: string;
}

export class BackendServiceLauncher {
    constructor(private readonly runtimeOwnerId: string) {}

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
                LUMINA_APP_ROOT: spec.appRoot,
                LUMINA_RESOURCES_DIR: spec.resourcesDir,
                LUMINA_DATA_PATH: app.isPackaged
                    ? app.getPath("userData")
                    : path.join(process.cwd(), "Lumina_Data"),
                LUMINA_ENV: app.isPackaged ? "production" : "development",
                LUMINA_ASSETS_DIR: spec.assetsDir,
                LUMINA_RUNTIME_OWNER: this.runtimeOwnerId,
                LUMINA_RUNTIME_TARGET: service.name,
                LUMINA_PARENT_PID: process.pid.toString(),
                LUMINA_CORE_PORT: ports.core_port.toString(),
                LUMINA_STT_PORT: ports.stt_port.toString(),
                LUMINA_TTS_PORT: ports.tts_port.toString(),
                LUMINA_VISION_PORT: ports.vision_port.toString(),
            },
        });

        if (verboseChildLogs) {
            child.stdout?.on("data", (data) => {
                this.logChildOutput(service.name, data.toString(), false);
            });

            child.stderr?.on("data", (data) => {
                this.logChildOutput(service.name, data.toString(), true);
            });
        }

        child.on("error", (err) => {
            console.error(`[${service.name}] Failed to spawn:`, err);
        });

        child.on("exit", onExit);
        return child;
    }

    private buildLaunchSpec(service: ServiceConfig): LaunchSpec {
        if (app.isPackaged) {
            return this.buildPackagedLaunchSpec(service);
        }
        return this.buildDevelopmentLaunchSpec(service);
    }

    private logChildOutput(
        serviceName: string,
        output: string,
        isError: boolean,
    ): void {
        for (const line of output.split(/\r?\n/)) {
            const trimmed = line.trim();
            if (!trimmed) {
                continue;
            }

            const prefix = isError
                ? `[${serviceName}] ERR:`
                : `[${serviceName}]`;
            const writer = isError ? console.error : console.log;
            writer(`${prefix} ${trimmed}`);
        }
    }

    private buildPackagedLaunchSpec(service: ServiceConfig): LaunchSpec {
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
            appRoot: process.resourcesPath,
            resourcesDir: process.resourcesPath,
            assetsDir: path.join(process.resourcesPath, "bin", "lumina_backend", "_internal", "assets"),
        };
    }

    private buildDevelopmentLaunchSpec(service: ServiceConfig): LaunchSpec {
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
        return {
            executable,
            args,
            cwd,
            appRoot: projectRoot,
            resourcesDir: projectRoot,
            assetsDir: path.join(projectRoot, "public"),
        };
    }
}
