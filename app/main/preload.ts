import { ipcRenderer, contextBridge, type IpcRendererEvent } from "electron";
import type {
    BackendState,
    ElectronAppBridge,
    ElectronSettingsBridge,
    ElectronSttBridge,
} from "../shared/electronBridge";

// --------- Expose some API to the Renderer process ---------
// [Phase 27 Security Hardening] Removed raw ipcRenderer exposure
// Only use typed APIs below (llm, settings, etc.)

// Settings API
const settingsBridge: ElectronSettingsBridge = {
    get: (key: string) =>
        ipcRenderer.invoke("settings:get", key),
    set: (key: string, value: unknown) =>
        ipcRenderer.invoke("settings:set", key, value),
};
contextBridge.exposeInMainWorld("settings", settingsBridge);

// STT API
const sttBridge: ElectronSttBridge = {
    getWSUrl: () => ipcRenderer.invoke("stt:get-ws-url"),
};
contextBridge.exposeInMainWorld("stt", sttBridge);

const appBridge: ElectronAppBridge = {
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
    retryBackend: () => ipcRenderer.invoke("app:retry-backend"),
    openLogs: () => ipcRenderer.invoke("app:open-logs"),
    openExternal: (url: string) => ipcRenderer.invoke("app:open-external", url),
};
contextBridge.exposeInMainWorld("app", appBridge);
