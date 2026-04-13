/**
 * Centralized Configuration for Lumina Frontend
 */
export const API_CONFIG = {
    // These are default ports. They will be overwritten by App.tsx on startup.
    BASE_URL: "http://127.0.0.1:8010",
    TTS_BASE_URL: "http://127.0.0.1:8010/tts",
    STT_BASE_URL: "http://127.0.0.1:8010/stt",
    TIMEOUT: 15000,
    DEFAULT_MODEL_PATH: "/live2d/Hiyori/Hiyori.model3.json",
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
    API_ENDPOINTS.CHARACTERS = `${API_CONFIG.BASE_URL}/characters`;
    API_ENDPOINTS.DEBUG = `${API_CONFIG.BASE_URL}/debug`;

    console.log("[Config] API Configuration Updated:", API_CONFIG);
};

export const API_ENDPOINTS = {
    SOUL: `${API_CONFIG.BASE_URL}/soul`,
    MEMORY: `${API_CONFIG.BASE_URL}/memory`,
    CHARACTERS: `${API_CONFIG.BASE_URL}/characters`,
    DEBUG: `${API_CONFIG.BASE_URL}/debug`,
};
