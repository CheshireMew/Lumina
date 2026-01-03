import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display/cubism4';

// Expose PIXI to window for pixi-live2d-display to use
(window as any).PIXI = PIXI;

interface Live2DViewerProps {
    modelPath: string;
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

const Live2DViewer = forwardRef<Live2DViewerRef, Live2DViewerProps>(({ modelPath }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const appRef = useRef<PIXI.Application | null>(null);
    const modelRef = useRef<Live2DModel | null>(null);
    const [error, setError] = useState<string | null>(null);

    useImperativeHandle(ref, () => ({
        motion: (group, index) => {
            if (modelRef.current) {
                modelRef.current.motion(group, index);
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

                // Auto-scale to fit
                const scaleX = appRef.current.view.width / model.width;
                const scaleY = appRef.current.view.height / model.height;
                // fit 80% of screen height
                const scale = Math.min(scaleX, scaleY) * 0.8;

                model.scale.set(scale);
                model.anchor.set(0.5, 0.5);
                model.x = appRef.current.view.width / 2;
                model.y = appRef.current.view.height / 2;

                // Interaction
                model.on('hit', (hitAreas: string[]) => {
                    if (hitAreas.includes('Body')) {
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
            if (modelRef.current) {
                modelRef.current.destroy();
            }
            if (appRef.current) {
                appRef.current.destroy(true, { children: true });
            }
        };
    }, [modelPath]);

    if (error) {
        return <div style={{ color: 'red', background: 'white', padding: 20 }}>Error: {error}</div>;
    }

    return <div ref={containerRef} style={{ width: '100%', height: '100%', overflow: 'hidden' }} />;
});

export default Live2DViewer;
