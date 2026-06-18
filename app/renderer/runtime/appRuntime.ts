import { ttsService } from "@core/voice/tts_service";
import { RuntimeConfig } from "./runtimeConfig";

let appliedUrlSignature = "";

const normalizeUrl = (url: string) => url.replace(/\/$/, "");

export const syncFrontendServiceUrls = (runtimeConfig: RuntimeConfig) => {
    const apiBaseUrl = normalizeUrl(runtimeConfig.apiBaseUrl);
    const ttsBaseUrl = normalizeUrl(runtimeConfig.ttsBaseUrl);
    const urlSignature = `${apiBaseUrl}::${ttsBaseUrl}`;

    if (urlSignature === appliedUrlSignature) {
        return;
    }

    ttsService.setBaseUrl(ttsBaseUrl);
    appliedUrlSignature = urlSignature;
};
