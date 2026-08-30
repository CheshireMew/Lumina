import { useEffect, useRef, useState } from "react";

import { events } from "../core/events";
import { connectSttStream } from "../runtime/sttStreamClient";

type VoiceStatus = "idle" | "listening" | "thinking";

interface UseVoiceInputSessionArgs {
    chatMode: "text" | "voice";
    voiceCapabilityState: string;
    onFinalText: (text: string) => void;
    onSpeechStart?: () => void;
}

const emotionMap: Record<string, string> = {
    "<|HAPPY|>": "Happy",
    "<|SAD|>": "Sad",
    "<|ANGRY|>": "Angry",
    "<|NEUTRAL|>": "Neutral",
    "<|FEAR|>": "Fear",
    "<|SURPRISE|>": "Surprise",
};

const formatTranscript = (text: string, emotion?: string) => {
    const displayText = text.replace(/<\|[A-Z]+\|>/g, "").trim();
    if (!emotion) {
        return { displayText, finalText: text };
    }

    const readableEmotion = emotionMap[emotion] || emotion;
    return {
        displayText,
        finalText: `(User emotion: ${readableEmotion}) ${displayText}`,
    };
};

export const useVoiceInputSession = ({
    chatMode,
    voiceCapabilityState,
    onFinalText,
    onSpeechStart,
}: UseVoiceInputSessionArgs) => {
    const [vadStatus, setVadStatus] = useState<VoiceStatus>("idle");
    const [voiceError, setVoiceError] = useState("");
    const [transcript, setTranscript] = useState("");
    const wsRef = useRef<WebSocket | null>(null);
    const onFinalTextRef = useRef(onFinalText);
    const onSpeechStartRef = useRef(onSpeechStart);
    const voiceCapabilityAvailable = voiceCapabilityState === "ready";

    useEffect(() => {
        onFinalTextRef.current = onFinalText;
        onSpeechStartRef.current = onSpeechStart;
    }, [onFinalText, onSpeechStart]);

    useEffect(() => {
        if (chatMode !== "voice") {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            setVoiceError("");
            setVadStatus("idle");
            return;
        }

        if (!voiceCapabilityAvailable) {
            setVoiceError(
                voiceCapabilityState === "starting"
                    ? "语音服务正在启动，请稍后再试"
                    : voiceCapabilityState === "offline"
                        ? "语音服务当前离线"
                        : "语音能力不可用",
            );
            setVadStatus("idle");
            return;
        }

        let ws: WebSocket | null = null;
        let isMounted = true;

        const connect = async () => {
            try {
                setVoiceError("正在启动语音服务…");
                ws = await connectSttStream();
                wsRef.current = ws;

                ws.onopen = () => {
                    if (!isMounted) return;
                    setVoiceError("");
                    setVadStatus("idle");
                };
                ws.onmessage = (event) => {
                    if (!isMounted) return;
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === "vad_status") {
                            setVadStatus(data.status);
                            if (data.status === "listening") {
                                events.emit("audio:vad.start", undefined);
                                onSpeechStartRef.current?.();
                            }
                            return;
                        }

                        if (data.type === "partial") {
                            setTranscript(data.text);
                            return;
                        }

                        if (data.type === "transcript" || data.type === "transcription") {
                            if (!data.text.trim()) {
                                return;
                            }
                            const { displayText, finalText } = formatTranscript(data.text, data.emotion);
                            setTranscript(displayText);
                            window.setTimeout(() => {
                                onFinalTextRef.current(finalText);
                                setTranscript("");
                            }, 500);
                            return;
                        }

                        if (data.type === "error") {
                            console.error("[VoiceInput] STT returned an error");
                            setVoiceError(data.message);
                            setVadStatus("idle");
                        }
                    } catch {
                        console.warn("[VoiceInput] Could not parse an STT message");
                    }
                };
                ws.onerror = () => {
                    if (!isMounted) return;
                    console.error("[VoiceInput] STT WebSocket connection failed");
                    setVoiceError("语音连接失败");
                };
                ws.onclose = () => {
                    if (!isMounted) return;
                    setVadStatus("idle");
                    setVoiceError("语音连接已断开");
                    if (wsRef.current === ws) {
                        wsRef.current = null;
                    }
                };
            } catch {
                console.error("[VoiceInput] STT initialization failed");
                if (isMounted) {
                    setVoiceError("语音服务初始化失败");
                }
            }
        };

        void connect();
        return () => {
            isMounted = false;
            if (wsRef.current === ws) {
                wsRef.current = null;
            }
            ws?.close();
        };
    }, [chatMode, voiceCapabilityAvailable, voiceCapabilityState]);

    return {
        vadStatus,
        voiceError,
        transcript,
        setVoiceError,
    };
};
