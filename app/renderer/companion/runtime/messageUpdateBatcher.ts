export interface StreamMessageBuffer {
    raw: string;
    reasoning: string;
}

type CommitUpdate = (turnId: string, buffer: StreamMessageBuffer) => void;
type RequestFrame = (callback: FrameRequestCallback) => number;
type CancelFrame = (handle: number) => void;

export class FrameMessageUpdateBatcher {
    private readonly pending = new Map<string, StreamMessageBuffer>();
    private frame: number | null = null;

    constructor(
        private readonly commit: CommitUpdate,
        private readonly requestFrame: RequestFrame = window.requestAnimationFrame.bind(window),
        private readonly cancelFrame: CancelFrame = window.cancelAnimationFrame.bind(window),
    ) {}

    queue(turnId: string, buffer: StreamMessageBuffer): void {
        this.pending.set(turnId, buffer);
        if (this.frame === null) {
            this.frame = this.requestFrame(() => {
                this.frame = null;
                this.flush();
            });
        }
    }

    flush(): void {
        if (this.frame !== null) {
            this.cancelFrame(this.frame);
            this.frame = null;
        }
        for (const [turnId, buffer] of this.pending) {
            this.commit(turnId, buffer);
        }
        this.pending.clear();
    }

    drop(turnId: string): void {
        this.pending.delete(turnId);
    }

    clear(): void {
        if (this.frame !== null) {
            this.cancelFrame(this.frame);
            this.frame = null;
        }
        this.pending.clear();
    }
}
