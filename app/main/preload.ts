import { ipcRenderer, contextBridge, type IpcRendererEvent } from "electron";

type BackendStatus = "starting" | "ready" | "error";

interface BackendState {
    status: BackendStatus;
    ports: Record<string, number>;
    errorMessage?: string;
}

// --------- Expose some API to the Renderer process ---------
// [Phase 27 Security Hardening] Removed raw ipcRenderer exposure
// Only use typed APIs below (llm, settings, etc.)

// Settings API
contextBridge.exposeInMainWorld("settings", {
    get: (key: string) =>
        ipcRenderer.invoke("settings:get", key),
    set: (key: string, value: any) =>
        ipcRenderer.invoke("settings:set", key, value),
});

// STT API
contextBridge.exposeInMainWorld("stt", {
    getWSUrl: () => ipcRenderer.invoke("stt:get-ws-url"),
});

contextBridge.exposeInMainWorld("app", {
    getBootstrapState: () => ipcRenderer.invoke("app:get-bootstrap-state"),
    onBackendStateChange: (callback: (state: BackendState) => void) => {
        const listener = (_event: IpcRendererEvent, state: BackendState) => {
            callback(state);
        };
        ipcRenderer.on("app:backend-state", listener);
        return () => {
            ipcRenderer.removeListener("app:backend-state", listener);
        };
    },
    uploadBackground: (filePath: string) =>
        ipcRenderer.invoke("app:upload-background", filePath),
});
