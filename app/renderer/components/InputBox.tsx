import React, { useState } from 'react';

interface InputBoxProps {
    onSend: (message: string) => void;
    disabled?: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled }) => {
    const [value, setValue] = useState('');

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim()) {
                onSend(value.trim());
                setValue('');
            }
        }
    };

    return (
        <div style={{
            position: 'absolute',
            bottom: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '80%',
            maxWidth: '500px',
            zIndex: 10
        }}>
            <input
                type="text"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder="Say something to Lumina..."
                style={{
                    width: '100%',
                    padding: '12px 20px',
                    borderRadius: '25px',
                    border: '1px solid rgba(255,255,255,0.2)',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    fontSize: '16px',
                    outline: 'none',
                    backdropFilter: 'blur(10px)',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                    transition: 'all 0.3s ease'
                }}
            />
        </div>
    );
};

export default InputBox;
