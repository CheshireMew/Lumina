/**
 * Memory Tab - 对话记忆设置
 */
import React from 'react';
import { buttonStyle, sectionTitleStyle } from '../styles';

interface MemoryTabProps {
    contextWindow: number;
    setContextWindow: (window: number) => void;
    onClearHistory?: () => void;
}

export const MemoryTab: React.FC<MemoryTabProps> = ({
    contextWindow, setContextWindow, onClearHistory
}) => {
    const handleClearHistory = () => {
        if (confirm('确定要清空所有对话历史吗？此操作不可恢复。')) {
            if (onClearHistory) onClearHistory();
            alert('对话历史已清空');
        }
    };

    return (
        <div>
            <h3 style={sectionTitleStyle}>Conversation Memory</h3>
            <div style={{ 
                backgroundColor: 'white', padding: '15px', 
                borderRadius: '8px', border: '1px solid #e5e7eb' 
            }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
                    Context Window: <strong>{contextWindow} turns</strong>
                </label>
                <input
                    type="range"
                    min="5"
                    max="50"
                    value={contextWindow}
                    onChange={(e) => setContextWindow(Number(e.target.value))}
                    style={{ width: '100%', accentColor: '#4f46e5' }}
                />
                <div style={{ marginTop: '20px' }}>
                    <button
                        onClick={handleClearHistory}
                        style={{ 
                            ...buttonStyle, 
                            backgroundColor: '#fee2e2', 
                            color: '#dc2626', 
                            border: '1px solid #fecaca' 
                        }}
                    >
                        Clear History & Reset
                    </button>
                </div>
            </div>
        </div>
    );
};

export default MemoryTab;
