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

interface Live2DRendererProps {
    modelPath: string;
    highDpi?: boolean;
    cubismCoreSrc?: string;
    rendererRuntimeSrc?: string;
}

const formatLive2DError = (error: unknown) => {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
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
                const fitModel = () => {
                    if (!app) return;

                    const screenWidth = app.renderer.screen.width;
                    const screenHeight = app.renderer.screen.height;
                    const scaleX = screenWidth / modelBaseWidth;
                    const scaleY = screenHeight / modelBaseHeight;
                    const scale = Math.min(scaleX, scaleY) * 0.6;
                    const bounds = model.getLocalBounds();

                    model.scale.set(scale);
                    model.x = screenWidth / 2 - (bounds.x + bounds.width / 2) * scale;
                    model.y = screenHeight * 0.6 - (bounds.y + bounds.height / 2) * scale;
                };

                fitModel();
                resizeHandler = fitModel;
                window.addEventListener('resize', resizeHandler);
                (model as any).timeScale = 0.8;

                // --- INTERACTION: Drag & Zoom ---
                model.interactive = true;
                model.buttonMode = true;

                let dragging = false;
                let dragData: PIXI.InteractionData | null = null;
                let dragOffset = { x: 0, y: 0 };

                model.on('pointerdown', (event: PIXI.InteractionEvent) => {
                    dragging = true;
                    dragData = event.data;
                    const newPosition = dragData.getLocalPosition(model.parent);
                    dragOffset.x = newPosition.x - model.x;
                    dragOffset.y = newPosition.y - model.y;
                    model.alpha = 0.8; 
                });

                model.on('pointerup', () => {
                    dragging = false;
                    dragData = null;
                    model.alpha = 1.0;
                });
                
                model.on('pointerupoutside', () => {
                    dragging = false;
                    dragData = null;
                    model.alpha = 1.0;
                });

                model.on('pointermove', () => {
                    if (dragging && dragData) {
                        const newPosition = dragData.getLocalPosition(model.parent);
                        model.x = newPosition.x - dragOffset.x;
                        model.y = newPosition.y - dragOffset.y;
                    }
                });

                // Zoom logic
                wheelTarget = app.view as HTMLCanvasElement;
                wheelTarget.onwheel = (e) => {
                    e.preventDefault();
                    const scaleFactor = 1.1;
                    let newScale = model.scale.x;
                    if (e.deltaY < 0) {
                        newScale *= scaleFactor;
                    } else {
                        newScale /= scaleFactor;
                    }
                    newScale = Math.min(Math.max(newScale, 0.1), 3.0);
                    model.scale.set(newScale);
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
            if (wheelTarget) {
                wheelTarget.onwheel = null;
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
