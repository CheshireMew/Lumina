/**
 * Centralized Configuration for Lumina Frontend
 */
export const API_CONFIG = {
    // These are default ports. They will be overwritten by App.tsx on startup.
    BASE_URL: "http://127.0.0.1:8010",
    TTS_BASE_URL: "http://127.0.0.1:8010/tts",
    STT_BASE_URL: "http://127.0.0.1:8010/stt",
    TIMEOUT: 15000,
    DEFAULT_LIVE2D_MODEL: "Hiyori",
};

/**
 * Helper to update config from Dynamic Ports
 */
export const updateApiConfig = (ports: Record<string, number>) => {
    if (ports.memory) API_CONFIG.BASE_URL = `http://127.0.0.1:${ports.memory}`;
    API_CONFIG.TTS_BASE_URL = `${API_CONFIG.BASE_URL}/tts`;
    API_CONFIG.STT_BASE_URL = `${API_CONFIG.BASE_URL}/stt`;

    // Update derived endpoints too
    API_ENDPOINTS.SOUL = `${API_CONFIG.BASE_URL}/soul`;
    API_ENDPOINTS.MEMORY = `${API_CONFIG.BASE_URL}/memory`;
    API_ENDPOINTS.CHARACTER = `${API_CONFIG.BASE_URL}/character`;

    console.log("[Config] API Configuration Updated:", API_CONFIG);
};

export const API_ENDPOINTS = {
    SOUL: `${API_CONFIG.BASE_URL}/soul`,
    MEMORY: `${API_CONFIG.BASE_URL}/memory`,
    CHARACTER: `${API_CONFIG.BASE_URL}/character`,
};
