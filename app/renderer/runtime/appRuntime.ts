import { memoryService } from "@core/memory/memory_service";
import { ttsService } from "@core/voice/tts_service";
import { API_CONFIG } from "../config";

export interface RuntimeLlmConfig {
    apiKey: string;
    baseUrl: string;
    model: string;
    providerType: "free" | "custom";
    characterId?: string;
}

interface RuntimeState {
    llm: Partial<RuntimeLlmConfig>;
}

const runtimeState: RuntimeState = {
    llm: {},
};

let appliedUrlSignature = "";
let appliedMemorySignature = "";
let memoryConfigChain: Promise<void> = Promise.resolve();

const normalizeUrl = (url: string) => url.replace(/\/$/, "");

const syncServiceBaseUrls = () => {
    const apiBaseUrl = normalizeUrl(API_CONFIG.BASE_URL);
    const ttsBaseUrl = normalizeUrl(API_CONFIG.TTS_BASE_URL);
    const urlSignature = `${apiBaseUrl}::${ttsBaseUrl}`;

    if (urlSignature === appliedUrlSignature) {
        return;
    }

    memoryService.setBaseUrl(apiBaseUrl);
    ttsService.setBaseUrl(ttsBaseUrl);
    appliedUrlSignature = urlSignature;
};

const buildMemorySignature = (llm: Partial<RuntimeLlmConfig>) => {
    const apiKey = llm.apiKey ?? "";
    const baseUrl = llm.baseUrl ? normalizeUrl(llm.baseUrl) : "";
    const model = llm.model ?? "";
    const providerType = llm.providerType ?? "";
    const characterId = llm.characterId ?? "";
    return [apiKey, baseUrl, model, providerType, characterId].join("\u0001");
};

export const syncFrontendRuntime = async (update: {
    llm?: Partial<RuntimeLlmConfig>;
}): Promise<boolean> => {
    syncServiceBaseUrls();

    if (update.llm) {
        runtimeState.llm = {
            ...runtimeState.llm,
            ...update.llm,
        };
    }

    memoryConfigChain = memoryConfigChain.then(async () => {
        try {
            const { llm } = runtimeState;
            if (!llm.apiKey || !llm.baseUrl || !llm.model || !llm.providerType || !llm.characterId) {
                return;
            }

            const signature = buildMemorySignature(llm);
            if (signature === appliedMemorySignature) {
                return;
            }

            const result = await memoryService.configure(
                llm.apiKey,
                normalizeUrl(llm.baseUrl),
                llm.model,
                llm.characterId,
                llm.providerType,
            );

            if (result) {
                appliedMemorySignature = signature;
            }
        } catch (error) {
            console.error("[appRuntime] Failed to sync memory runtime:", error);
        }
    });

    await memoryConfigChain;
    return buildMemorySignature(runtimeState.llm) === appliedMemorySignature;
};
