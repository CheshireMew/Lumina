import type {
    ElectronAppBridge,
    ElectronSettingsBridge,
    ElectronSttBridge,
} from "../../shared/electronBridge";

declare global {
    interface Window {
        settings: ElectronSettingsBridge;
        stt: ElectronSttBridge;
        app: ElectronAppBridge;
    }
}
