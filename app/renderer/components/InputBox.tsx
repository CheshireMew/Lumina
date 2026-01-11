import React, { useState, useRef } from 'react';
import { Camera, Loader2 } from 'lucide-react';
import { events } from '../core/events';

interface InputBoxProps {
    onSend: (message: string) => void;
    disabled?: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled }) => {
    const [value, setValue] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim()) {
                // Interrupt AI if it's talking
                events.emit('core:interrupt', undefined);
                onSend(value.trim());
                setValue('');
            }
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

            // Call Backend
            // TODO: Use API_CONFIG.BASE_URL if available, or relative path
            const res = await fetch('http://127.0.0.1:8010/vision/analyze', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                const description = data.description;
                
                // Inject into prompt as System/User Context
                // For now, we prepend it to the message or auto-send it
                // Strategy: Auto-send a hidden system message or just fill the input?
                // Let's fill the input for transparency + allow user to edit
                const newPrompt = `[Image Context]: ${description}\n\n(User's question...?)`;
                setValue(prev => (prev ? prev + '\n' + newPrompt : newPrompt));
                
                // Focus back
                // (Optional: auto-send if we want)
            } else {
                console.error('Vision API failed');
                alert('Vision analysis failed. Check backend console.');
            }
        } catch (err) {
            console.error(err);
            alert('Failed to connect to Vision Service.');
        } finally {
            setIsAnalyzing(false);
            if (fileInputRef.current) fileInputRef.current.value = ''; // Reset
        }
    };

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
            {/* Wrapper acting as the 'Visual' Input Box */}
            <div style={{ 
                position: 'relative', 
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                padding: '8px 16px', // Adjusted padding
                borderRadius: '30px',
                border: '1px solid rgba(255,255,255,0.3)',
                backgroundColor: 'rgba(20, 20, 30, 0.6)',
                backdropFilter: 'blur(12px)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.3), 0 0 10px rgba(165, 180, 252, 0.2)',
                transition: 'all 0.3s ease'
            }}>
                <input
                    type="text"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled || isAnalyzing}
                    placeholder={isAnalyzing ? "Analyzing image..." : "Talk directly to Lumina..."}
                    style={{
                        flex: 1, // Take remaining space
                        background: 'transparent',
                        border: 'none',
                        color: 'white',
                        fontSize: '16px',
                        outline: 'none',
                        fontFamily: '"Microsoft YaHei", sans-serif',
                        minWidth: 0, // Prevent flex overflow
                        height: '36px' // Match height roughly
                    }}
                />

                {/* Hidden File Input */}
                <input 
                    type="file" 
                    ref={fileInputRef} 
                    style={{ display: 'none' }} 
                    accept="image/*"
                    onChange={handleImageUpload}
                />

                {/* Camera / Upload Button */}
                <button 
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isAnalyzing || disabled}
                    style={{
                        marginLeft: '12px', // Space between input and button
                        background: 'rgba(255,255,255,0.1)', 
                        borderRadius: '50%',
                        border: '1px solid rgba(255,255,255,0.2)',
                        color: isAnalyzing ? '#818cf8' : 'rgba(255,255,255,0.8)',
                        cursor: 'pointer',
                        padding: '0',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.2s',
                        width: '36px',
                        height: '36px',
                        flexShrink: 0 // Don't shrink
                    }}
                    title="Upload Image for Analysis"
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.2)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'}
                >
                    {isAnalyzing ? <Loader2 size={18} className="animate-spin" /> : <Camera size={18} />}
                </button>
            </div>
        </div>
    );
};

export default InputBox;
