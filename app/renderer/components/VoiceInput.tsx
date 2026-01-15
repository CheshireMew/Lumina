import React, { useState, useEffect, useRef } from 'react';
import { events } from '../core/events';

interface VoiceInputProps {
    onSend: (message: string) => void;
    disabled?: boolean;
    onSpeechStart?: () => void;
}

const VoiceInput: React.FC<VoiceInputProps> = ({ onSend, disabled, onSpeechStart }) => {
    const [vadStatus, setVadStatus] = useState<'idle' | 'listening' | 'thinking'>('idle');
    const [error, setError] = useState<string>('');
    const [transcript, setTranscript] = useState<string>('');
    const [enabled, setEnabled] = useState<boolean>(true);

    const wsRef = useRef<WebSocket | null>(null);
    const onSendRef = useRef(onSend);
    const onSpeechStartRef = useRef(onSpeechStart);

    useEffect(() => {
        onSendRef.current = onSend;
        onSpeechStartRef.current = onSpeechStart;
    }, [onSend, onSpeechStart]);

    useEffect(() => {
        if (!enabled) return;

        let ws: WebSocket | null = null;
        const connectWS = async () => {
            try {
                const wsUrl = await window.stt.getWSUrl();
                ws = new WebSocket(wsUrl);
                wsRef.current = ws;

                ws.onopen = () => {
                    console.log('[VoiceInput] WebSocket connected');
                    setError('');
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'vad_status') {
                        console.log('[VAD Status]', data.status);
                        setVadStatus(data.status);

                        if (data.status === 'listening') {
                             console.log('[VAD] User speaking, emitting event...');
                             events.emit('audio:vad.start', undefined);
                             
                             if (onSpeechStartRef.current) {
                                 onSpeechStartRef.current();
                             }
                        }
                    }
                    else if (data.type === 'partial') {
                        console.log('[STT] Partial:', data.segment);
                        setTranscript(data.text);
                    }
                    else if (data.type === 'transcript' || data.type === 'transcription') {
                        console.log('[STT] Final:', data.text);

                        if (data.text.trim()) {
                            // Extract Emotion if available
                            let finalText = data.text;
                            
                            // 1. Remove raw XML-like tags from display text if present (e.g. <|HAPPY|>)
                            const displayText = data.text.replace(/<\|[A-Z]+\|>/g, '').trim();
                            setTranscript(displayText);

                            // 2. Inject emotion into LLM context
                            if (data.emotion) {
                                // Map SenseVoice tags to human readable
                                // <|HAPPY|> -> Happy
                                const emotionMap: Record<string, string> = {
                                    '<|HAPPY|>': 'Happy',
                                    '<|SAD|>': 'Sad',
                                    '<|ANGRY|>': 'Angry',
                                    '<|NEUTRAL|>': 'Neutral',
                                    '<|FEAR|>': 'Fear',
                                    '<|SURPRISE|>': 'Surprise'
                                };
                                const readableEmotion = emotionMap[data.emotion] || data.emotion;
                                finalText = `(User emotion: ${readableEmotion}) ${displayText}`;
                            }

                            setTimeout(() => {
                                onSendRef.current(finalText);
                                setTranscript('');
                            }, 500);
                        }
                    }
                    else if (data.type === 'error') {
                        setError(data.message);
                        setVadStatus('idle');
                    }
                };

                ws.onclose = () => {
                    console.log('[VoiceInput] WebSocket closed');
                };

                ws.onerror = () => {
                    setError('无法连接语音服务');
                };

            } catch (e) {
                console.error(e);
                setError('初始化失败');
            }
        };

        connectWS();

        return () => {
            if (ws) ws.close();
        };
    }, [enabled]);

    const getStatusText = () => {
        if (!enabled) return 'Mic Disabled';
        if (error) return error;
        if (vadStatus === 'thinking') return 'Thinking...';
        if (vadStatus === 'listening') return 'Listening...';
        return 'Ready';
    };

    const getIconColor = () => {
        if (!enabled) return '#666666';
        if (error) return '#ff6b6b';
        if (vadStatus === 'thinking') return '#ffa502';
        if (vadStatus === 'listening') return '#ff4757';
        return 'rgba(255,255,255,0.6)';
    };

    const toggleMic = () => {
        setEnabled(!enabled);
        if (enabled) {
            setVadStatus('idle');
            setTranscript('');
        }
    };

    return (
        <div style={{
            position: 'absolute',
            bottom: '30px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 10
        }}>
            {transcript && enabled && (
                <div style={{
                    maxWidth: '300px',
                    padding: '10px 16px',
                    backgroundColor: 'rgba(0,0,0,0.75)',
                    borderRadius: '12px',
                    color: 'white',
                    fontSize: '13px',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255,255,255,0.1)',
                }}>
                    {transcript}
                </div>
            )}

            <div style={{
                color: 'white',
                fontSize: '14px',
                textShadow: '0 1px 2px black',
                fontWeight: 500,
                height: '20px'
            }}>
                {getStatusText()}
            </div>

            <div
                onClick={toggleMic}
                style={{
                    width: '60px',
                    height: '60px',
                    borderRadius: '50%',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    transform: vadStatus === 'listening' && enabled ? 'scale(1.1)' : 'scale(1)',
                    opacity: enabled ? 1 : 0.6,
                    // 磨砂效果 (Frosted Glass)
                    backgroundColor: 'rgba(128, 128, 128, 0.2)', // 灰色半透明
                    backdropFilter: 'blur(12px)', // 磨砂模糊
                    border: '1px solid rgba(255, 255, 255, 0.15)', // 微妙边框
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)', // 柔和阴影
                    // 聆听时增强光晕
                    filter: vadStatus === 'listening' ? `drop-shadow(0 0 8px ${getIconColor()})` : 'none'
                }}>
                {/* 
                   纯麦克风图标 (Pure Mic Icon Style)
                   无背景圆，仅保留线条/形状
                */}
                {!enabled ? (
                    // Disabled State
                    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
                        <rect x="9" y="4" width="6" height="11" rx="3" fill="#888" />
                        <path d="M5 11v1a7 7 0 0 0 14 0v-1" stroke="#888" strokeWidth="2" strokeLinecap="round" />
                        <line x1="12" y1="19" x2="12" y2="22" stroke="#888" strokeWidth="2" strokeLinecap="round" />
                        <line x1="8" y1="22" x2="16" y2="22" stroke="#888" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                ) : vadStatus === 'listening' ? (
                    // Listening State (Red active)
                    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
                        <rect x="9" y="4" width="6" height="11" rx="3" fill="#ff4444" />
                        <path d="M5 11v1a7 7 0 0 0 14 0v-1" stroke="#ff4444" strokeWidth="2" strokeLinecap="round" />
                        <line x1="12" y1="19" x2="12" y2="22" stroke="#ff4444" strokeWidth="2" strokeLinecap="round" />
                        <line x1="8" y1="22" x2="16" y2="22" stroke="#ff4444" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                ) : vadStatus === 'thinking' ? (
                    // Thinking State (Mic shape with loading accent)
                    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
                        <rect x="9" y="4" width="6" height="11" rx="3" fill="#ccc" opacity="0.5" />
                        <path d="M12 2 a 10 10 0 0 1 10 10" stroke="#fff" strokeWidth="2" strokeLinecap="round" fill="none">
                            <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite" />
                        </path>
                    </svg>
                ) : (
                    // Ready State (White)
                    <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
                        <rect x="9" y="4" width="6" height="11" rx="3" fill="white" />
                        <path d="M5 11v1a7 7 0 0 0 14 0v-1" stroke="white" strokeWidth="2" strokeLinecap="round" />
                        <line x1="12" y1="19" x2="12" y2="22" stroke="white" strokeWidth="2" strokeLinecap="round" />
                        <line x1="8" y1="22" x2="16" y2="22" stroke="white" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                )}
            </div>
        </div>
    );
};

export default VoiceInput;
