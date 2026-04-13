export interface IElectronSettings {
    set: (key: string, value: any) => Promise<boolean>;
}

export interface IElectronSTT {
    getWSUrl: () => Promise<string>;
}

export interface IElectronApp {
    getBootstrapState: () => Promise<{
        backend: {
            status: "starting" | "ready" | "error";
            ports: Record<string, number>;
            errorMessage?: string;
        };
        localSettings: {
            activeCharacterId: string;
            backgroundImage: string;
            contextWindow: number;
            isTTSEnabled: boolean;
            live2dHighDpi: boolean;
            thinkingEnabled: boolean;
            userName: string;
        };
    }>;
    onBackendStateChange: (
        callback: (state: {
            status: "starting" | "ready" | "error";
            ports: Record<string, number>;
            errorMessage?: string;
        }) => void,
    ) => () => void;
    uploadBackground: (filePath: string) => Promise<string>;
}

declare global {
    interface Window {
        settings: IElectronSettings;
        stt: IElectronSTT;
        app: IElectronApp;
    }
}
