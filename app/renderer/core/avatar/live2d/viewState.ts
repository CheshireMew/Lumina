const VIEW_STATE_STORAGE_PREFIX = "lumina.live2d.viewState.v2";
const VIEW_STATE_STORE_KEY = "live2d_view_state";
const MIN_SCALE_RATIO = 0.2;
const MAX_SCALE_RATIO = 5;

export const MIN_ABSOLUTE_SCALE = 0.1;
export const MAX_ABSOLUTE_SCALE = 5;

export interface Live2DViewState {
    xRatio: number;
    yRatio: number;
    scaleRatio: number;
}

export const clampScaleRatio = (scaleRatio: number) =>
    Math.min(Math.max(scaleRatio, MIN_SCALE_RATIO), MAX_SCALE_RATIO);

const getStableModelKey = (modelPath: string) => {
    try {
        const url = new URL(modelPath);
        return decodeURIComponent(url.pathname).replace(/\\/g, "/");
    } catch {
        return modelPath.split(/[?#]/, 1)[0].replace(/\\/g, "/");
    }
};

const getViewStateStorageKey = (modelPath: string) =>
    `${VIEW_STATE_STORAGE_PREFIX}:${getStableModelKey(modelPath)}`;

const normalizeViewState = (value: unknown): Live2DViewState | null => {
    if (!value || typeof value !== "object") return null;
    const state = value as Partial<Live2DViewState>;
    if (
        typeof state.xRatio !== "number" ||
        !Number.isFinite(state.xRatio) ||
        typeof state.yRatio !== "number" ||
        !Number.isFinite(state.yRatio) ||
        typeof state.scaleRatio !== "number" ||
        !Number.isFinite(state.scaleRatio)
    ) {
        return null;
    }
    return {
        xRatio: state.xRatio,
        yRatio: state.yRatio,
        scaleRatio: clampScaleRatio(state.scaleRatio),
    };
};

export async function loadViewState(
    modelPath: string,
): Promise<Live2DViewState | null> {
    const modelKey = getStableModelKey(modelPath);
    try {
        const storedStates = (await window.settings?.get?.(
            VIEW_STATE_STORE_KEY,
        )) as Record<string, unknown> | null;
        if (storedStates && typeof storedStates === "object") {
            return normalizeViewState(storedStates[modelKey]);
        }
    } catch (error) {
        console.warn("[Live2DRenderer] Failed to load view state from settings:", error);
    }

    try {
        const raw = window.localStorage.getItem(getViewStateStorageKey(modelPath));
        return raw ? normalizeViewState(JSON.parse(raw)) : null;
    } catch (error) {
        console.warn("[Live2DRenderer] Failed to load saved view state:", error);
        return null;
    }
}

export async function saveViewState(
    modelPath: string,
    state: Live2DViewState,
): Promise<void> {
    const modelKey = getStableModelKey(modelPath);
    try {
        const storedStates = await window.settings?.get?.(VIEW_STATE_STORE_KEY);
        await window.settings?.set?.(VIEW_STATE_STORE_KEY, {
            ...(storedStates && typeof storedStates === "object"
                ? storedStates
                : {}),
            [modelKey]: state,
        });
        return;
    } catch (error) {
        console.warn("[Live2DRenderer] Failed to save view state to settings:", error);
    }

    try {
        window.localStorage.setItem(
            getViewStateStorageKey(modelPath),
            JSON.stringify(state),
        );
    } catch (error) {
        console.warn("[Live2DRenderer] Failed to save view state:", error);
    }
}
