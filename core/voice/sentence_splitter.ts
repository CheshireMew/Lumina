/**
 * Sentence Splitter - 句子分割器
 * 监听 token 流，检测句子边界，触发 TTS 合成
 */

export class SentenceSplitter {
    private buffer: string = '';
    private onSentenceCallback: ((sentence: string) => void) | null = null;
    // 优化：添加逗号等短停顿符，提前触发 TTS (包含换行)
    private sentenceEndRegex = /[。！？.!?,，、；\n]$/;
    private minLength = 1; // 降低最小长度，避免丢失短句
    // 优化：降低超时时间，减少等待延迟（从 1500ms -> 800ms）
    private maxWaitMs = 800; // 最大等待时间（毫秒）
    private lastTokenTime = 0;
    private timeoutId: NodeJS.Timeout | null = null;

    constructor(onSentence: (sentence: string) => void) {
        this.onSentenceCallback = onSentence;
    }

    /**
     * 喂入一个 token
     */
    feedToken(token: string) {
        this.buffer += token;
        this.lastTokenTime = Date.now();

        // 清除旧的超时定时器
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
        }

        // 检测句子结束
        const trimmedBuffer = this.buffer.trim();
        if (this.sentenceEndRegex.test(trimmedBuffer)) {
            // 确保句子不为空且有实际内容
            if (trimmedBuffer.length >= this.minLength) {
                this.emit(trimmedBuffer);
                this.buffer = '';
                return;
            }
        }

        // 设置超时保护：如果长时间没有新 token，强制输出
        this.timeoutId = setTimeout(() => {
            const trimmed = this.buffer.trim();
            if (trimmed.length > 0) {
                console.log('[SentenceSplitter] Timeout triggered, flushing buffer');
                this.emit(trimmed);
                this.buffer = '';
            }
        }, this.maxWaitMs);
    }

    /**
     * 强制输出当前缓存（流结束时调用）
     */
    flush() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        if (this.buffer.trim().length > 0) {
            console.log('[SentenceSplitter] Flushing remaining buffer');
            this.emit(this.buffer.trim());
            this.buffer = '';
        }
    }

    /**
     * 重置状态
     */
    reset() {
        this.buffer = '';
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
    }

    private emit(sentence: string) {
        if (this.onSentenceCallback) {
            console.log(`[SentenceSplitter] Emitting sentence: "${sentence}"`);
            this.onSentenceCallback(sentence);
        }
    }
}
