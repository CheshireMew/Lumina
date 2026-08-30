import { app, BrowserWindow, ipcMain, protocol, shell } from "electron";
import path from "node:path";
import store from "./config_store";
import { backendService } from "../../core/backend/backend_service";
import { isChildOf } from "./safe_fs";
import type {
    BackendState,
    BackendStatus,
    BootstrapState,
} from "../shared/electronBridge";
import { DEFAULT_USER_NAME } from "../shared/productDefaults";

// Runtime initialization moved to app.whenReady so ports and local protocols are ready first.

// [Fix] Suppress GPU/Skia errors (SharedImageManager::ProduceSkia)
app.commandLine.appendSwitch("enable-gpu-rasterization");
app.commandLine.appendSwitch("ignore-gpu-blacklist");
app.commandLine.appendSwitch("disable-features", "WidgetLayering");
app.commandLine.appendSwitch("disable-gpu-process-crash-limit");

// The built directory structure
process.env.DIST = path.join(__dirname, "../dist");
process.env.VITE_PUBLIC = app.isPackaged
    ? process.env.DIST
    : path.join(process.env.DIST, "../public");

// Disable security warnings in development
if (!app.isPackaged) {
    process.env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true";
}

let win: BrowserWindow | null;
let shutdownComplete = false;
let shutdownStarted = false;
let backendStartPromise: Promise<void> | null = null;

let backendState: BackendState = {
    status: "starting",
    ports: {},
};

const VITE_DEV_SERVER_URL = process.env["VITE_DEV_SERVER_URL"];

function getBootstrapState(): BootstrapState {
    return {
        backend: backendState,
        localSettings: {
            backgroundImage: store.get("backgroundImage") || "",
            isTTSEnabled: store.get("isTTSEnabled") ?? true,
            live2dHighDpi: store.get("live2d_high_dpi") ?? false,
            userName: store.get("userName") || DEFAULT_USER_NAME,
        },
    };
}

function registerIpcHandlers() {
    ipcMain.removeHandler("settings:get");
    ipcMain.handle("settings:get", async (_event, key) => {
        return store.get(key);
    });

    ipcMain.removeHandler("settings:set");
    ipcMain.handle("settings:set", async (_event, key, value) => {
        store.set(key, value);
        return true;
    });

    ipcMain.removeHandler("stt:get-ws-url");
    ipcMain.handle("stt:get-ws-url", async () => {
        return await backendService.getWebSocketURL();
    });

    ipcMain.removeHandler("app:get-bootstrap-state");
    ipcMain.handle("app:get-bootstrap-state", () => {
        return getBootstrapState();
    });

    ipcMain.removeHandler("app:upload-background");
    ipcMain.handle("app:upload-background", async (_event, filePath) => {
        try {
            const fs = require("fs");
            const fsPromises = require("fs/promises");

            if (!fs.existsSync(filePath)) throw new Error("File not found");

            const dataRoot = !app.isPackaged
                ? path.join(process.cwd(), "Lumina_Data")
                : app.getPath("userData");

            const bgDir = path.join(dataRoot, "backgrounds");
            if (!fs.existsSync(bgDir)) fs.mkdirSync(bgDir, { recursive: true });

            const ext = path.extname(filePath);
            const safeName = `bg_${Date.now()}${ext}`;
            const destPath = path.join(bgDir, safeName);

            await fsPromises.copyFile(filePath, destPath);
            console.log(`[Media] Background copied to: ${destPath}`);

            const normPath = destPath.replace(/\\/g, "/");
            return `lumina-local://${normPath}`;
        } catch (e) {
            console.error("Failed to upload background:", e);
            throw e;
        }
    });

    ipcMain.removeHandler("app:retry-backend");
    ipcMain.handle("app:retry-backend", async () => {
        await startBackend(true);
        return backendState;
    });

    ipcMain.removeHandler("app:open-logs");
    ipcMain.handle("app:open-logs", async () => {
        const dataRoot = app.isPackaged
            ? app.getPath("userData")
            : path.join(process.cwd(), "Lumina_Data");
        const logsPath = path.join(dataRoot, "logs");
        const error = await shell.openPath(logsPath);
        if (error) throw new Error(error);
        return logsPath;
    });

    ipcMain.removeHandler("app:open-external");
    ipcMain.handle("app:open-external", async (_event, rawUrl) => {
        const url = new URL(String(rawUrl));
        if (!["http:", "https:"].includes(url.protocol)) {
            throw new Error("Unsupported link protocol");
        }
        await shell.openExternal(url.toString());
    });
}

function syncBackendState(status: BackendStatus, errorMessage?: string) {
    backendState = {
        status,
        ports: backendService.getServicePorts(),
        errorMessage,
    };

    if (win && !win.isDestroyed() && !win.webContents.isDestroyed()) {
        win.webContents.send("app:backend-state", backendState);
    }
}

function registerLocalProtocol() {
    interface ProtocolRequest {
        url: string;
        [key: string]: any;
    }

    protocol.registerFileProtocol(
        "lumina-local",
        (
            request: ProtocolRequest,
            callback: (
                response: string | { path: string } | { error: number },
            ) => void,
        ) => {
            try {
                let url = request.url.replace("lumina-local://", "");
                if (url.startsWith("/")) url = url.slice(1);

                const decodedUrl = decodeURI(url);
                const normPath = path.normalize(decodedUrl);

                const allowedRoots = [
                    app.getPath("userData"),
                    process.cwd(),
                    app.getPath("temp"),
                ].map((root) => path.normalize(root));

                const isAllowed = allowedRoots.some((root) =>
                    isChildOf(root, normPath),
                );

                if (!isAllowed) {
                    console.error(
                        `🚨 [Security] Blocked unauthorized file access: ${normPath}`,
                    );
                    console.error(`Debug: Roots: ${allowedRoots.join(", ")}`);
                    return callback({ error: -10 });
                }

                return callback({ path: normPath });
            } catch (error) {
                console.error("Failed to register protocol", error);
                return callback({ error: -2 });
            }
        },
    );
}

function openDetachedDevTools(target: BrowserWindow) {
    if (!VITE_DEV_SERVER_URL || target.isDestroyed()) {
        return;
    }

    const tryOpen = () => {
        if (target.isDestroyed() || target.webContents.isDestroyed()) {
            return;
        }

        if (target.webContents.isDevToolsOpened()) {
            return;
        }

        try {
            target.webContents.openDevTools({ mode: "detach" });
        } catch (error) {
            console.warn("[DevTools] Failed to open detached window:", error);
        }
    };

    target.webContents.once("dom-ready", tryOpen);
    target.webContents.once("did-finish-load", tryOpen);
    setTimeout(tryOpen, 1500);
    setTimeout(tryOpen, 4000);
}

function createWindow() {
    win = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 960,
        minHeight: 640,
        show: false,
        backgroundColor: "#eef2ff",
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true, // ✅  Security Audit #4
            nodeIntegration: false, // ✅ Security Audit #4
            sandbox: true,
        },
    });

    // Test active push message to Renderer-process.
    win.webContents.on("did-finish-load", () => {
        win?.webContents.send(
            "main-process-message",
            new Date().toLocaleString(),
        );
        syncBackendState(backendState.status, backendState.errorMessage);
    });

    let hasShownWindow = false;
    const showWindow = () => {
        if (hasShownWindow || !win || win.isDestroyed()) {
            return;
        }

        hasShownWindow = true;
        win.show();
    };

    const loadRenderer = async () => {
        if (!win || win.isDestroyed()) {
            return;
        }

        if (VITE_DEV_SERVER_URL) {
            await win.loadURL(VITE_DEV_SERVER_URL);
        } else {
            await win.loadFile(path.join(process.env.DIST || "", "index.html"));
        }
    };

    void loadRenderer();

    win.once("ready-to-show", showWindow);
    win.webContents.once("did-finish-load", showWindow);
    setTimeout(showWindow, 1200);

    openDetachedDevTools(win);
}

async function startBackend(forceRetry = false) {
    if (backendStartPromise) return backendStartPromise;
    backendStartPromise = (async () => {
        syncBackendState("starting");
        try {
            console.log("Starting backend runtime...");
            if (forceRetry) await backendService.retryStart();
            else await backendService.start();
            console.log("Backend runtime started.");
            syncBackendState("ready");
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            console.error("Failed to start backend runtime:", error);
            syncBackendState("error", errorMessage);
        }
    })();
    try {
        await backendStartPromise;
    } finally {
        backendStartPromise = null;
    }
}

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
        win = null;
    }
});

app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on("before-quit", (event) => {
    if (shutdownComplete) {
        return;
    }
    event.preventDefault();
    if (shutdownStarted) {
        return;
    }
    shutdownStarted = true;
    void backendService.stop().finally(() => {
        shutdownComplete = true;
        app.quit();
    });
});

app.whenReady().then(async () => {
    registerIpcHandlers();
    registerLocalProtocol();
    createWindow();
    void startBackend();
});
