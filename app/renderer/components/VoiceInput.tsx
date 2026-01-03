import React, { useState, useEffect, useRef } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';

interface VoiceInputProps {
    onSend: (message: string) => void;
    disabled?: boolean;
}

// 辅助函数：Float32Array -> Int16Array
const floatTo16BitPCM = (input: Float32Array) => {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
        const s = Math.max(-1, Math.min(1, input[i]));
        output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return output;
};

const VoiceInput: React.FC<VoiceInputProps> = ({ onSend, disabled }) => {
    const [transcribing, setTranscribing] = useState(false);
    const [error, setError] = useState<string>('');
    const [transcript, setTranscript] = useState<string>('');

    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        let ws: WebSocket | null = null;
        const connectWS = async () => {
            try {
                const wsUrl = await (window as any).stt.getWSUrl();
                ws = new WebSocket(wsUrl);
                wsRef.current = ws;

                ws.onopen = () => {
                    console.log('[VoiceInput] WebSocket connected');
                    setError('');
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'transcript') {
                        console.log('Transcript:', data.text);
                        setTranscribing(false);
                        if (data.text.trim()) {
                            setTranscript(data.text);
                            setTimeout(() => {
                                onSend(data.text);
                                setTranscript('');
                            }, 500);
                        }
                    } else if (data.type === 'error') {
                        setError(data.message);
                        setTranscribing(false);
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
    }, [onSend]);

    const vad = useMicVAD({
        startOnLoad: true,
        positiveSpeechThreshold: 0.8,
        // minSpeechFrames 已过时，移除或使用 minSpeechMs (如果不确定属性名，直接用默认值即可)
        // 根据报错提示，可能是 minSpeechMs，但为了安全起见，我们先省略，使用默认值

        workletURL: "/vad.worklet.bundle.min.js",
        modelURL: "/silero_vad_v5.onnx",
        ortConfig(ort: any) {
            ort.env.wasm.wasmPaths = "/";
            ort.env.wasm.numThreads = 1;
            ort.env.wasm.proxy = false;
        },
        onSpeechStart: () => {
            console.log('Speech started');
            setTranscript('');
        },
        onSpeechEnd: (audio: Float32Array) => {
            console.log('Speech ended, sending audio...', audio.length);
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                setTranscribing(true);
                // 使用自定义转换函数
                const pcm16 = floatTo16BitPCM(audio);
                wsRef.current.send(pcm16.buffer);
            }
        },
        onVADMismatch: () => {
            console.warn('VAD Mismatch');
        }
    } as any);

    const getStatusText = () => {
        if (vad.loading) return 'Loading VAD...';
        if (vad.errored) return 'VAD Error';
        if (error) return error;
        if (transcribing) return 'Thinking...';
        if (vad.userSpeaking) return 'Listening...';
        return 'Ready';
    };

    const getIconColor = () => {
        if (error || vad.errored) return '#ff6b6b';
        if (transcribing) return '#ffa502';
        if (vad.userSpeaking) return '#ff4757';
        return 'rgba(255,255,255,0.6)';
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
            <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                border: `3px solid ${getIconColor()}`,
                backgroundColor: 'rgba(0,0,0,0.7)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontSize: '28px',
                boxShadow: vad.userSpeaking ? `0 0 20px ${getIconColor()}` : '0 4px 10px rgba(0,0,0,0.3)',
                transition: 'all 0.2s ease',
                transform: vad.userSpeaking ? 'scale(1.1)' : 'scale(1)',
            }}>
                {transcribing ? '⏳' : vad.userSpeaking ? '🎤' : '⚪'}
            </div>

            <div style={{
                color: 'white',
                fontSize: '14px',
                textShadow: '0 1px 2px black',
                fontWeight: 500,
                height: '20px'
            }}>
                {getStatusText()}
            </div>

            {transcript && (
                <div style={{
                    maxWidth: '300px',
                    padding: '8px 12px',
                    backgroundColor: 'rgba(0,0,0,0.7)',
                    borderRadius: '8px',
                    color: 'white',
                    fontSize: '12px',
                    marginTop: '5px'
                }}>
                    {transcript}
                </div>
            )}
        </div>
    );
};

export default VoiceInput;
