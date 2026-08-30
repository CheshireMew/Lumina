import React from 'react';
import { X } from 'lucide-react';

import { useDialogAccessibility } from '../hooks/useDialogAccessibility';

interface MotionTesterProps {
    onTriggerMotion: (group: string, index: number) => void;
    isOpen: boolean;
    onClose: () => void;
}

const MotionTester: React.FC<MotionTesterProps> = ({ onTriggerMotion, isOpen, onClose }) => {
    const dialogRef = useDialogAccessibility<HTMLDivElement>(isOpen, onClose);
    const idleMotions = [
        { index: 0, label: '标准 / 放松', emotion: '平静' },
        { index: 1, label: '微笑 / 思考', emotion: '开心 / 思考' },
        { index: 2, label: '害羞 / 脸红', emotion: '害羞' },
        { index: 3, label: '认真 / 担心', emotion: '严肃' },
        { index: 4, label: '开心 / 兴奋', emotion: '开心' },
        { index: 5, label: '惊讶 / 震惊', emotion: '惊讶' },
        { index: 6, label: '喜欢 / 亲近', emotion: '喜爱' },
        { index: 7, label: '生气 / 不耐烦', emotion: '生气' },
        { index: 8, label: '困倦 / 疲惫', emotion: '困倦' },
    ];

    if (!isOpen) return null;

    return (
        <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="motion-tester-title"
            tabIndex={-1}
            style={{
            position: 'fixed',
            top: 16,
            right: 16,
            width: 'min(300px, calc(100vw - 32px))',
            height: 'calc(100vh - 32px)',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '-2px 0 10px rgba(0,0,0,0.1)',
            zIndex: 999,
            padding: '20px',
            boxSizing: 'border-box',
            borderRadius: '18px',
            overflowY: 'auto',
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
            }}>
                <h2 id="motion-tester-title" style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: '#333' }}>
                    动作测试
                </h2>
                <button
                    onClick={onClose}
                    aria-label="关闭动作测试"
                    style={{
                        padding: '6px',
                        backgroundColor: 'transparent',
                        color: '#64748b',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                    }}
                >
                    <X size={20} />
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
                            待机动作 {motion.index}：{motion.label}
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
                <strong>说明：</strong>
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
