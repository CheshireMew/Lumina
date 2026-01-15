import React from 'react';
import { Braces } from 'lucide-react';

interface EdgeDetailModalProps {
    detailEdge: any;
    onClose: () => void;
}

export const EdgeDetailModal: React.FC<EdgeDetailModalProps> = ({ detailEdge, onClose }) => {
    if (!detailEdge) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 10000, backdropFilter: 'blur(5px)'
        }} onClick={onClose}>
            <div 
                onClick={(e) => e.stopPropagation()}
                style={{
                    background: 'linear-gradient(135deg, rgba(30, 20, 50, 0.95), rgba(20, 10, 40, 0.98))',
                    border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '16px',
                    padding: '24px', maxWidth: '600px', width: '90%', maxHeight: '80vh', overflow: 'auto',
                    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h3 style={{ color: '#c084fc', margin: 0, fontSize: '18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Braces size={20} /> Edge Detail
                    </h3>
                    <button 
                        onClick={onClose}
                        style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', fontSize: '24px' }}
                    >×</button>
                </div>
                <pre style={{
                    background: 'rgba(0,0,0,0.3)', borderRadius: '10px', padding: '16px',
                    color: '#e2e8f0', fontSize: '12px', lineHeight: '1.6', overflow: 'auto',
                    fontFamily: 'Consolas, Monaco, monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-all'
                }}>
                    {JSON.stringify(detailEdge, null, 2)}
                </pre>
            </div>
        </div>
    );
};
