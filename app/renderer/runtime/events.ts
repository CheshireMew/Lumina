export type RuntimeEventMap = {
    emotion: { emotion: string };
};

const RUNTIME_EVENT_NAMES: Record<keyof RuntimeEventMap, string> = {
    emotion: "lumina:emotion",
};

export function emitRuntimeEvent<K extends keyof RuntimeEventMap>(
    name: K,
    detail: RuntimeEventMap[K],
): void {
    window.dispatchEvent(
        new CustomEvent(RUNTIME_EVENT_NAMES[name], {
            detail,
        }),
    );
}

export function subscribeRuntimeEvent<K extends keyof RuntimeEventMap>(
    name: K,
    handler: (detail: RuntimeEventMap[K]) => void,
): () => void {
    const eventName = RUNTIME_EVENT_NAMES[name];
    const listener = (event: Event) => {
        handler((event as CustomEvent<RuntimeEventMap[K]>).detail);
    };

    window.addEventListener(eventName, listener);
    return () => window.removeEventListener(eventName, listener);
}
