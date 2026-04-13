interface ElectronSettingsStore {
    activeCharacterId: string;
    backgroundImage: string;
    contextWindow: number;
    isTTSEnabled: boolean;
    live2d_high_dpi: boolean;
    thinking_enabled: boolean;
    userName: string;
}

async function setSetting<K extends keyof ElectronSettingsStore>(
    key: K,
    value: ElectronSettingsStore[K],
): Promise<boolean>;
async function setSetting(key: string, value: unknown): Promise<boolean>;
async function setSetting(key: string, value: unknown): Promise<boolean> {
    return window.settings.set(key, value);
}

export const electronSettings = {
    set: setSetting,
};

export interface BackendState {
    status: "starting" | "ready" | "error";
    ports: Record<string, number>;
    errorMessage?: string;
}

export interface BootstrapState {
    backend: BackendState;
    localSettings: {
        activeCharacterId: string;
        backgroundImage: string;
        contextWindow: number;
        isTTSEnabled: boolean;
        live2dHighDpi: boolean;
        thinkingEnabled: boolean;
        userName: string;
    };
}

const DEFAULT_BOOTSTRAP_STATE: BootstrapState = {
    backend: {
        status: "starting",
        ports: {},
    },
    localSettings: {
        activeCharacterId: "hiyori",
        backgroundImage: "",
        contextWindow: 50,
        isTTSEnabled: true,
        live2dHighDpi: false,
        thinkingEnabled: false,
        userName: "Master",
    },
};

let bootstrapStatePromise: Promise<BootstrapState> | null = null;

export async function loadBootstrapState(): Promise<BootstrapState> {
    if (!window.app?.getBootstrapState) {
        return DEFAULT_BOOTSTRAP_STATE;
    }

    if (!bootstrapStatePromise) {
        bootstrapStatePromise = window.app.getBootstrapState().catch((error) => {
            bootstrapStatePromise = null;
            throw error;
        });
    }

    return bootstrapStatePromise;
}

export async function getSttWebSocketUrl(): Promise<string> {
    return window.stt.getWSUrl();
}

export async function uploadBackground(filePath: string): Promise<string> {
    return window.app.uploadBackground(filePath);
}

export function onBackendStateChange(
    callback: (state: BackendState) => void,
): () => void {
    if (!window.app?.onBackendStateChange) {
        return () => {};
    }

    return window.app.onBackendStateChange(callback);
}
