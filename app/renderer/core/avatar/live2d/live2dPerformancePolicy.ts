export const LIVE2D_ACTIVE_FRAME_RATE = 30;
export const LIVE2D_IDLE_FRAME_RATE = 15;
export const LIVE2D_ACTIVE_RENDER_WINDOW_MS = 4000;
export const LIVE2D_MAX_RESOLUTION = 1.5;

export const resolveLive2DResolution = (
    highDpi: boolean,
    devicePixelRatio: number,
) => highDpi ? Math.min(Math.max(devicePixelRatio, 1), LIVE2D_MAX_RESOLUTION) : 1;
