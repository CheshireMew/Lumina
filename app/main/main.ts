import { app, BrowserWindow, ipcMain, protocol } from "electron";
import path from "node:path";
import store from "./config_store";
import { llmService } from "../../core/llm/llm_service";
import { pythonSTTService } from "../../core/stt/python_stt_service";
import { isChildOf } from "./safe_fs";

// Initialize LLM Service with stored config
// Initialize LLM Service with stored config or Defaults (Free Tier)
// Initialize LLM Service with stored config or Defaults (Free Tier)
// Initialize LLM Service as Proxy to Python Backend
// [Phase 19] Initialization moved to app.whenReady for dynamic port

// [Fix] Suppress GPU/Skia errors (SharedImageManager::ProduceSkia)
app.commandLine.appendSwitch("enable-gpu-rasterization");
app.commandLine.appendSwitch("ignore-gpu-blacklist");
app.commandLine.appendSwitch("disable-features", "WidgetLayering");
// app.commandLine.appendSwitch("no-sandbox"); // Removed for Security Audit #4
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

// 🚧 Use ['ENV_NAME'] avoid vite:define plugin - Vite@2.x
const VITE_DEV_SERVER_URL = process.env["VITE_DEV_SERVER_URL"];

function createWindow() {
    win = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true, // ✅  Security Audit #4
            nodeIntegration: false, // ✅ Security Audit #4
            sandbox: true, // ✅ Explicitly enabled
        },
    });

    // IPC Handlers
    ipcMain.handle("llm:chat", async (_event, message) => {
        return await llmService.chat(message);
    });

    // 流式聊天 IPC Handler
    ipcMain.on("llm:chatStream", async (event, message: string) => {
        await llmService.chatStream(message, (token: string) => {
            // 每收到一个 token，就通过事件发送给渲染进程
            event.sender.send("llm:streamToken", token);
        });
        // 流结束后发送完成信号
        event.sender.send("llm:streamEnd");
    });

    // Advanced Chat Stream with History
    ipcMain.on("llm:chatStreamWithHistory", async (event, args) => {
        const {
            history,
            userMessage,
            contextWindow,
            summary,
            longTermMemory,
            userName,
            charName,
            role,
            dynamicState,
            enableThinking = false, // ⚡ Destructure with default
            temperature,
            topP,
            presencePenalty,
            frequencyPenalty,
            characterId,
            userId,
        } = args;
        await llmService.chatStreamWithHistory(
            history,
            userMessage,
            contextWindow,
            (token: string) => {
                event.sender.send("llm:streamToken", token);
            },
            summary,
            longTermMemory,
            userName,
            charName,
            role,
            dynamicState, // ✅ Pass to Service
            enableThinking, // ✅ Pass Thinking Mode flag
            temperature,
            topP,
            presencePenalty,
            frequencyPenalty,
            characterId, // [Phase 20]
            userId, // [Phase 20]
        );
        event.sender.send("llm:streamEnd");
    });

    // Summarization IPC
    ipcMain.handle("llm:updateSummary", async (_event, args) => {
        const { currentSummary, newMessages } = args;
        return await llmService.updateSummary(currentSummary, newMessages);
    });

    // System Prompt IPC
    ipcMain.on("llm:setSystemPrompt", (_event, prompt: string) => {
        llmService.setSystemPrompt(prompt);
    });

    ipcMain.handle("settings:get", (_event, key) => {
        return store.get(key);
    });

    ipcMain.handle("settings:set", async (_event, key, value) => {
        const oldValue = store.get(key); // Capture for rollback
        store.set(key, value);

        // [Phase 17] Sync Config to Python Backend
        if (["apiKey", "apiBaseUrl", "modelName"].includes(key)) {
            const syncToBackend = async () => {
                const axios = require("axios");
                const maxRetries = 3;
                let lastError;

                for (let i = 0; i < maxRetries; i++) {
                    try {
                        const apiKey = store.get("apiKey") as string;
                        const baseUrl = store.get("apiBaseUrl") as string;
                        const modelName = store.get("modelName") as string;

                        const memPort =
                            pythonSTTService.getServicePorts()["memory"] ||
                            8010;

                        await axios.post(
                            `http://127.0.0.1:${memPort}/llm-mgmt/providers/custom_provider`,
                            {
                                api_key: apiKey,
                                base_url: baseUrl,
                                models: [modelName],
                            },
                            { timeout: 3000 },
                        );
                        console.log(
                            "[Main] ✅ Synced config to Python Backend",
                        );
                        return; // Success
                    } catch (e: any) {
                        lastError = e;
                        console.warn(
                            `[Main] Sync attempt ${i + 1} failed: ${e.message}`,
                        );
                        await new Promise((r) => setTimeout(r, 1000)); // Wait 1s
                    }
                }

                // If exhausted retries => ROLLBACK
                console.error(
                    "[Main] ❌ Sync failed after retries. Rolling back setting.",
                );
                store.set(key, oldValue); // Revert local state

                // Notify logic (optional, but good for debug)
                throw new Error(
                    `Failed to sync with backend: ${lastError.message}`,
                );
            };

            try {
                await syncToBackend();
            } catch (e) {
                // Return false to indicate failure to frontend
                return false;
            }
        }

        // Re-init LLM (Proxy) if config changes - Just updates internal strings
        if (
            ["apiKey", "apiBaseUrl", "modelName", "llm_temperature"].includes(
                key,
            )
        ) {
            // Just re-init proxy, args ignored
            const memPort =
                pythonSTTService.getServicePorts()["memory"] || 8010;
            llmService.init(
                "proxy-key",
                `http://127.0.0.1:${memPort}`,
                "default",
                0.7,
            );
        }
        return true;
    });

    // Python STT Service - 获取 WebSocket URL
    ipcMain.handle("stt:get-ws-url", () => {
        return pythonSTTService.getWebSocketURL();
    });

    // Get Dynamic Ports
    ipcMain.handle("app:get-ports", () => {
        return pythonSTTService.getServicePorts();
    });

    // [Security] Safe Background Upload
    ipcMain.handle("app:upload-background", async (_event, filePath) => {
        try {
            const fs = require("fs");
            const fsPromises = require("fs/promises");

            // 1. Validate
            if (!fs.existsSync(filePath)) throw new Error("File not found");

            // 2. Prepare Dest
            // [Alignment] Use 'Lumina_Data' in Dev (Portable), 'userData' in Prod
            const dataRoot = !app.isPackaged
                ? path.join(process.cwd(), "Lumina_Data")
                : app.getPath("userData");

            const bgDir = path.join(dataRoot, "backgrounds");
            if (!fs.existsSync(bgDir)) fs.mkdirSync(bgDir, { recursive: true });

            // 3. Generate Safe Name
            const ext = path.extname(filePath);
            const safeName = `bg_${Date.now()}${ext}`;
            const destPath = path.join(bgDir, safeName);

            // 4. Copy
            await fsPromises.copyFile(filePath, destPath);
            console.log(`[Media] Background copied to: ${destPath}`);

            // 5. Return Safe URL
            // Normalize path separators to forward slashes for URL
            const normPath = destPath.replace(/\\/g, "/");
            return `lumina-local://${normPath}`;
        } catch (e) {
            console.error("Failed to upload background:", e);
            throw e;
        }
    });

    // Test active push message to Renderer-process.
    win.webContents.on("did-finish-load", () => {
        win?.webContents.send(
            "main-process-message",
            new Date().toLocaleString(),
        );
    });

    if (VITE_DEV_SERVER_URL) {
        win.loadURL(VITE_DEV_SERVER_URL);
    } else {
        win.loadFile(path.join(process.env.DIST || "", "index.html"));
    }

    // Open the DevTools only in Dev
    if (!app.isPackaged) {
        win.webContents.openDevTools();
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

app.on("will-quit", () => {
    pythonSTTService.stop();
});

app.whenReady().then(async () => {
    // [Fix] Register 'lumina-local' protocol to serve local files
    // Usage: lumina-local://E:/Path/To/File.png
    const { protocol } = require("electron");
    // Types for Protocol Handler
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
                // [Debug] Protocol Trace
                // console.log(`[Protocol] Request: ${request.url}`);

                // Handle both // and /// just in case
                let url = request.url.replace("lumina-local://", "");
                if (url.startsWith("/")) url = url.slice(1); // Remove leading slash if using ///

                const decodedUrl = decodeURI(url);

                const normPath = path.normalize(decodedUrl);

                // console.log(`[Protocol] Normalized Path: ${normPath}`);

                // [Security] White-list allowed directories
                const allowedRoots = [
                    app.getPath("userData"),
                    process.cwd(),
                    app.getPath("temp"),
                ].map((r) => path.normalize(r));

                const isAllowed = allowedRoots.some((root) =>
                    isChildOf(root, normPath),
                );

                if (!isAllowed) {
                    console.error(
                        `🚨 [Security] Blocked unauthorized file access: ${normPath}`,
                    );
                    console.error(`Debug: Roots: ${allowedRoots.join(", ")}`);
                    // Return error code -10 (ERR_ACCESS_DENIED)
                    return callback({ error: -10 });
                }

                return callback({ path: normPath });
            } catch (error) {
                console.error("Failed to register protocol", error);
                return callback({ error: -2 }); // FAILED
            }
        },
    );

    createWindow();
    try {
        console.log("Starting Python Backend...");
        await pythonSTTService.start();

        console.log("Python Backend started.");

        // [Phase 19] Init LLM Service with dynamic port
        const ports = pythonSTTService.getServicePorts();
        const memPort = ports["memory"] || 8010;
        console.log(
            `[Main] Initializing LLM Proxy to http://127.0.0.1:${memPort}`,
        );
        llmService.init(
            "proxy-key",
            `http://127.0.0.1:${memPort}`,
            "default-model",
            0.7,
        );
    } catch (error) {
        console.error("Failed to start Python Backend:", error);
    }
});
