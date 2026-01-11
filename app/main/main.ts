import { app, BrowserWindow, ipcMain } from "electron";
import path from "node:path";
import store from "./config_store";
import { llmService } from "../../core/llm/llm_service";
import { pythonSTTService } from "../../core/stt/python_stt_service";

// Initialize LLM Service with stored config
// Initialize LLM Service with stored config or Defaults (Free Tier)
// Initialize LLM Service with stored config or Defaults (Free Tier)
const storedApiKey = store.get("apiKey") as string;
let storedBaseUrl = store.get("apiBaseUrl") as string;

// ⚡ STRICT MIGRATION: Auto-fix stale port 8001 or localhost issues
if (
  !storedBaseUrl ||
  storedBaseUrl.includes("8001") ||
  storedBaseUrl.includes("localhost") ||
  storedBaseUrl.includes("/free-llm")
) {
  console.log("[Main] Detected stale/ipv6 URL. Enforcing IPv4 + Port 8010...");
  storedBaseUrl = "http://127.0.0.1:8010/v1";
  store.set("apiBaseUrl", storedBaseUrl); // Persist constraint
}

const apiKey = storedApiKey || "sk-free-demo";
const apiBaseUrl = storedBaseUrl;
const modelName = (store.get("modelName") as string) || "free_tier";
const temperature = (store.get("llm_temperature") as number) || 0.7;

// Always initialize to prevent 'Chat model not initialized' error
llmService.init(apiKey, apiBaseUrl, modelName, temperature);

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
      frequencyPenalty
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

  ipcMain.handle("settings:set", (_event, key, value) => {
    store.set(key, value);
    // Re-init LLM if config changes
    if (
      ["apiKey", "apiBaseUrl", "modelName", "llm_temperature"].includes(key)
    ) {
      const newApiKey = store.get("apiKey") as string;
      const newBaseUrl = store.get("apiBaseUrl") as string;
      const newModelName = store.get("modelName") as string;
      const newTemp = (store.get("llm_temperature") as number) || 0.7;
      if (newApiKey) {
        llmService.init(newApiKey, newBaseUrl, newModelName, newTemp);
      }
    }
    return true;
  });

  // Python STT Service - 获取 WebSocket URL
  ipcMain.handle("stt:get-ws-url", () => {
    return pythonSTTService.getWebSocketURL();
  });

  // Test active push message to Renderer-process.
  win.webContents.on("did-finish-load", () => {
    win?.webContents.send("main-process-message", new Date().toLocaleString());
  });

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    win.loadFile(path.join(process.env.DIST || "", "index.html"));
  }

  // Open the DevTools.
  win.webContents.openDevTools();
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
  } catch (error) {
    console.error("Failed to start Python Backend:", error);
  }
});
