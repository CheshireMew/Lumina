import React, { useState, useEffect, useRef } from 'react';

interface ChatBubbleProps {
    message: string;
    isStreaming?: boolean;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({ message, isStreaming = false }) => {
    const [displayedText, setDisplayedText] = useState('');
    const wasStreamingRef = useRef(false);

    useEffect(() => {
        if (isStreaming) {
            // 流式模式：直接同步显示
            setDisplayedText(message);
            wasStreamingRef.current = true;
        } else if (wasStreamingRef.current) {
            // 流式刚结束：保持当前文本，不重新触发
            wasStreamingRef.current = false;
        } else if (message) {
            // 非流式模式：打字机效果
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
    }, [message, isStreaming]);

    if (!message) return null;

    return (
        <div style={{
            position: 'absolute',
            top: '15%',
            left: '75%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            padding: '15px 20px',
            borderRadius: '20px 20px 20px 5px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
            maxWidth: '400px',
            maxHeight: '300px',
            overflowY: 'auto',
            wordWrap: 'break-word',
            whiteSpace: 'pre-wrap',
            fontSize: '16px',
            lineHeight: '1.6',
            color: '#333',
            fontFamily: '"Microsoft YaHei", sans-serif',
            backdropFilter: 'blur(5px)',
            border: '1px solid rgba(255,255,255,0.5)',
            animation: 'fadeIn 0.3s ease-out'
        }}>
            {displayedText.replace(/\[[^\]]+\]/g, '').replace(/[\(（][^)）]+[\)）]/g, '')}
        </div>
    );
};

export default ChatBubble;
