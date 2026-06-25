import React, { useState, useRef } from 'react';
import { Camera, Loader2, Mic, Keyboard, Send } from 'lucide-react';
import { events } from '../core/events';
import { useVisionUpload } from '../hooks/useVisionUpload';
import { useVoiceInputSession } from '../hooks/useVoiceInputSession';

interface InputBoxProps {
    onSend: (message: string) => void;
    disabled?: boolean;
    embedded?: boolean;
    chatMode: 'text' | 'voice';
    onToggleChatMode: () => void;
    onSpeechStart?: () => void;
    visionBaseUrl: string;
    voiceCapabilityState?: string;
    visionCapabilityState?: string;
}

const InputBox: React.FC<InputBoxProps> = ({ 
    onSend, 
    disabled, 
    embedded = false, 
    chatMode,
    onToggleChatMode,
    onSpeechStart,
    visionBaseUrl,
    voiceCapabilityState = 'ready',
    visionCapabilityState = 'ready',
}) => {
    // --- Text State ---
    const [value, setValue] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { isAnalyzing, analyze } = useVisionUpload(visionBaseUrl, visionCapabilityState);

    const { vadStatus, voiceError, transcript, setVoiceError } = useVoiceInputSession({
        chatMode,
        voiceCapabilityState,
        onFinalText: onSend,
        onSpeechStart,
    });

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
        if (visionCapabilityState !== 'ready') {
            alert('视觉能力未安装');
            if (fileInputRef.current) fileInputRef.current.value = '';
            return;
        }
        try {
            const description = await analyze(file);
            setValue(prev => (prev ? prev + '\n' + `[Image Context]: ${description}` : `[Image Context]: ${description}`));
        } catch (err) {
            console.error('[InputBox] Vision analysis failed', err);
            alert(err instanceof Error ? err.message : 'Failed to connect to Vision Service.');
        } finally {
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
                    onClick={() => {
                        if (chatMode === 'text' && voiceCapabilityState !== 'ready') {
                            setVoiceError('语音能力未安装');
                            return;
                        }
                        onToggleChatMode();
                    }}
                    title={chatMode === 'text' ? '切换到语音' : '切换到文字'}
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
                    disabled={isAnalyzing || disabled || visionCapabilityState !== 'ready'}
                    title={visionCapabilityState === 'ready' ? '上传图片' : '视觉能力未安装'}
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
