import React, { useEffect, useState, useRef } from 'react';
import type { ChatAttachment, ChatSendRequest } from '@core/llm/types';
import { Camera, Keyboard, Loader2, Mic, Send, Square, Volume2, VolumeX, X } from 'lucide-react';
import { useVisionUpload } from '../hooks/useVisionUpload';
import { useVoiceInputSession } from '../hooks/useVoiceInputSession';

interface InputBoxProps {
    onSend: (message: string | ChatSendRequest) => boolean | void;
    onInterrupt?: () => void;
    disabled?: boolean;
    isProcessing?: boolean;
    isTtsEnabled?: boolean;
    onToggleTts?: () => void;
    embedded?: boolean;
    chatMode: 'text' | 'voice';
    onToggleChatMode: () => void;
    onSpeechStart?: () => void;
    visionBaseUrl: string;
    voiceCapabilityState?: string;
    visionCapabilityState?: string;
    visionCapabilityError?: string | null;
}

const InputBox: React.FC<InputBoxProps> = ({ 
    onSend, 
    onInterrupt,
    disabled, 
    isProcessing = false,
    isTtsEnabled = true,
    onToggleTts,
    embedded = false, 
    chatMode,
    onToggleChatMode,
    onSpeechStart,
    visionBaseUrl,
    voiceCapabilityState = 'ready',
    visionCapabilityState = 'ready',
    visionCapabilityError,
}) => {
    // --- Text State ---
    const [value, setValue] = useState('');
    const [attachment, setAttachment] = useState<ChatAttachment | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textAreaRef = useRef<HTMLTextAreaElement>(null);
    const { isAnalyzing, analyze } = useVisionUpload(
        visionBaseUrl,
        visionCapabilityState,
        visionCapabilityError,
    );
    const visionUnavailableMessage = visionCapabilityError || '视觉能力尚未就绪';

    const { vadStatus, voiceError, transcript, setVoiceError } = useVoiceInputSession({
        chatMode,
        voiceCapabilityState,
        onFinalText: onSend,
        onSpeechStart,
    });

    useEffect(() => {
        const input = textAreaRef.current;
        if (!input) return;
        input.style.height = 'auto';
        input.style.height = `${Math.min(Math.max(input.scrollHeight, 40), 96)}px`;
    }, [value]);

    // --- Handlers ---
    const handleSend = () => {
        if (value.trim() || attachment) {
            const visibleText = value.trim();
            const accepted = attachment
                ? onSend({
                    displayText: visibleText,
                    requestText: [
                        visibleText,
                        `用户附加了一张图片（${attachment.name}）。图片分析结果：${attachment.description}`,
                    ].filter(Boolean).join('\n\n'),
                    attachments: [attachment],
                })
                : onSend(visibleText);
            if (accepted !== false) {
                setValue('');
                setAttachment(null);
            }
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
            alert(visionUnavailableMessage);
            if (fileInputRef.current) fileInputRef.current.value = '';
            return;
        }
        try {
            const description = await analyze(file);
            const previewUrl = await new Promise<string>((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(String(reader.result || ""));
                reader.onerror = () => reject(new Error("无法读取图片预览"));
                reader.readAsDataURL(file);
            });
            setAttachment({
                id: crypto.randomUUID(),
                type: "image",
                name: file.name,
                previewUrl,
                description,
            });
        } catch (err) {
            console.error('[InputBox] Vision analysis failed', err);
            alert(err instanceof Error ? err.message : '无法连接视觉服务');
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
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', minWidth: 0, minHeight: '40px' }}>
                {chatMode === 'text' ? (
                    <textarea
                        ref={textAreaRef}
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={disabled || isAnalyzing}
                        placeholder={isAnalyzing ? "正在分析图片…" : "和 Lumina 说点什么…"}
                        aria-label="消息输入"
                        rows={1}
                        style={{
                            width: '100%',
                            background: 'transparent',
                            border: 'none',
                            color: '#374151',
                            fontSize: '16px',
                            outline: 'none',
                            fontFamily: '"Microsoft YaHei", sans-serif',
                            minHeight: '40px',
                            maxHeight: '96px',
                            padding: '9px 0',
                            lineHeight: 1.45,
                            resize: 'none',
                            overflowY: 'auto'
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
                                vadStatus === 'listening' ? '正在聆听…' : (vadStatus === 'thinking' ? '正在处理…' : '可以开始说话')
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
                        if (
                            chatMode === 'text' &&
                            voiceCapabilityState !== 'ready'
                        ) {
                            setVoiceError(
                                voiceCapabilityState === 'starting'
                                    ? '语音服务正在启动，请稍后再试'
                                    : voiceCapabilityState === 'offline'
                                        ? '语音服务当前离线'
                                        : '语音能力不可用',
                            );
                            return;
                        }
                        onToggleChatMode();
                    }}
                    title={chatMode === 'text' ? '切换到语音' : '切换到文字'}
                    aria-label={chatMode === 'text' ? '切换到语音输入' : '切换到文字输入'}
                    disabled={disabled || isProcessing}
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
                    title={visionCapabilityState === 'ready' ? '上传图片' : visionUnavailableMessage}
                    aria-label="添加图片"
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

                {onToggleTts && (
                    <button
                        type="button"
                        onClick={onToggleTts}
                        title={isTtsEnabled ? '关闭回复朗读' : '开启回复朗读'}
                        aria-label={isTtsEnabled ? '关闭回复朗读' : '开启回复朗读'}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            padding: 8,
                            color: isTtsEnabled ? '#db2777' : '#6b7280',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        {isTtsEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
                    </button>
                )}

                {isProcessing ? (
                    <button
                        onClick={onInterrupt}
                        aria-label="停止生成"
                        title="停止生成"
                        style={{
                            width: 40,
                            height: 40,
                            borderRadius: '50%',
                            background: '#fff1f2',
                            border: '1px solid #fecdd3',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            color: '#e11d48',
                            marginLeft: 4,
                        }}
                    >
                        <Square size={15} fill="currentColor" />
                    </button>
                ) : chatMode === 'text' && (
                <button
                    onClick={handleSend}
                    aria-label="发送消息"
                    title="发送消息"
                    disabled={disabled || isAnalyzing || (!value.trim() && !attachment)}
                    style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        background: (value.trim() || attachment) ? 'linear-gradient(135deg, #f472b6 0%, #db2777 100%)' : '#e5e7eb',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: (value.trim() || attachment) ? 'pointer' : 'default',
                        color: 'white',
                        boxShadow: (value.trim() || attachment) ? '0 4px 12px rgba(219, 39, 119, 0.3)' : 'none',
                        transition: 'all 0.2s ease',
                        marginLeft: 4
                    }}
                    onMouseEnter={e => {
                        if (value.trim() || attachment) e.currentTarget.style.transform = 'scale(1.05)';
                    }}
                    onMouseLeave={e => {
                        if (value.trim() || attachment) e.currentTarget.style.transform = 'scale(1)';
                    }}
                >
                    <Send size={18} fill="white" />
                </button>
                )}
            </div>
        </div>
    );

    const attachmentPreview = attachment && (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 14px 0',
            borderTop: '1px solid rgba(15, 23, 42, 0.05)',
        }}>
            <img
                src={attachment.previewUrl}
                alt={attachment.name}
                style={{ width: 52, height: 52, objectFit: 'cover', borderRadius: 10, border: '1px solid rgba(15,23,42,.1)' }}
            />
            <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#334155', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {attachment.name}
                </div>
                <div style={{ fontSize: 12, color: '#64748b' }}>图片已就绪，将随消息一起发送</div>
            </div>
            <button
                type="button"
                onClick={() => setAttachment(null)}
                aria-label="移除图片"
                title="移除图片"
                style={{ border: 0, background: 'transparent', color: '#64748b', cursor: 'pointer', padding: 6 }}
            >
                <X size={18} />
            </button>
        </div>
    );

    if (embedded) return <>{attachmentPreview}{innerContent}</>;

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
            {attachmentPreview}
            {innerContent}
        </div>
    );
};

export default InputBox;
