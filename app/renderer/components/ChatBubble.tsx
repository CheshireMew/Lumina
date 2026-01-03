import React, { useState, useEffect } from 'react';

interface ChatBubbleProps {
    message: string;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
    const [displayedText, setDisplayedText] = useState('');

    useEffect(() => {
        setDisplayedText('');
        let i = 0;
        const timer = setInterval(() => {
            if (i < message.length) {
                setDisplayedText((prev) => prev + message.charAt(i));
                i++;
            } else {
                clearInterval(timer);
            }
        }, 50); // Typewriter speed

        return () => clearInterval(timer);
    }, [message]);

    if (!message) return null;

    return (
        <div style={{
            position: 'absolute',
            top: '20%',
            left: '60%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            padding: '15px 20px',
            borderRadius: '20px 20px 20px 5px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
            maxWidth: '300px',
            zIndex: 10,
            fontSize: '16px',
            lineHeight: '1.5',
            color: '#333',
            fontFamily: '"Microsoft YaHei", sans-serif',
            backdropFilter: 'blur(5px)',
            border: '1px solid rgba(255,255,255,0.5)',
            animation: 'fadeIn 0.3s ease-out'
        }}>
            {displayedText}
        </div>
    );
};

export default ChatBubble;
