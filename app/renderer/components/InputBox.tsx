import React, { useState, useRef, useEffect } from 'react';
import { Camera, Loader2, Mic, Keyboard, Send, X } from 'lucide-react';
import { events } from '../core/events';

interface InputBoxProps {
    onSend: (message: string) => void;
    disabled?: boolean;
    embedded?: boolean;
    chatMode: 'text' | 'voice';
    onToggleChatMode: () => void;
    onSpeechStart?: () => void;
}

const InputBox: React.FC<InputBoxProps> = ({ 
    onSend, 
    disabled, 
    embedded = false, 
    chatMode,
    onToggleChatMode,
    onSpeechStart 
}) => {
    // --- Text State ---
    const [value, setValue] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // --- Voice State ---
    const [vadStatus, setVadStatus] = useState<'idle' | 'listening' | 'thinking'>('idle');
    const [voiceError, setVoiceError] = useState<string>('');
    const [transcript, setTranscript] = useState<string>('');
    const wsRef = useRef<WebSocket | null>(null);
    const onSendRef = useRef(onSend);
    const onSpeechStartRef = useRef(onSpeechStart);

    // Sync Refs
    useEffect(() => {
        onSendRef.current = onSend;
        onSpeechStartRef.current = onSpeechStart;
    }, [onSend, onSpeechStart]);

    // --- Voice Logic ---
    useEffect(() => {
        if (chatMode !== 'voice') {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            return;
        }

        let ws: WebSocket | null = null;
        const connectWS = async () => {
            try {
                // @ts-ignore
                const wsUrl = await window.stt.getWSUrl();
                ws = new WebSocket(wsUrl);
                wsRef.current = ws;

                ws.onopen = () => setVoiceError('');
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'vad_status') {
                        setVadStatus(data.status);
                        if (data.status === 'listening') {
                             events.emit('audio:vad.start', undefined);
                             if (onSpeechStartRef.current) onSpeechStartRef.current();
                        }
                    } else if (data.type === 'partial') {
                        setTranscript(data.text);
                    } else if (data.type === 'transcript' || data.type === 'transcription') {
                        if (data.text.trim()) {
                            let finalText = data.text;
                            // Clean tags
                            const displayText = data.text.replace(/<\|[A-Z]+\|>/g, '').trim();
                            setTranscript(displayText);
                            
                            // Emotion handling
                            if (data.emotion) {
                                const emotionMap: Record<string, string> = {
                                    '<|HAPPY|>': 'Happy', '<|SAD|>': 'Sad', '<|ANGRY|>': 'Angry',
                                    '<|NEUTRAL|>': 'Neutral', '<|FEAR|>': 'Fear', '<|SURPRISE|>': 'Surprise'
                                };
                                const readableEmotion = emotionMap[data.emotion] || data.emotion;
                                finalText = `(User emotion: ${readableEmotion}) ${displayText}`;
                            }

                            setTimeout(() => {
                                onSendRef.current(finalText);
                                setTranscript('');
                            }, 500);
                        }
                    } else if (data.type === 'error') {
                        setVoiceError(data.message);
                        setVadStatus('idle');
                    }
                };
                ws.onerror = () => setVoiceError('Connection Failed');
            } catch (e) {
                console.error(e);
                setVoiceError('Init Failed');
            }
        };

        connectWS();
        return () => { if (ws) ws.close(); };
    }, [chatMode]);

    // --- Handlers ---
    const handleSend = () => {
        if (value.trim()) {
            events.emit('core:interrupt', undefined);
            onSend(value.trim());
            setValue('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setIsAnalyzing(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('prompt', 'Describe this image in detail.');
            const res = await fetch('http://127.0.0.1:8010/vision/analyze', { method: 'POST', body: formData });
            if (res.ok) {
                const data = await res.json();
                setValue(prev => (prev ? prev + '\n' + `[Image Context]: ${data.description}` : `[Image Context]: ${data.description}`));
            } else {
                alert('Vision analysis failed.');
            }
        } catch (err) {
            alert('Failed to connect to Vision Service.');
        } finally {
            setIsAnalyzing(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    // --- RENDER ---
    const micColor = voiceError ? '#ff6b6b' : (vadStatus === 'listening' ? '#ff4757' : (vadStatus === 'thinking' ? '#ffa502' : '#6b7280'));

    const innerContent = (
        <div style={embedded ? { 
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            padding: '8px 12px 8px 16px', // Less padding right for buttons
            borderTop: '1px solid rgba(0,0,0,0.05)',
            backgroundColor: 'transparent',
            gap: '12px'
        } : { 
            position: 'relative', 
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            padding: '8px 12px 8px 16px',
            borderRadius: '30px',
            border: '1px solid rgba(255, 255, 255, 0.5)',
            backgroundColor: 'rgba(255, 255, 255, 0.6)', 
            backdropFilter: 'blur(16px)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
            transition: 'all 0.3s ease',
            gap: '12px'
        }}>
            {/* 1. LEFT: Main Input / Visualizer */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', minWidth: 0, height: '40px' }}>
                {chatMode === 'text' ? (
                    <input
                        type="text"
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={disabled || isAnalyzing}
                        placeholder={isAnalyzing ? "Analyzing image..." : "Talk directly to Lumina..."}
                        style={{
                            width: '100%',
                            background: 'transparent',
                            border: 'none',
                            color: '#374151',
                            fontSize: '16px',
                            outline: 'none',
                            fontFamily: '"Microsoft YaHei", sans-serif',
                            height: '100%'
                        }}
                    />
                ) : (
                    // Voice Visualizer
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%', color: '#374151', height: '100%' }}>
                        <div style={{ 
                            width: 10, height: 10, borderRadius: '50%', 
                            backgroundColor: micColor,
                            boxShadow: vadStatus === 'listening' ? `0 0 10px ${micColor}` : 'none',
                            transition: 'all 0.2s'
                        }} />
                        <span style={{ fontSize: '15px', fontWeight: 500, opacity: 0.8, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {voiceError || transcript || (
                                vadStatus === 'listening' ? 'Listening...' : (vadStatus === 'thinking' ? 'Processing...' : 'Ready')
                            )}
                        </span>
                        
                        {/* Simple Waveform Animation */}
                        {vadStatus === 'listening' && (
                             <div style={{ display: 'flex', gap: 3, alignItems: 'center', height: 16, marginLeft: 8 }}>
                                <div className="animate-pulse" style={{ width: 3, height: 12, background: '#818cf8', borderRadius: 2, animationDuration: '0.6s' }}></div>
                                <div className="animate-pulse" style={{ width: 3, height: 16, background: '#6366f1', borderRadius: 2, animationDuration: '0.5s' }}></div>
                                <div className="animate-pulse" style={{ width: 3, height: 10, background: '#818cf8', borderRadius: 2, animationDuration: '0.7s' }}></div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* 2. RIGHT: Actions Group */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                
                {/* Toggle Mode */}
                <button
                    onClick={onToggleChatMode}
                    title={chatMode === 'text' ? 'Switch to Voice' : 'Switch to Text'}
                    style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 8,
                        color: '#6b7280',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: 0.7,
                        transition: 'opacity 0.2s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                    onMouseLeave={e => e.currentTarget.style.opacity = '0.7'}
                >
                    {chatMode === 'text' ? <Mic size={20} /> : <Keyboard size={20} />}
                </button>

                {/* Upload Image */}
                <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept="image/*" onChange={handleImageUpload} />
                <button 
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isAnalyzing || disabled}
                    title="Upload Image"
                    style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 8,
                        color: isAnalyzing ? '#818cf8' : '#6b7280',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: 0.7
                    }}
                    onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                    onMouseLeave={e => e.currentTarget.style.opacity = '0.7'}
                >
                    {isAnalyzing ? <Loader2 size={20} className="animate-spin" /> : <Camera size={20} />}
                </button>

                {/* Send Button (Colored Pill/Circle) */}
                <button
                    onClick={handleSend}
                    disabled={disabled || (!value.trim() && chatMode === 'text')} // Disable if empty in text mode
                    style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        background: (value.trim() || chatMode === 'voice') ? 'linear-gradient(135deg, #f472b6 0%, #db2777 100%)' : '#e5e7eb', // Pink gradient if active, gray if disabled
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: (value.trim() || chatMode === 'voice') ? 'pointer' : 'default',
                        color: 'white',
                        boxShadow: (value.trim() || chatMode === 'voice') ? '0 4px 12px rgba(219, 39, 119, 0.3)' : 'none',
                        transition: 'all 0.2s ease',
                        marginLeft: 4
                    }}
                    onMouseEnter={e => {
                        if (value.trim() || chatMode === 'voice') e.currentTarget.style.transform = 'scale(1.05)';
                    }}
                    onMouseLeave={e => {
                        if (value.trim() || chatMode === 'voice') e.currentTarget.style.transform = 'scale(1)';
                    }}
                >
                    <Send size={18} fill="white" />
                </button>
            </div>
        </div>
    );

    if (embedded) return innerContent;

    // Fallback wrapper for standalone usage (if ever used)
    return (
        <div style={{
            position: 'absolute',
            bottom: '50px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '80%',
            maxWidth: '600px',
            zIndex: 10
        }}>
            {innerContent}
        </div>
    );
};

export default InputBox;
