import { API_CONFIG } from '../../../config';

const LIVE2D_RUNTIME_SCRIPT_ID = 'lumina-pixi-live2d-cubism4';

let runtimePromise: Promise<any> | null = null;
let runtimeSrc: string | null = null;

const getLive2DRuntime = () => {
    return (window as any).PIXI?.live2d || null;
};

export const ensureLive2DRuntimeLoaded = async (src?: string | null) => {
    const existingRuntime = getLive2DRuntime();
    if (existingRuntime?.Live2DModel) {
        return existingRuntime;
    }

    const nextSrc = src || `${API_CONFIG.BASE_URL}/assets/libs/pixi-live2d-display-cubism4.min.js`;
    if (!nextSrc) {
        throw new Error('Live2D renderer runtime script is unavailable.');
    }

    if (runtimePromise && runtimeSrc !== nextSrc) {
        runtimePromise = null;
    }

    if (!runtimePromise) {
        runtimeSrc = nextSrc;
        runtimePromise = (async () => {
            document.getElementById(LIVE2D_RUNTIME_SCRIPT_ID)?.remove();

            const response = await fetch(nextSrc, { cache: 'force-cache' });
            if (!response.ok) {
                throw new Error(`Failed to load Live2D renderer runtime: ${response.status} ${response.statusText}`);
            }

            const source = await response.text();
            const script = document.createElement('script');
            script.id = LIVE2D_RUNTIME_SCRIPT_ID;
            script.textContent = source;
            document.head.appendChild(script);

            const runtime = getLive2DRuntime();
            if (!runtime?.Live2DModel) {
                throw new Error('Live2D renderer runtime loaded, but PIXI.live2d.Live2DModel was not exposed.');
            }

            return runtime;
        })();
    }

    return runtimePromise;
};
