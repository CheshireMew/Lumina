import { API_CONFIG } from '../../../config';

const CUBISM_CORE_SCRIPT_ID = 'lumina-live2d-cubism-core';

let cubismCorePromise: Promise<void> | null = null;
let cubismCoreSrc: string | null = null;

const getCubismCore = () => {
    const runtime = (window as any).Live2DCubismCore;
    if (runtime) {
        return runtime;
    }

    try {
        return window.eval('typeof Live2DCubismCore !== "undefined" ? Live2DCubismCore : undefined');
    } catch {
        return null;
    }
};

export const ensureCubismCoreLoaded = async (src?: string | null) => {
    const existingRuntime = getCubismCore();
    if (existingRuntime) {
        (window as any).Live2DCubismCore = existingRuntime;
        return;
    }

    const nextSrc = src || `${API_CONFIG.BASE_URL}/assets/libs/live2dcubismcore.min.js`;
    if (!nextSrc) {
        throw new Error('Live2D core script is unavailable.');
    }

    if (cubismCorePromise && cubismCoreSrc !== nextSrc) {
        cubismCorePromise = null;
    }

    if (!cubismCorePromise) {
        cubismCoreSrc = nextSrc;
        cubismCorePromise = (async () => {
            document.getElementById(CUBISM_CORE_SCRIPT_ID)?.remove();

            const response = await fetch(nextSrc, { cache: 'force-cache' });
            if (!response.ok) {
                throw new Error(`Failed to load Live2D core script: ${response.status} ${response.statusText}`);
            }

            const source = await response.text();
            const script = document.createElement('script');
            script.id = CUBISM_CORE_SCRIPT_ID;
            script.textContent = `${source}\n;window.Live2DCubismCore = Live2DCubismCore;`;
            document.head.appendChild(script);

            const runtime = getCubismCore();
            if (!runtime) {
                throw new Error('Live2D core script loaded, but Live2DCubismCore was not exposed on window.');
            }
            (window as any).Live2DCubismCore = runtime;
        })();
    }

    await cubismCorePromise;
};
