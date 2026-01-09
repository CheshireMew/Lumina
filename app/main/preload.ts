import { ipcRenderer, contextBridge } from 'electron'

// --------- Expose some API to the Renderer process ---------
contextBridge.exposeInMainWorld('ipcRenderer', {
    on(...args: Parameters<typeof ipcRenderer.on>) {
        const [channel, listener] = args
        return ipcRenderer.on(channel, (event, ...args) => listener(event, ...args))
    },
    off(...args: Parameters<typeof ipcRenderer.off>) {
        const [channel, ...omit] = args
        return ipcRenderer.off(channel, ...omit)
    },
    send(...args: Parameters<typeof ipcRenderer.send>) {
        const [channel, ...omit] = args
        return ipcRenderer.send(channel, ...omit)
    },
    invoke(...args: Parameters<typeof ipcRenderer.invoke>) {
        const [channel, ...omit] = args
        return ipcRenderer.invoke(channel, ...omit)
    },
})

// LLM API
contextBridge.exposeInMainWorld('llm', {
    // Basic Chat
    chat: (message: string) => ipcRenderer.invoke('llm:chat', message),
    
    // Stream Chat (Simple)
    chatStream: (message: string) => ipcRenderer.send('llm:chatStream', message),
    
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
        dynamicState: string = ""
    ) => ipcRenderer.send('llm:chatStreamWithHistory', { history, userMessage, contextWindow, summary, longTermMemory, userName, charName, role, dynamicState }),

    // Summarization
    updateSummary: (currentSummary: string, newMessages: any[]) => ipcRenderer.invoke('llm:updateSummary', { currentSummary, newMessages }),

    // System Prompt
    setSystemPrompt: (prompt: string) => ipcRenderer.send('llm:setSystemPrompt', prompt),

    // Stream Listeners
    onStreamToken: (callback: (token: string) => void) => {
        // Remove existing listener to avoid duplicates if re-registered
        ipcRenderer.removeAllListeners('llm:streamToken');
        ipcRenderer.on('llm:streamToken', (_event, token) => callback(token));
    },
    onStreamEnd: (callback: () => void) => {
        ipcRenderer.removeAllListeners('llm:streamEnd');
        ipcRenderer.on('llm:streamEnd', () => callback());
    },
    removeStreamListeners: () => {
        ipcRenderer.removeAllListeners('llm:streamToken');
        ipcRenderer.removeAllListeners('llm:streamEnd');
    }
})

// Settings API
contextBridge.exposeInMainWorld('settings', {
    get: (key: string) => ipcRenderer.invoke('settings:get', key),
    set: (key: string, value: any) => ipcRenderer.invoke('settings:set', key, value),
})

// STT API
contextBridge.exposeInMainWorld('stt', {
    getWSUrl: () => ipcRenderer.invoke('stt:get-ws-url'),
})
