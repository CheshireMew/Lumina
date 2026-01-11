/**
 * SettingsModal 共享类型定义
 */
import { CharacterProfile } from "@core/llm/types";

export type Tab = "general" | "voice" | "memory" | "characters";

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onClearHistory?: () => void;
  onContextWindowChange?: (newWindow: number) => void;
  onLLMSettingsChange?: (
    apiKey: string,
    baseUrl: string,
    model: string
  ) => void;
  onCharactersUpdated?: (
    characters: CharacterProfile[],
    activeId: string
  ) => void;
  onUserNameUpdated?: (newName: string) => void;
  onLive2DHighDpiChange?: (enabled: boolean) => void;
  onCharacterSwitch?: (characterId: string) => void;
  activeCharacterId: string;
}

export interface WhisperModelInfo {
  name: string;
  desc?: string;
  size?: string;
  engine?: string;
  download_status: "idle" | "downloading" | "completed" | "failed";
}

export interface AudioDevice {
  index: number;
  name: string;
  channels: number;
}

export interface VoiceInfo {
  name: string;
  gender: string;
}

export const AVAILABLE_MODELS = [
  { name: "Hiyori (Default)", path: "/live2d/Hiyori/Hiyori.model3.json" },
  {
    name: "Laffey II (拉菲)",
    path: "/live2d/imported/Laffey_II/Laffey Ⅱ.model3.json",
  },
  { name: "PinkFox", path: "/live2d/imported/PinkFox/PinkFox.model3.json" },
  {
    name: "Kasane Teto (重音テト)",
    path: "/live2d/imported/KasaneTeto/重音テト.model3.json",
  },
  { name: "Haru", path: "/live2d/imported/Haru/Haru.model3.json" },
  { name: "MaoPro", path: "/live2d/imported/MaoPro/mao_pro.model3.json" },
  { name: "MemuCat", path: "/live2d/imported/MemuCat/memu_cat.model3.json" },
  {
    name: "Hiyori (Mic Ver)",
    path: "/live2d/imported/Hiyori_Mic/hiyori_pro_mic.model3.json",
  },
];

export const STT_SERVER_URL = "http://127.0.0.1:8765";
export const MEMORY_SERVER_URL = "http://127.0.0.1:8010";
