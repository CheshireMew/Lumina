import { ttsService } from "@core/voice/tts_service";
import { API_CONFIG } from "../config";

let appliedUrlSignature = "";

const normalizeUrl = (url: string) => url.replace(/\/$/, "");

export const syncFrontendServiceUrls = () => {
    const apiBaseUrl = normalizeUrl(API_CONFIG.BASE_URL);
    const ttsBaseUrl = normalizeUrl(API_CONFIG.TTS_BASE_URL);
    const urlSignature = `${apiBaseUrl}::${ttsBaseUrl}`;

    if (urlSignature === appliedUrlSignature) {
        return;
    }

    ttsService.setBaseUrl(ttsBaseUrl);
    appliedUrlSignature = urlSignature;
};
