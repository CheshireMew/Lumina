import React, { useState, useEffect, useRef } from 'react';

interface ChatBubbleProps {
    message: string;
    isStreaming?: boolean;
    reasoning?: string;
    embedded?: boolean; // New prop
}

const ChatBubble: React.FC<ChatBubbleProps> = ({ message, isStreaming = false, reasoning, embedded = false }) => {
    const [displayedText, setDisplayedText] = useState('');
    const wasStreamingRef = useRef(false);

    useEffect(() => {
        // [Fix] Simplified logic to prevent double-rendering during streaming
        if (isStreaming) {
            // During streaming: Just show the message directly
            setDisplayedText(message);
            wasStreamingRef.current = true;
        } else {
            if (wasStreamingRef.current) {
                // Stream just ended: Show final message directly (no animation)
                setDisplayedText(message);
                wasStreamingRef.current = false;
            } else if (message && message !== displayedText) {
                // New non-streaming message: Show directly without typewriter
                // Typewriter animation was causing duplication issues
                setDisplayedText(message);
            }
        }
    }, [message, isStreaming]);

    if (!message && !embedded) return null; // In embedded mode, maybe we still want to show the area? Or just empty? 

    // If embedded, we strip the container styles
    if (embedded) {
        return (
            <div style={{
                position: 'relative',
                width: '100%',
                padding: '10px 0', 
                overflowWrap: 'break-word',
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap',
                fontSize: '16px',
                lineHeight: '1.6',
                color: '#374151', // Dark Gray text
                fontFamily: '"Microsoft YaHei", "Segoe UI", sans-serif',
                animation: 'fadeIn 0.3s ease-out',
            }}>
                {/* 🧠 Thinking Process Block */}
                {reasoning && (
                    <div style={{ 
                        marginBottom: '16px', 
                        padding: '12px', 
                        backgroundColor: 'rgba(255, 255, 255, 0.5)', 
                        borderRadius: '12px',
                        borderLeft: '4px solid #8b5cf6', 
                        fontSize: '0.9em',
                        color: '#6b7280'
                    }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px', color: '#7c3aed' }}>
                            <span>🧠</span> DeepSeek Thinking...
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'Consolas, monospace', opacity: 0.9, maxHeight: '200px', overflowY: 'auto' }}>
                            {reasoning}
                        </div>
                    </div>
                )}
                
                {/* Main Content */}
                {displayedText}
            </div>
        );
    }

    if (!message) return null;

    return (
        <div style={{
            position: 'absolute',
            top: '20%',
            left: '20px',
            transform: 'none',
            backgroundColor: 'rgba(255, 255, 255, 0.75)', // White Frosted
            padding: '16px 24px',
            borderRadius: '24px',
            boxShadow: '0 8px 32px rgba(31, 38, 135, 0.15)', // Softer shadow
            maxWidth: '450px',
            maxHeight: '70vh',
            overflowY: 'auto',
            overflowWrap: 'break-word',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            fontSize: '16px',
            lineHeight: '1.6',
            color: '#374151', // Dark Gray text
            fontFamily: '"Microsoft YaHei", "Segoe UI", sans-serif',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.4)', // Subtle white border
            animation: 'fadeIn 0.3s ease-out',
            zIndex: 100,
        }}>
            {/* Same reasoning block for standalone - duplicated for clarity or extractable */}
            {reasoning && (
                <div style={{ 
                    marginBottom: '16px', 
                    padding: '12px', 
                    backgroundColor: 'rgba(255, 255, 255, 0.5)', 
                    borderRadius: '12px',
                    borderLeft: '4px solid #8b5cf6', 
                    fontSize: '0.9em',
                    color: '#6b7280'
                }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px', color: '#7c3aed' }}>
                        <span>🧠</span> DeepSeek Thinking...
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'Consolas, monospace', opacity: 0.9, maxHeight: '200px', overflowY: 'auto' }}>
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
