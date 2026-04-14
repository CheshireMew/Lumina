import { resolveBundledAssetSrc } from '../../../utils/srcUtils';

const CUBISM_CORE_SCRIPT_ID = 'lumina-live2d-cubism-core';

let cubismCorePromise: Promise<void> | null = null;
let cubismCoreSrc: string | null = null;

export const ensureCubismCoreLoaded = async (src?: string | null) => {
    if ((window as any).Live2DCubismCore) {
        return;
    }

    const nextSrc = src || resolveBundledAssetSrc('/libs/live2dcubismcore.min.js');
    if (!nextSrc) {
        throw new Error('Live2D core script is unavailable.');
    }

    if (cubismCorePromise && cubismCoreSrc !== nextSrc) {
        cubismCorePromise = null;
    }

    if (!cubismCorePromise) {
        cubismCoreSrc = nextSrc;
        cubismCorePromise = new Promise<void>((resolve, reject) => {
            const existing = document.getElementById(CUBISM_CORE_SCRIPT_ID) as HTMLScriptElement | null;
            if (existing) {
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', () => reject(new Error('Failed to load Live2D core script.')), { once: true });
                return;
            }

            const script = document.createElement('script');
            script.id = CUBISM_CORE_SCRIPT_ID;
            script.src = nextSrc;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load Live2D core script.'));
            document.head.appendChild(script);
        });
    }

    await cubismCorePromise;
};
