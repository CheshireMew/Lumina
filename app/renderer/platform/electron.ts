import { DEFAULT_USER_NAME } from "../../shared/productDefaults";

interface ElectronSettingsStore {
    backgroundImage: string;
    isTTSEnabled: boolean;
    live2d_high_dpi: boolean;
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

const DEFAULT_BOOTSTRAP_STATE: BootstrapState = {
    backend: {
        status: "starting",
        ports: {},
    },
    localSettings: {
        backgroundImage: "",
        isTTSEnabled: true,
        live2dHighDpi: false,
        userName: DEFAULT_USER_NAME,
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

export async function retryBackend(): Promise<BackendState> {
    return window.app.retryBackend();
}

export async function openLogs(): Promise<string> {
    return window.app.openLogs();
}

export function onBackendStateChange(
    callback: (state: BackendState) => void,
): () => void {
    if (!window.app?.onBackendStateChange) {
        return () => {};
    }

    return window.app.onBackendStateChange(callback);
}
import type {
    BackendState,
    BootstrapState,
} from "../../shared/electronBridge";

export type { BackendState, BootstrapState } from "../../shared/electronBridge";
