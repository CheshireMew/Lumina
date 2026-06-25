import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import * as PIXI from 'pixi.js';
import { IAvatarRenderer } from '../types';
import { ensureCubismCoreLoaded } from './cubismCore';
import { ensureLive2DRuntimeLoaded } from './live2dRuntime';

const exposePixiGlobal = () => {
    const currentPixi = (window as any).PIXI;
    if (currentPixi?.Application && Object.isExtensible(currentPixi)) {
        Object.assign(currentPixi, PIXI);
        return;
    }

    (window as any).PIXI = {
        ...(currentPixi?.live2d ? { live2d: currentPixi.live2d } : {}),
        ...PIXI,
    };
};

// pixi-live2d-display's browser build mutates window.PIXI.live2d.
exposePixiGlobal();

const MOTION_PRELOAD_NONE = 'NONE';
const VIEW_STATE_STORAGE_PREFIX = 'lumina.live2d.viewState.v2';
const VIEW_STATE_STORE_KEY = 'live2d_view_state';
const MIN_SCALE_RATIO = 0.2;
const MAX_SCALE_RATIO = 5;
const MIN_ABSOLUTE_SCALE = 0.1;
const MAX_ABSOLUTE_SCALE = 5.0;

interface Live2DRendererProps {
    modelPath: string;
    highDpi?: boolean;
    cubismCoreSrc: string;
    rendererRuntimeSrc: string;
}

interface Live2DViewState {
    xRatio: number;
    yRatio: number;
    scaleRatio: number;
}

const formatLive2DError = (error: unknown) => {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
};

const getStableModelKey = (modelPath: string) => {
    try {
        const url = new URL(modelPath);
        return decodeURIComponent(url.pathname).replace(/\\/g, '/');
    } catch {
        return modelPath.split(/[?#]/, 1)[0].replace(/\\/g, '/');
    }
};

const getViewStateStorageKey = (modelPath: string) => {
    return `${VIEW_STATE_STORAGE_PREFIX}:${getStableModelKey(modelPath)}`;
};

const isFiniteNumber = (value: unknown): value is number => {
    return typeof value === 'number' && Number.isFinite(value);
};

const normalizeViewState = (value: unknown): Live2DViewState | null => {
    if (!value || typeof value !== 'object') {
        return null;
    }

    const state = value as Partial<Live2DViewState>;
    if (
        !isFiniteNumber(state.xRatio) ||
        !isFiniteNumber(state.yRatio) ||
        !isFiniteNumber(state.scaleRatio)
    ) {
        return null;
    }

    return {
        xRatio: state.xRatio,
        yRatio: state.yRatio,
        scaleRatio: Math.min(Math.max(state.scaleRatio, MIN_SCALE_RATIO), MAX_SCALE_RATIO),
    };
};

const loadViewState = async (modelPath: string): Promise<Live2DViewState | null> => {
    const modelKey = getStableModelKey(modelPath);

    try {
        const storedStates = await window.settings?.get?.(VIEW_STATE_STORE_KEY);
        if (storedStates && typeof storedStates === 'object') {
            return normalizeViewState(storedStates[modelKey]);
        }
    } catch (error) {
        console.warn('[Live2DRenderer] Failed to load view state from settings:', error);
    }

    try {
        const raw = window.localStorage.getItem(getViewStateStorageKey(modelPath));
        return raw ? normalizeViewState(JSON.parse(raw)) : null;
    } catch (error) {
        console.warn('[Live2DRenderer] Failed to load saved view state:', error);
        return null;
    }
};

const saveViewState = async (
    modelPath: string,
    state: Live2DViewState,
) => {
    const modelKey = getStableModelKey(modelPath);

    try {
        const storedStates = await window.settings?.get?.(VIEW_STATE_STORE_KEY);
        const nextStates = {
            ...(
                storedStates && typeof storedStates === 'object'
                    ? storedStates
                    : {}
            ),
            [modelKey]: state,
        };
        await window.settings?.set?.(VIEW_STATE_STORE_KEY, nextStates);
        return;
    } catch (error) {
        console.warn('[Live2DRenderer] Failed to save view state to settings:', error);
    }

    try {
        window.localStorage.setItem(
            getViewStateStorageKey(modelPath),
            JSON.stringify(state),
        );
    } catch (error) {
        console.warn('[Live2DRenderer] Failed to save view state:', error);
    }
};

const Live2DRenderer = forwardRef<IAvatarRenderer, Live2DRendererProps>(({ modelPath, highDpi = false, cubismCoreSrc, rendererRuntimeSrc }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const appRef = useRef<PIXI.Application | null>(null);
    const modelRef = useRef<any | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
    const lastInteractionRef = useRef<number>(Date.now());
    const idleMotionsRef = useRef<any[]>([]);

    // Implement the Standard Interface
    useImperativeHandle(ref, () => ({
        setEmotion: (emotionId: string) => {
            if (modelRef.current) {
                // Map generic emotions if needed, or pass directly
                (modelRef.current as any).expression(emotionId);
            }
        },
        motion: (group: string, index?: number) => {
             if (modelRef.current) {
                lastInteractionRef.current = Date.now();
                (modelRef.current as any).motion(group, index, 3); // Priority 3 = Force
             }
        },
        stopExpression: () => {
             const model = modelRef.current as any;
             if (!model) return;
             if (model.internalModel?.motionManager?.stopAllMotions) {
                 model.internalModel.motionManager.stopAllMotions();
             } else {
                 model.expression('');
             }
        },
        speak: async (audioUrl) => {
            // TODO: Implement LipSync integration here if moving logic from frontend to avatar runtime.
        },
        setBlendShapes: (data) => {
            const model = modelRef.current as any;
            if (!model) return;
            
            // Live2D uses parameters instead of BlendShapes
            // Common parameter IDs (may vary by model)
            const coreModel = model.internalModel?.coreModel;
            if (!coreModel) return;
            
            try {
                // Eye Blink (Parameter IDs vary, trying common ones)
                coreModel.setParameterValueById?.('ParamEyeLOpen', 1 - data.eyeBlinkLeft);
                coreModel.setParameterValueById?.('ParamEyeROpen', 1 - data.eyeBlinkRight);
                
                // Mouth Open
                coreModel.setParameterValueById?.('ParamMouthOpenY', data.jawOpen);
                
                // Head Rotation
                // Angle X = Pan (Left/Right) = headPan
                // Angle Y = Tilt (Up/Down) = headTilt
                // Angle Z = Roll = headRoll
                coreModel.setParameterValueById?.('ParamAngleX', data.headPan * 30); 
                coreModel.setParameterValueById?.('ParamAngleY', data.headTilt * 30);
                coreModel.setParameterValueById?.('ParamAngleZ', data.headRoll * 30);
                
                // Body follows head slightly
                coreModel.setParameterValueById?.('ParamBodyAngleX', data.headPan * 10);
            } catch (e) {
                // Parameter ID may not exist in this model, ignore
            }
        },
        lookAt: (x: number, y: number) => {
            if (modelRef.current) {
                // Map 0..1 to -1..1
                const tx = (x - 0.5) * 2;
                const ty = (y - 0.5) * 2;
                (modelRef.current as any).focus(tx, ty);
            }
        },
        getCanvas: () => {
            return appRef.current?.view as HTMLCanvasElement || null;
        }
    }));

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        let isMounted = true;
        let app: PIXI.Application | null = null;
        let wheelTarget: HTMLCanvasElement | null = null;
        let resizeHandler: (() => void) | null = null;
        let removeInteractionHandlers: (() => void) | null = null;

        const fail = (stage: string, error: unknown) => {
            const message = formatLive2DError(error);
            console.error(`[Live2DRenderer] ${stage}:`, error);
            if (isMounted) {
                setError(`${stage}: ${message}`);
                setIsLoading(false);
            }
        };

        const loadModel = async () => {
            try {
                console.log(`[Live2DRenderer] Loading model from: ${modelPath}`);
                setIsLoading(true);
                setError(null);

                app = new PIXI.Application({
                    width: window.innerWidth,
                    height: window.innerHeight,
                    backgroundAlpha: 0,
                    resizeTo: window,
                    antialias: true,
                    resolution: highDpi ? window.devicePixelRatio : 1,
                    autoDensity: highDpi,
                });
                appRef.current = app;
                container.appendChild(app.view as HTMLCanvasElement);

                await ensureCubismCoreLoaded(cubismCoreSrc);
                const { Live2DModel } = await ensureLive2DRuntimeLoaded(rendererRuntimeSrc);
                const model = await Live2DModel.from(modelPath, {
                    motionPreload: MOTION_PRELOAD_NONE as any,
                });

                if (!isMounted || !app) {
                    model.destroy();
                    return;
                }

                modelRef.current = model;
                app.stage.addChild(model as any);

                // --- CONSTANT IDLE ANIMATION ---
                const motionManager = (model as any).internalModel.motionManager;
                if (motionManager) {
                     if (motionManager.definitions['Idle']) {
                        idleMotionsRef.current = motionManager.definitions['Idle'];
                    }
                    // Disable built-in auto-idle
                    motionManager.startRandomMotion = () => {};
                }

                // Custom Idle Loop
                const IDLE_THRESHOLD = 15000; 
                idleTimerRef.current = setInterval(() => {
                    const timeSinceLast = Date.now() - lastInteractionRef.current;
                    if (timeSinceLast > IDLE_THRESHOLD) {
                        if (idleMotionsRef.current.length > 0) {
                            const randomIdx = Math.floor(Math.random() * idleMotionsRef.current.length);
                            (model as any).motion('Idle', randomIdx, 1);
                            lastInteractionRef.current = Date.now();
                        }
                    }
                }, 1000);

                const modelBaseWidth = model.width;
                const modelBaseHeight = model.height;
                model.anchor?.set?.(0.5, 0.5);
                let savedViewState = await loadViewState(modelPath);
                let defaultScale = 1;
                let lastPersistAt = 0;

                const captureViewState = (): Live2DViewState | null => {
                    if (!app || !defaultScale) return null;

                    const screenWidth = app.renderer.screen.width;
                    const screenHeight = app.renderer.screen.height;
                    if (!screenWidth || !screenHeight) return null;

                    return {
                        xRatio: model.x / screenWidth,
                        yRatio: model.y / screenHeight,
                        scaleRatio: Math.min(
                            Math.max(model.scale.x / defaultScale, MIN_SCALE_RATIO),
                            MAX_SCALE_RATIO,
                        ),
                    };
                };

                const persistViewState = () => {
                    const nextState = captureViewState();
                    if (!nextState) return;

                    savedViewState = nextState;
                    void saveViewState(modelPath, nextState);
                };

                const fitModel = () => {
                    if (!app) return;

                    const screenWidth = app.renderer.screen.width;
                    const screenHeight = app.renderer.screen.height;
                    const scaleX = screenWidth / modelBaseWidth;
                    const scaleY = screenHeight / modelBaseHeight;
                    const scale = Math.min(scaleX, scaleY) * 0.6;

                    defaultScale = scale;

                    if (savedViewState) {
                        const restoredScale = scale * savedViewState.scaleRatio;
                        model.scale.set(restoredScale);
                        model.x = savedViewState.xRatio * screenWidth;
                        model.y = savedViewState.yRatio * screenHeight;
                        return;
                    }

                    model.scale.set(scale);
                    model.x = screenWidth / 2;
                    model.y = screenHeight * 0.6;
                };

                fitModel();
                resizeHandler = fitModel;
                window.addEventListener('resize', resizeHandler);
                (model as any).timeScale = 0.8;

                // --- INTERACTION: Drag & Zoom ---
                model.interactive = true;
                model.buttonMode = true;

                let dragging = false;
                let dragStart = { x: 0, y: 0 };
                let modelStart = { x: 0, y: 0 };
                wheelTarget = app.view as HTMLCanvasElement;

                const handlePointerDown = (event: PointerEvent) => {
                    if (event.button !== 0) return;
                    dragging = true;
                    dragStart = { x: event.clientX, y: event.clientY };
                    modelStart = { x: model.x, y: model.y };
                    model.alpha = 0.8;
                };

                const handlePointerMove = (event: PointerEvent) => {
                    if (!dragging) return;

                    model.x = modelStart.x + event.clientX - dragStart.x;
                    model.y = modelStart.y + event.clientY - dragStart.y;
                    const now = Date.now();
                    if (now - lastPersistAt > 250) {
                        lastPersistAt = now;
                        persistViewState();
                    }
                };

                const handlePointerUp = () => {
                    if (dragging) {
                        persistViewState();
                    }
                    dragging = false;
                    model.alpha = 1.0;
                };

                const handleWheel = (event: WheelEvent) => {
                    event.preventDefault();
                    const scaleFactor = 1.1;
                    let newScale = model.scale.x;
                    if (event.deltaY < 0) {
                        newScale *= scaleFactor;
                    } else {
                        newScale /= scaleFactor;
                    }
                    newScale = Math.min(Math.max(newScale, MIN_ABSOLUTE_SCALE), MAX_ABSOLUTE_SCALE);
                    model.scale.set(newScale);
                    persistViewState();
                };

                wheelTarget.addEventListener('wheel', handleWheel, { passive: false });
                wheelTarget.addEventListener('pointerdown', handlePointerDown);
                window.addEventListener('pointermove', handlePointerMove);
                window.addEventListener('pointerup', handlePointerUp);
                window.addEventListener('pointercancel', handlePointerUp);
                window.addEventListener('blur', handlePointerUp);
                removeInteractionHandlers = () => {
                    persistViewState();
                    wheelTarget?.removeEventListener('wheel', handleWheel);
                    wheelTarget?.removeEventListener('pointerdown', handlePointerDown);
                    window.removeEventListener('pointermove', handlePointerMove);
                    window.removeEventListener('pointerup', handlePointerUp);
                    window.removeEventListener('pointercancel', handlePointerUp);
                    window.removeEventListener('blur', handlePointerUp);
                };

                // Hit Events
                model.on('hit', (hitAreas: string[]) => {
                    if (hitAreas.includes('Body')) {
                        lastInteractionRef.current = Date.now();
                        model.motion('TapBody');
                    }
                });

                setIsLoading(false);

            } catch (error) {
                fail('Failed to load Live2D model', error);
            }
        };

        loadModel();

        return () => {
            isMounted = false;
            if (idleTimerRef.current) clearInterval(idleTimerRef.current);
            idleTimerRef.current = null;
            if (removeInteractionHandlers) {
                removeInteractionHandlers();
            }
            if (resizeHandler) {
                window.removeEventListener('resize', resizeHandler);
            }
            if (modelRef.current) {
                modelRef.current.destroy();
                modelRef.current = null;
            }
            if (appRef.current) {
                try {
                    appRef.current.destroy(true, { children: true });
                } catch (error) {
                    console.warn('[Live2DRenderer] Failed to destroy PIXI application:', error);
                }
                appRef.current = null;
            }
        };
    }, [modelPath, highDpi, cubismCoreSrc, rendererRuntimeSrc]);

    if (error) {
        return (
            <div style={{ width: '100%', height: '100%', position: 'relative' }}>
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#64748b',
                    textAlign: 'center',
                    padding: 24,
                    pointerEvents: 'none',
                }}>
                    <div style={{ maxWidth: 'min(720px, 80vw)', wordBreak: 'break-word' }}>
                        <div>Avatar failed to load</div>
                        <div style={{ marginTop: 8, fontSize: 13, color: '#94a3b8' }}>{error}</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
            {isLoading && (
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                }}>
                    <div style={{
                        width: '72px',
                        height: '72px',
                        borderRadius: '999px',
                        background: 'rgba(255,255,255,0.35)',
                        border: '1px solid rgba(255,255,255,0.6)',
                        backdropFilter: 'blur(8px)',
                        boxShadow: '0 16px 40px rgba(15, 23, 42, 0.10)',
                    }} />
                </div>
            )}
        </div>
    );
});

export default Live2DRenderer;
