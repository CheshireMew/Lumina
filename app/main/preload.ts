import { ipcRenderer, contextBridge } from "electron";

// --------- Expose some API to the Renderer process ---------
// [Phase 27 Security Hardening] Removed raw ipcRenderer exposure
// Only use typed APIs below (llm, settings, etc.)

// LLM API
contextBridge.exposeInMainWorld("llm", {
  // Basic Chat
  chat: (message: string) => ipcRenderer.invoke("llm:chat", message),

  // Stream Chat (Simple)
  chatStream: (message: string) => ipcRenderer.send("llm:chatStream", message),

  // Stream Chat with History (Advanced)
  chatStreamWithHistory: (
    history: any[],
    userMessage: string,
    contextWindow: number,
    summary?: string,
    longTermMemory?: string,
    userName?: string,
    charName?: string,
    role: "user" | "system" = "user",
    dynamicState: string = "",
    enableThinking?: boolean,
    temperature?: number,
    topP?: number,
    presencePenalty?: number,
    frequencyPenalty?: number,
    characterId?: string,
    userId?: string
  ) =>
    ipcRenderer.send("llm:chatStreamWithHistory", {
      history,
      userMessage,
      contextWindow,
      summary,
      longTermMemory,
      userName,
      charName,
      role,
      dynamicState,
      enableThinking,
      temperature,
      topP,
      presencePenalty,
      frequencyPenalty,
      characterId,
      userId,
    }),

  // Summarization
  updateSummary: (currentSummary: string, newMessages: any[]) =>
    ipcRenderer.invoke("llm:updateSummary", { currentSummary, newMessages }),

  // System Prompt
  setSystemPrompt: (prompt: string) =>
    ipcRenderer.send("llm:setSystemPrompt", prompt),

  // Stream Listeners
  onStreamToken: (callback: (token: string) => void) => {
    // Remove existing listener to avoid duplicates if re-registered
    ipcRenderer.removeAllListeners("llm:streamToken");
    ipcRenderer.on("llm:streamToken", (_event, token) => callback(token));
  },
  onStreamEnd: (callback: () => void) => {
    ipcRenderer.removeAllListeners("llm:streamEnd");
    ipcRenderer.on("llm:streamEnd", () => callback());
  },
  removeStreamListeners: () => {
    ipcRenderer.removeAllListeners("llm:streamToken");
    ipcRenderer.removeAllListeners("llm:streamEnd");
  },
});

// Settings API
contextBridge.exposeInMainWorld("settings", {
  get: (key: string) => ipcRenderer.invoke("settings:get", key),
  set: (key: string, value: any) =>
    ipcRenderer.invoke("settings:set", key, value),
});

// STT API
contextBridge.exposeInMainWorld("stt", {
  getWSUrl: () => ipcRenderer.invoke("stt:get-ws-url"),
});

contextBridge.exposeInMainWorld("app", {
  getPorts: () => ipcRenderer.invoke("app:get-ports"),
});
