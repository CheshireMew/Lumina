import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import * as PIXI from 'pixi.js';
import type { Live2DBehavior } from '@core/llm/types';
import { IAvatarRenderer } from '../types';
import {
    createLive2DController,
    type Live2DController,
} from './live2dController';
import {
    LIVE2D_ACTIVE_FRAME_RATE,
    resolveLive2DResolution,
} from './live2dPerformancePolicy';

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

interface Live2DRendererProps {
    modelPath: string;
    highDpi?: boolean;
    cubismCoreSrc: string;
    rendererRuntimeSrc: string;
    behavior: Live2DBehavior;
}

const formatLive2DError = (error: unknown) => {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
};

const Live2DRenderer = forwardRef<IAvatarRenderer, Live2DRendererProps>(({ modelPath, highDpi = false, cubismCoreSrc, rendererRuntimeSrc, behavior }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const appRef = useRef<PIXI.Application | null>(null);
    const modelRef = useRef<any | null>(null);
    const controllerRef = useRef<Live2DController | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Implement the Standard Interface
    useImperativeHandle(ref, () => ({
        setEmotion: (emotionId: string) => {
            if (modelRef.current) {
                controllerRef.current?.markInteraction();
                // Map generic emotions if needed, or pass directly
                (modelRef.current as any).expression(emotionId);
            }
        },
        motion: (group: string, index?: number) => {
             if (modelRef.current) {
                controllerRef.current?.markInteraction();
                (modelRef.current as any).motion(group, index, 3); // Priority 3 = Force
             }
        },
        stopExpression: () => {
             const model = modelRef.current as any;
             if (!model) return;
             controllerRef.current?.markInteraction();
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
            controllerRef.current?.markInteraction();
            
            // Live2D uses parameters instead of BlendShapes
            // Common parameter IDs (may vary by model)
            const coreModel = model.internalModel?.coreModel;
            if (!coreModel) return;

            const setParameter = (id: string, value: number) => {
                if (id) coreModel.setParameterValueById?.(id, value);
            };
            
            try {
                setParameter(behavior.parameters.eyeBlinkLeft, 1 - data.eyeBlinkLeft);
                setParameter(behavior.parameters.eyeBlinkRight, 1 - data.eyeBlinkRight);
                setParameter(behavior.parameters.mouthOpen, data.jawOpen);
                setParameter(behavior.parameters.headPan, data.headPan * 30);
                setParameter(behavior.parameters.headTilt, data.headTilt * 30);
                setParameter(behavior.parameters.headRoll, data.headRoll * 30);
                setParameter(behavior.parameters.bodyPan, data.headPan * 10);
            } catch (e) {
                // Parameter ID may not exist in this model, ignore
            }
        },
        lookAt: (x: number, y: number) => {
            if (modelRef.current) {
                controllerRef.current?.markInteraction();
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
                    resolution: resolveLive2DResolution(highDpi, window.devicePixelRatio),
                    autoDensity: highDpi,
                });
                app.ticker.maxFPS = LIVE2D_ACTIVE_FRAME_RATE;
                appRef.current = app;
                container.appendChild(app.view as HTMLCanvasElement);

                const controller = await createLive2DController({
                    app,
                    modelPath,
                    cubismCoreSrc,
                    rendererRuntimeSrc,
                    behavior,
                    isActive: () => isMounted,
                });
                if (!isMounted) {
                    controller.dispose();
                    return;
                }
                controllerRef.current = controller;
                modelRef.current = controller.model;

                setIsLoading(false);

            } catch (error) {
                fail('Failed to load Live2D model', error);
            }
        };

        loadModel();

        return () => {
            isMounted = false;
            controllerRef.current?.dispose();
            controllerRef.current = null;
            modelRef.current = null;
            if (appRef.current) {
                try {
                    appRef.current.destroy(true, { children: true });
                } catch (error) {
                    console.warn('[Live2DRenderer] Failed to destroy PIXI application:', error);
                }
                appRef.current = null;
            }
        };
    }, [modelPath, highDpi, cubismCoreSrc, rendererRuntimeSrc, behavior]);

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
