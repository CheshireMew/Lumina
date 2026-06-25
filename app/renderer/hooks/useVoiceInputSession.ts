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

        if (voiceCapabilityState !== "ready") {
            setVoiceError("语音能力未安装");
            setVadStatus("idle");
            return;
        }

        let ws: WebSocket | null = null;
        let isMounted = true;

        const connect = async () => {
            try {
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
                            console.error("[VoiceInput] STT error message", data);
                            setVoiceError(data.message);
                            setVadStatus("idle");
                        }
                    } catch (error) {
                        console.warn("WebSocket message parse error:", error);
                    }
                };
                ws.onerror = (event) => {
                    if (!isMounted) return;
                    console.error("[VoiceInput] STT WebSocket error", event);
                    setVoiceError("Connection Failed");
                };
                ws.onclose = () => {
                    if (!isMounted) return;
                    setVadStatus("idle");
                    setVoiceError("语音连接已断开");
                    if (wsRef.current === ws) {
                        wsRef.current = null;
                    }
                };
            } catch (error) {
                console.error("[VoiceInput] STT init failed", error);
                if (isMounted) {
                    setVoiceError("Init Failed");
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
    }, [chatMode, voiceCapabilityState]);

    return {
        vadStatus,
        voiceError,
        transcript,
        setVoiceError,
    };
};
