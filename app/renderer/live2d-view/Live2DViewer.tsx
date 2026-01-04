import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display/cubism4';

// Expose PIXI to window for pixi-live2d-display to use
(window as any).PIXI = PIXI;

interface Live2DViewerProps {
    modelPath: string;
    highDpi?: boolean;
}

export interface Live2DViewerRef {
    /**
     * Trigger a motion group
     * @param group The name of the motion group (e.g., 'TapBody')
     */
    motion: (group: string, index?: number) => void;
    /**
     * Set an expression
     * @param expressionId The ID of the expression
     */
    expression: (expressionId: string) => void;
}

const Live2DViewer = forwardRef<Live2DViewerRef, Live2DViewerProps>(({ modelPath, highDpi = false }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const appRef = useRef<PIXI.Application | null>(null);
    const modelRef = useRef<Live2DModel | null>(null);
    const [error, setError] = useState<string | null>(null);

    const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
    const lastInteractionRef = useRef<number>(Date.now());
    const idleMotionsRef = useRef<any[]>([]);

    useImperativeHandle(ref, () => ({
        motion: (group, index) => {
            if (modelRef.current) {
                // Update interaction time
                lastInteractionRef.current = Date.now();

                // Stop any custom idle timer handling temporarily if needed
                // (Though our interval loop handles verification)

                // Force priority to ensuring emotional reactions override idle
                // 3 = FORCE priority in Cubism. 
                // Since we disabled built-in auto-idle, we don't need to manually stop motions or delay.
                // Standard priority logic handles blending.

                const success = (modelRef.current as any).motion(group, index, 3);
                console.log(`[Live2DViewer] Manual trigger (${group} ${index}):`, success);
            }
        },
        expression: (expressionId) => {
            if (modelRef.current) {
                // CoreModel access for setting parameters/expressions might differ slightly depending on SDK version
                // internalModel.motionManager.expressionManager... 
                // For simplicity with this library, it often wraps expression logic.
                // Let's rely on internal model expression manager if available or parameter setting.
                (modelRef.current as any).expression(expressionId);
            }
        }
    }));

    useEffect(() => {
        if (!containerRef.current) return;

        // Initialize PIXI Application
        // Transparent background for desktop companion feel
        const app = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundAlpha: 0, // Transparent
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
                console.log(`Loading Live2D model from: ${modelPath}`);
                const model = await Live2DModel.from(modelPath);

                if (!isMounted || !appRef.current) {
                    model.destroy();
                    return;
                }

                modelRef.current = model;
                appRef.current.stage.addChild(model as any);

                // --- CUSTOM IDLE LOGIC ---
                // 1. Disable built-in auto-idle by overriding startRandomMotion
                // This is safer than modifying definitions because it keeps data intact for manual calls
                const motionManager = (model as any).internalModel.motionManager;
                if (motionManager) {
                    // Save original references if needed (optional)
                    // Save Idle motions for our custom timer
                    if (motionManager.definitions['Idle']) {
                        idleMotionsRef.current = motionManager.definitions['Idle'];
                    }

                    // Disable auto-playback
                    console.log('[Live2DViewer] Overriding startRandomMotion to disable built-in auto-idle.');
                    motionManager.startRandomMotion = () => {
                        // Do nothing. This stops the model from randomly moving on its own.
                    };
                }

                // 2. Setup Idle Timer
                const IDLE_THRESHOLD = 15000; // 15 seconds
                idleTimerRef.current = setInterval(() => {
                    const timeSinceLast = Date.now() - lastInteractionRef.current;
                    if (timeSinceLast > IDLE_THRESHOLD) {
                        // Trigger a random idle motion
                        if (idleMotionsRef.current.length > 0) {
                            const randomIdx = Math.floor(Math.random() * idleMotionsRef.current.length);
                            console.log(`[Live2DViewer] Custom Idle triggering (Index ${randomIdx})`);

                            // Play using the STANDARD 'Idle' group (data is intact now)
                            (model as any).motion('Idle', randomIdx, 1); // Priority 1 (IDLE) is fine here

                            lastInteractionRef.current = Date.now();
                        }
                    }
                }, 1000);

                // Auto-scale to fit
                const scaleX = appRef.current.view.width / model.width;
                const scaleY = appRef.current.view.height / model.height;
                // fit 80% of screen height
                const scale = Math.min(scaleX, scaleY) * 0.8;

                model.scale.set(scale);
                model.anchor.set(0.5, 0.5);
                model.x = appRef.current.view.width / 2;
                model.y = appRef.current.view.height / 2;

                // Slow down animation slightly for more natural feel and longer duration
                (model as any).timeScale = 0.8;

                // Interaction
                model.on('hit', (hitAreas: string[]) => {
                    if (hitAreas.includes('Body')) {
                        // Reset idle timer
                        lastInteractionRef.current = Date.now();
                        model.motion('TapBody');
                    }
                });

            } catch (error) {
                console.error('Failed to load Live2D model:', error);
                setError(error instanceof Error ? error.message : String(error));
            }
        };

        loadModel();

        return () => {
            isMounted = false;
            if (idleTimerRef.current) clearInterval(idleTimerRef.current);
            if (modelRef.current) {
                modelRef.current.destroy();
            }
            if (appRef.current) {
                appRef.current.destroy(true, { children: true });
            }
        };
    }, [modelPath, highDpi]);

    // --- Interaction Handlers (Zoom & Pan) ---
    const draggingRef = useRef(false);
    const dragStartRef = useRef({ x: 0, y: 0 });
    const modelStartPosRef = useRef({ x: 0, y: 0 });

    useEffect(() => {
        const canvas = containerRef.current?.querySelector('canvas');
        if (!canvas || !appRef.current) return;

        const handleWheel = (e: WheelEvent) => {
            e.preventDefault();
            if (!modelRef.current) return;

            const scaleAmount = -e.deltaY * 0.0002;
            const newScale = Math.max(0.1, Math.min(modelRef.current.scale.x + scaleAmount, 5.0)); // Clamp scale 0.1x to 5x

            modelRef.current.scale.set(newScale);
        };

        const handlePointerDown = (e: PointerEvent) => {
            if (e.button !== 0) return; // Only Left Click
            draggingRef.current = true;
            dragStartRef.current = { x: e.clientX, y: e.clientY };
            if (modelRef.current) {
                modelStartPosRef.current = { x: modelRef.current.x, y: modelRef.current.y };
            }
        };

        const handlePointerMove = (e: PointerEvent) => {
            if (!draggingRef.current || !modelRef.current) return;

            const dx = e.clientX - dragStartRef.current.x;
            const dy = e.clientY - dragStartRef.current.y;

            modelRef.current.x = modelStartPosRef.current.x + dx;
            modelRef.current.y = modelStartPosRef.current.y + dy;
        };

        const handlePointerUp = () => {
            draggingRef.current = false;
        };

        canvas.addEventListener('wheel', handleWheel, { passive: false });
        canvas.addEventListener('pointerdown', handlePointerDown);
        window.addEventListener('pointermove', handlePointerMove); // Listen on window to catch drags outside canvas
        window.addEventListener('pointerup', handlePointerUp);

        return () => {
            canvas.removeEventListener('wheel', handleWheel);
            canvas.removeEventListener('pointerdown', handlePointerDown);
            window.removeEventListener('pointermove', handlePointerMove);
            window.removeEventListener('pointerup', handlePointerUp);
        };
    }, [modelPath, highDpi]); // Re-bind if app/model stays same but checking existence is safe

    if (error) {
        return <div style={{ color: 'red', background: 'white', padding: 20 }}>Error: {error}</div>;
    }

    return <div ref={containerRef} style={{ width: '100%', height: '100%', overflow: 'hidden' }} />;
});

export default Live2DViewer;
