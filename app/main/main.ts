import { app, BrowserWindow, ipcMain } from "electron";
import path from "node:path";
import store from "./config_store";
import { llmService } from "../../core/llm/llm_service";
import { pythonSTTService } from "../../core/stt/python_stt_service";

// Initialize LLM Service with stored config
// Initialize LLM Service with stored config or Defaults (Free Tier)
// Initialize LLM Service with stored config or Defaults (Free Tier)
// Initialize LLM Service as Proxy to Python Backend
// We pass the Memory Server Port (8010) as the "baseUrl" for the proxy.
// [Phase 19] Initialization moved to app.whenReady for dynamic port
// const backendUrl = "http://127.0.0.1:8010";
// llmService.init("proxy-key", backendUrl, "default-model", 0.7);

// [Fix] Suppress GPU/Skia errors (SharedImageManager::ProduceSkia)
app.commandLine.appendSwitch("enable-gpu-rasterization");
app.commandLine.appendSwitch("ignore-gpu-blacklist");
app.commandLine.appendSwitch("disable-features", "WidgetLayering");
app.commandLine.appendSwitch("no-sandbox"); // Helper for some GPU contexts
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
            contextIsolation: true, // [Phase 27] Enable Context Isolation
            nodeIntegration: false, // [Phase 27] Disable Node Integration
            // sandbox: true // ⚠️ Cannot enable Sandbox yet if we use certain Node modules in Preload?
            // Actually, if we use 'electron' module in preload (ipcRenderer), sandbox=true is fine in modern electron.
            // But let's start with ContextIsolation as the critical fix.
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
            userId // [Phase 20]
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
        store.set(key, value);

        // [Phase 17] Sync Config to Python Backend
        // When user changes API Key/BaseURL in frontend, push to Backend's LLM Manager
        if (["apiKey", "apiBaseUrl", "modelName"].includes(key)) {
            try {
                const apiKey = store.get("apiKey") as string;
                const baseUrl = store.get("apiBaseUrl") as string;
                const modelName = store.get("modelName") as string;

                // We assume 'custom_provider' or update the active provider?
                // For simplicity, update 'custom_provider' if baseUrl matches openai, else...
                // Or just update the 'custom_provider' generic slot and ensure route uses it.
                // This is tricky without a full UI.
                // Let's TRY to sync to 'custom_provider' for now.

                const axios = require("axios");
                const memPort =
                    pythonSTTService.getServicePorts()["memory"] || 8010;
                await axios.post(
                    `http://127.0.0.1:${memPort}/llm-mgmt/providers/custom_provider`,
                    {
                        api_key: apiKey,
                        base_url: baseUrl,
                        models: [modelName],
                    }
                );

                // Also update route to use custom_provider?
                // await axios.post('http://127.0.0.1:8010/llm-mgmt/routes/chat', {
                //    provider_id: "custom_provider",
                //    model: modelName
                // });

                console.log("[Main] Synced config to Python Backend");
            } catch (e) {
                console.error("[Main] Failed to sync config to backend:", e);
            }
        }

        // Re-init LLM (Proxy) if config changes - Just updates internal strings
        if (
            ["apiKey", "apiBaseUrl", "modelName", "llm_temperature"].includes(
                key
            )
        ) {
            // Just re-init proxy, args ignored
            const memPort =
                pythonSTTService.getServicePorts()["memory"] || 8010;
            llmService.init(
                "proxy-key",
                `http://127.0.0.1:${memPort}`,
                "default",
                0.7
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

    // Test active push message to Renderer-process.
    win.webContents.on("did-finish-load", () => {
        win?.webContents.send(
            "main-process-message",
            new Date().toLocaleString()
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
    createWindow();
    try {
        console.log("Starting Python Backend...");
        await pythonSTTService.start();

        console.log("Python Backend started.");

        // [Phase 19] Init LLM Service with dynamic port
        const ports = pythonSTTService.getServicePorts();
        const memPort = ports["memory"] || 8010;
        console.log(
            `[Main] Initializing LLM Proxy to http://127.0.0.1:${memPort}`
        );
        llmService.init(
            "proxy-key",
            `http://127.0.0.1:${memPort}`,
            "default-model",
            0.7
        );
    } catch (error) {
        console.error("Failed to start Python Backend:", error);
    }
});
