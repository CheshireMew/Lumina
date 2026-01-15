export interface IElectronSettings {
  get: (key: string) => Promise<any>;
  set: (key: string, value: any) => Promise<boolean>;
}

export interface IElectronLLM {
  chat: (message: string) => Promise<string>;
  chatStream: (message: string) => void;
  chatStreamWithHistory: (
    history: any[],
    userMessage: string,
    contextWindow: number,
    summary?: string,
    longTermMemory?: string,
    userName?: string,
    charName?: string,
    role?: "user" | "system",
    dynamicState?: string,
    enableThinking?: boolean,
    temperature?: number,
    topP?: number,
    presencePenalty?: number,
    frequencyPenalty?: number,
    characterId?: string,
    userId?: string
  ) => void;
  updateSummary: (
    currentSummary: string,
    newMessages: any[]
  ) => Promise<string>;
  setSystemPrompt: (prompt: string) => void;
  onStreamToken: (callback: (token: string) => void) => void;
  onStreamEnd: (callback: () => void) => void;
  removeStreamListeners: () => void;
}

export interface IElectronSTT {
  getWSUrl: () => Promise<string>;
}

export interface IElectronApp {
  getPorts: () => Promise<Record<string, number>>;
}

declare global {
  interface Window {
    settings: IElectronSettings;
    llm: IElectronLLM;
    stt: IElectronSTT;
    app: IElectronApp;
  }
}
