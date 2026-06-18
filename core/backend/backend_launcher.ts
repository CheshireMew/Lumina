import { ChildProcess, spawn } from "child_process";
import fs from "node:fs";
import path from "path";
import { app } from "electron";

import type { BackendPorts, ServiceConfig } from "./types";

interface LaunchSpec {
    executable: string;
    args: string[];
    cwd: string;
    appRoot: string;
    assetsDir: string;
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
                LUMINA_APP_ROOT: spec.appRoot,
                LUMINA_DATA_PATH: app.isPackaged
                    ? app.getPath("userData")
                    : path.join(process.cwd(), "Lumina_Data"),
                LUMINA_ENV: app.isPackaged ? "production" : "development",
                LUMINA_ASSETS_DIR: spec.assetsDir,
                LUMINA_MEMORY_PORT: (ports.memory_port || 8010).toString(),
                LUMINA_STT_PORT: (ports.stt_port || 8765).toString(),
                LUMINA_TTS_PORT: (ports.tts_port || 8766).toString(),
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
            appRoot: process.cwd(),
            assetsDir: path.join(path.dirname(executable), "_internal", "assets"),
        };
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
            assetsDir: path.join(projectRoot, "public"),
        };
    }
}
