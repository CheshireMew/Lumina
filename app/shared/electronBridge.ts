export type BackendStatus = "starting" | "ready" | "error";

export interface BackendState {
    status: BackendStatus;
    ports: Record<string, number>;
    errorMessage?: string;
}

export interface LocalSettingsSnapshot {
    backgroundImage: string;
    isTTSEnabled: boolean;
    live2dHighDpi: boolean;
    userName: string;
}

export interface BootstrapState {
    backend: BackendState;
    localSettings: LocalSettingsSnapshot;
}

export interface ElectronSettingsBridge {
    get: (key: string) => Promise<unknown>;
    set: (key: string, value: unknown) => Promise<boolean>;
}

export interface ElectronSttBridge {
    getWSUrl: () => Promise<string>;
}

export interface ElectronAppBridge {
    getBootstrapState: () => Promise<BootstrapState>;
    onBackendStateChange: (
        callback: (state: BackendState) => void,
    ) => () => void;
    uploadBackground: (filePath: string) => Promise<string>;
    retryBackend: () => Promise<BackendState>;
    openLogs: () => Promise<string>;
    openExternal: (url: string) => Promise<void>;
}
