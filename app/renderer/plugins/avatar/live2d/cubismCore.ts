import { resolveBundledAssetSrc } from '../../../utils/srcUtils';

const CUBISM_CORE_SCRIPT_ID = 'lumina-live2d-cubism-core';

let cubismCorePromise: Promise<void> | null = null;

export const ensureCubismCoreLoaded = async () => {
    if ((window as any).Live2DCubismCore) {
        return;
    }

    if (!cubismCorePromise) {
        cubismCorePromise = new Promise<void>((resolve, reject) => {
            const existing = document.getElementById(CUBISM_CORE_SCRIPT_ID) as HTMLScriptElement | null;
            if (existing) {
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', () => reject(new Error('Failed to load Live2D core script.')), { once: true });
                return;
            }

            const script = document.createElement('script');
            script.id = CUBISM_CORE_SCRIPT_ID;
            script.src = resolveBundledAssetSrc('/libs/live2dcubismcore.min.js');
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load Live2D core script.'));
            document.head.appendChild(script);
        });
    }

    await cubismCorePromise;
};
