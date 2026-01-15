import React, { useState, useEffect, useRef } from 'react';

interface ChatBubbleProps {
    message: string;
    isStreaming?: boolean;
    reasoning?: string;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({ message, isStreaming = false, reasoning }) => {
    const [displayedText, setDisplayedText] = useState('');
    const wasStreamingRef = useRef(false);

    useEffect(() => {
        if (isStreaming) {
            // Streaming mode: Sync immediately
            setDisplayedText(message);
            wasStreamingRef.current = true;
        } else {
            // Not streaming
            if (wasStreamingRef.current) {
                // Just ended streaming: Sync final
                setDisplayedText(message);
                wasStreamingRef.current = false;
            } else if (message) {
                // Static message update
                if (displayedText && message.startsWith(displayedText)) {
                    // Just an append (late packet?), don't typewriter, just show
                    setDisplayedText(message);
                } else {
                    // New message (Typewriter effect)
                    setDisplayedText('');
                    let i = 0;
                    const timer = setInterval(() => {
                        if (i < message.length) {
                            setDisplayedText((prev) => prev + message.charAt(i));
                            i++;
                        } else {
                            clearInterval(timer);
                        }
                    }, 50);
                    return () => clearInterval(timer);
                }
            }
        }
    }, [message, isStreaming]);

    if (!message) return null;

    return (
        <div style={{
            position: 'absolute',
            top: '20%',
            left: '20px',
            transform: 'none',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            padding: '16px 24px',
            borderRadius: '24px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
            maxWidth: '450px',
            maxHeight: '70vh',
            overflowY: 'auto',
            overflowWrap: 'break-word',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            fontSize: '16px',
            lineHeight: '1.6',
            color: '#1f2937',
            fontFamily: '"Microsoft YaHei", "Segoe UI", sans-serif',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255,255,255,0.8)',
            animation: 'fadeIn 0.3s ease-out',
            zIndex: 100,
        }}>
            {/* 🧠 Thinking Process Block */}
            {reasoning && (
                <div style={{ 
                    marginBottom: '16px', 
                    padding: '12px', 
                    backgroundColor: 'rgba(243, 244, 246, 0.8)', 
                    borderRadius: '12px',
                    borderLeft: '4px solid #8b5cf6', // Purple accent for "Thinking"
                    fontSize: '0.9em',
                    color: '#4b5563'
                }}>
                    <div style={{ 
                        fontWeight: 'bold', 
                        marginBottom: '4px', 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '6px',
                        color: '#7c3aed'
                    }}>
                        <span>🧠</span> DeepSeek Thinking...
                    </div>
                    <div style={{ 
                        whiteSpace: 'pre-wrap', 
                        fontFamily: 'Consolas, monospace',
                        opacity: 0.9,
                        maxHeight: '200px',
                        overflowY: 'auto'
                    }}>
                        {reasoning}
                    </div>
                </div>
            )}
            
            {/* Main Content */}
            {displayedText}
        </div>
    );
};

export default ChatBubble;
