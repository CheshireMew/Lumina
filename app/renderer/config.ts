/**
 * Centralized Configuration for Lumina Frontend
 */

export const API_CONFIG = {
  BASE_URL: "http://127.0.0.1:8010",
  TTS_BASE_URL: "http://127.0.0.1:8766",
  STT_BASE_URL: "http://127.0.0.1:8765",
  TIMEOUT: 15000,
  DEFAULT_MODEL_PATH: "/live2d/Hiyori/Hiyori.model3.json",
};

export const API_ENDPOINTS = {
  SOUL: `${API_CONFIG.BASE_URL}/soul`,
  MEMORY: `${API_CONFIG.BASE_URL}/memory`,
  CHARACTERS: `${API_CONFIG.BASE_URL}/characters`,
  GALGAME: `${API_CONFIG.BASE_URL}/galgame`,
  DREAM: `${API_CONFIG.BASE_URL}/dream`,
  DEBUG: `${API_CONFIG.BASE_URL}/debug`,
};
