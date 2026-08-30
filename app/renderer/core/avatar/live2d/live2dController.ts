import type { Live2DBehavior } from "@core/llm/types";
import type * as PIXI from "pixi.js";
import { ensureCubismCoreLoaded } from "./cubismCore";
import { ensureLive2DRuntimeLoaded } from "./live2dRuntime";
import {
    clampScaleRatio,
    loadViewState,
    MAX_ABSOLUTE_SCALE,
    MIN_ABSOLUTE_SCALE,
    saveViewState,
    type Live2DViewState,
} from "./viewState";
import {
    LIVE2D_ACTIVE_FRAME_RATE,
    LIVE2D_ACTIVE_RENDER_WINDOW_MS,
    LIVE2D_IDLE_FRAME_RATE,
} from "./live2dPerformancePolicy";

const MOTION_PRELOAD_NONE = "NONE";

export interface Live2DController {
    model: any;
    markInteraction: () => void;
    dispose: () => void;
}

interface Live2DControllerOptions {
    app: PIXI.Application;
    modelPath: string;
    cubismCoreSrc: string;
    rendererRuntimeSrc: string;
    behavior: Live2DBehavior;
    isActive: () => boolean;
}

export async function createLive2DController({
    app,
    modelPath,
    cubismCoreSrc,
    rendererRuntimeSrc,
    behavior,
    isActive,
}: Live2DControllerOptions): Promise<Live2DController> {
    await ensureCubismCoreLoaded(cubismCoreSrc);
    const { Live2DModel } = await ensureLive2DRuntimeLoaded(rendererRuntimeSrc);
    const model = await Live2DModel.from(modelPath, {
        motionPreload: MOTION_PRELOAD_NONE as any,
    });
    if (!isActive()) {
        model.destroy();
        return {
            model,
            markInteraction: () => undefined,
            dispose: () => undefined,
        };
    }
    app.stage.addChild(model as any);

    let lastInteractionAt = Date.now();
    let activeRenderingUntil = lastInteractionAt + LIVE2D_ACTIVE_RENDER_WINDOW_MS;
    const setFrameRate = (frameRate: number) => {
        if (app.ticker.maxFPS !== frameRate) app.ticker.maxFPS = frameRate;
    };
    const markInteraction = () => {
        lastInteractionAt = Date.now();
        activeRenderingUntil = lastInteractionAt + LIVE2D_ACTIVE_RENDER_WINDOW_MS;
        setFrameRate(LIVE2D_ACTIVE_FRAME_RATE);
    };

    const motionManager = model.internalModel?.motionManager;
    const idleMotions =
        motionManager?.definitions?.[behavior.idleMotionGroup] || [];
    if (motionManager) motionManager.startRandomMotion = () => {};
    const idleTimer = window.setInterval(() => {
        const now = Date.now();
        if (
            now - lastInteractionAt > behavior.idleThresholdMs &&
            idleMotions.length > 0
        ) {
            const index = Math.floor(Math.random() * idleMotions.length);
            model.motion(behavior.idleMotionGroup, index, 1);
            markInteraction();
        } else if (now >= activeRenderingUntil) {
            setFrameRate(LIVE2D_IDLE_FRAME_RATE);
        }
    }, 1000);

    const handleVisibilityChange = () => {
        if (document.visibilityState === "hidden") {
            app.stop();
            return;
        }
        app.start();
        setFrameRate(
            Date.now() < activeRenderingUntil
                ? LIVE2D_ACTIVE_FRAME_RATE
                : LIVE2D_IDLE_FRAME_RATE,
        );
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    const modelBaseWidth = model.width;
    const modelBaseHeight = model.height;
    model.anchor?.set?.(0.5, 0.5);
    model.timeScale = behavior.timeScale;
    let savedViewState = await loadViewState(modelPath);
    let defaultScale = 1;
    let lastPersistAt = 0;

    const captureViewState = (): Live2DViewState | null => {
        const screenWidth = app.renderer.screen.width;
        const screenHeight = app.renderer.screen.height;
        if (!screenWidth || !screenHeight || !defaultScale) return null;
        return {
            xRatio: model.x / screenWidth,
            yRatio: model.y / screenHeight,
            scaleRatio: clampScaleRatio(model.scale.x / defaultScale),
        };
    };

    const persistViewState = () => {
        const nextState = captureViewState();
        if (!nextState) return;
        savedViewState = nextState;
        void saveViewState(modelPath, nextState);
    };

    const fitModel = () => {
        const screenWidth = app.renderer.screen.width;
        const screenHeight = app.renderer.screen.height;
        const scale = Math.min(
            screenWidth / modelBaseWidth,
            screenHeight / modelBaseHeight,
        ) * behavior.fitScale;
        defaultScale = scale;

        if (savedViewState) {
            model.scale.set(scale * savedViewState.scaleRatio);
            model.x = savedViewState.xRatio * screenWidth;
            model.y = savedViewState.yRatio * screenHeight;
            return;
        }
        model.scale.set(scale);
        model.x = screenWidth / 2;
        model.y = screenHeight * behavior.verticalPositionRatio;
    };

    fitModel();
    window.addEventListener("resize", fitModel);
    model.interactive = true;
    model.buttonMode = true;

    const canvas = app.view as HTMLCanvasElement;
    let dragging = false;
    let dragStart = { x: 0, y: 0 };
    let modelStart = { x: 0, y: 0 };
    const handlePointerDown = (event: PointerEvent) => {
        if (event.button !== 0) return;
        dragging = true;
        dragStart = { x: event.clientX, y: event.clientY };
        modelStart = { x: model.x, y: model.y };
        model.alpha = 0.8;
        markInteraction();
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
        if (dragging) persistViewState();
        dragging = false;
        model.alpha = 1;
    };
    const handleWheel = (event: WheelEvent) => {
        event.preventDefault();
        const scaleFactor = event.deltaY < 0 ? 1.1 : 1 / 1.1;
        const scale = Math.min(
            Math.max(model.scale.x * scaleFactor, MIN_ABSOLUTE_SCALE),
            MAX_ABSOLUTE_SCALE,
        );
        model.scale.set(scale);
        markInteraction();
        persistViewState();
    };
    const handleHit = (hitAreas: string[]) => {
        if (!hitAreas.includes(behavior.tapHitArea)) return;
        markInteraction();
        model.motion(behavior.tapMotionGroup);
    };

    canvas.addEventListener("wheel", handleWheel, { passive: false });
    canvas.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
    window.addEventListener("blur", handlePointerUp);
    model.on("hit", handleHit);

    return {
        model,
        markInteraction,
        dispose: () => {
            window.clearInterval(idleTimer);
            document.removeEventListener("visibilitychange", handleVisibilityChange);
            persistViewState();
            window.removeEventListener("resize", fitModel);
            canvas.removeEventListener("wheel", handleWheel);
            canvas.removeEventListener("pointerdown", handlePointerDown);
            window.removeEventListener("pointermove", handlePointerMove);
            window.removeEventListener("pointerup", handlePointerUp);
            window.removeEventListener("pointercancel", handlePointerUp);
            window.removeEventListener("blur", handlePointerUp);
            model.off("hit", handleHit);
            model.destroy();
        },
    };
}
