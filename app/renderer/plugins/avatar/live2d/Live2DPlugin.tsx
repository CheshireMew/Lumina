import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display/cubism4';
import { IAvatarRenderer } from '../../../core/avatar/types';

// Expose PIXI to window for pixi-live2d-display to use
(window as any).PIXI = PIXI;

interface Live2DPluginProps {
    modelPath: string;
    highDpi?: boolean;
}

const Live2DPlugin = forwardRef<IAvatarRenderer, Live2DPluginProps>(({ modelPath, highDpi = false }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const appRef = useRef<PIXI.Application | null>(null);
    const modelRef = useRef<Live2DModel | null>(null);
    const [error, setError] = useState<string | null>(null);

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
            // TODO: Implement LipSync integration here if moving logic from frontend to plugin
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
        if (!containerRef.current) return;

        // Initialize PIXI Application
        const app = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundAlpha: 0, 
            resizeTo: window,
            antialias: true,
            resolution: highDpi ? window.devicePixelRatio : 1,
            autoDensity: highDpi,
        });

        containerRef.current.appendChild(app.view as HTMLCanvasElement);
        appRef.current = app;

        let isMounted = true;

        const loadModel = async () => {
            try {
                console.log(`[Live2DPlugin] Loading model from: ${modelPath}`);
                const model = await Live2DModel.from(modelPath);

                if (!isMounted || !appRef.current) {
                    model.destroy();
                    return;
                }

                modelRef.current = model;
                appRef.current.stage.addChild(model as any);

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

                // Fitting Logic
                const scaleX = appRef.current.view.width / model.width;
                const scaleY = appRef.current.view.height / model.height;
                const scale = Math.min(scaleX, scaleY) * 0.6; 
                model.scale.set(scale);
                model.anchor.set(0.5, 0.5);
                model.x = window.innerWidth / 2;
                model.y = window.innerHeight * 0.6;
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
                const canvas = appRef.current.view as HTMLCanvasElement;
                canvas.onwheel = (e) => {
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

            } catch (error) {
                console.error('[Live2DPlugin] Failed to load model:', error);
                setError(error instanceof Error ? error.message : String(error));
            }
        };

        loadModel();

        return () => {
            isMounted = false;
            if (idleTimerRef.current) clearInterval(idleTimerRef.current);
            if (modelRef.current) modelRef.current.destroy();
            if (appRef.current) appRef.current.destroy(true, { children: true });
        };
    }, [modelPath, highDpi]);

    if (error) return <div style={{ color: 'red' }}>Error: {error}</div>;
    return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
});

export default Live2DPlugin;
