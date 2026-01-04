import React from 'react';

interface MotionTesterProps {
    onTriggerMotion: (group: string, index: number) => void;
    isOpen: boolean;
    onClose: () => void;
}

const MotionTester: React.FC<MotionTesterProps> = ({ onTriggerMotion, isOpen, onClose }) => {
    const idleMotions = [
        { index: 0, label: '默认/悲伤', emotion: 'neutral/sad' },
        { index: 1, label: '动作1 (思考)', emotion: 'thinking/思考' },
        { index: 2, label: '动作2 (可能是害羞)', emotion: 'shy?' },
        { index: 3, label: '动作3 (未知)', emotion: 'unknown' },
        { index: 4, label: '动作4 (开心)', emotion: 'happy/开心' },
        { index: 5, label: '动作5 (惊讶)', emotion: 'surprised/惊讶' },
        { index: 6, label: '动作6 (喜欢)', emotion: 'love/喜欢' },
        { index: 7, label: '动作7 (生气)', emotion: 'angry/生气' },
        { index: 8, label: '动作8 (困)', emotion: 'sleepy/困' },
    ];

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            right: isOpen ? 0 : '-320px',
            width: '300px',
            height: '100vh',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '-2px 0 10px rgba(0,0,0,0.1)',
            zIndex: 999,
            padding: '20px',
            overflowY: 'auto',
            transition: 'right 0.3s ease',
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
            }}>
                <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: '#333' }}>
                    🎭 动作测试器
                </h2>
                <button
                    onClick={onClose}
                    style={{
                        padding: '6px 12px',
                        fontSize: '14px',
                        backgroundColor: '#f44336',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                    }}
                >
                    ✕
                </button>
            </div>

            <p style={{ color: '#666', marginBottom: '16px', fontSize: '12px', lineHeight: '1.5' }}>
                点击测试动作，观察模型表现，找出正确映射
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {idleMotions.map(motion => (
                    <button
                        key={motion.index}
                        onClick={() => {
                            console.log(`[MotionTester] Triggering Idle motion ${motion.index}`);
                            onTriggerMotion('Idle', motion.index);
                        }}
                        style={{
                            padding: '10px 12px',
                            fontSize: '13px',
                            backgroundColor: '#2196F3',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.2s',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = '#1976D2';
                            e.currentTarget.style.transform = 'translateX(-4px)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = '#2196F3';
                            e.currentTarget.style.transform = 'translateX(0)';
                        }}
                    >
                        <div style={{ fontWeight: 'bold', marginBottom: '2px' }}>
                            Idle {motion.index}: {motion.label}
                        </div>
                        <div style={{ fontSize: '11px', opacity: 0.9 }}>
                            {motion.emotion}
                        </div>
                    </button>
                ))}
            </div>

            <div style={{
                marginTop: '16px',
                padding: '12px',
                backgroundColor: '#fff3cd',
                borderRadius: '6px',
                fontSize: '11px',
                lineHeight: '1.5',
            }}>
                <strong>📝 说明:</strong>
                <ol style={{ margin: '6px 0 0 0', paddingLeft: '16px' }}>
                    <li>逐个点击测试</li>
                    <li>记录实际表现</li>
                    <li>告诉我正确映射</li>
                </ol>
            </div>
        </div>
    );
};

export default MotionTester;
