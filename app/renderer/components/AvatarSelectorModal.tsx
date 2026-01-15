import React, { useState } from 'react';
import { X, User, Box, Layers, Image as ImageIcon } from 'lucide-react';
import { CharacterProfile } from '@core/llm/types';
import { API_CONFIG } from '../../config';

interface AvatarSelectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    activeCharacter: CharacterProfile | undefined;
    onModelSelect: (modelPath: string) => void;
}

// Hardcoded for now - ideally fetched from backend
const AVAILABLE_MODELS = [
    { name: 'Hiyori (Live2D)', path: '/live2d/Hiyori/Hiyori.model3.json', type: 'live2d', thumbnail: '/live2d/Hiyori/ico_00.png' },
    { name: 'Hiyori Mic (Live2D)', path: '/live2d/imported/Hiyori_Mic/hiyori_pro_mic.model3.json', type: 'live2d' },
    { name: 'Laffey II (Live2D)', path: '/live2d/imported/Laffey_II/Laffey Ⅱ.model3.json', type: 'live2d' },
    { name: 'Reimen (Live2D)', path: '/live2d/imported/Rei/Rei.model3.json', type: 'live2d' },
    { name: 'XiaoYue (VRM)', path: '/vrm/XiaoYue.vrm', type: 'vrm' },
    { name: 'Sprite Mode (2D)', path: '/sprites/default', type: 'sprite' },
];

const AvatarSelectorModal: React.FC<AvatarSelectorModalProps> = ({ isOpen, onClose, activeCharacter, onModelSelect }) => {
    if (!isOpen) return null;

    const [customPath, setCustomPath] = useState('');

    const handleSelect = (path: string) => {
        if (confirm('Verify: Switch avatar model? This will reload the character.')) {
            onModelSelect(path);
            onClose();
        }
    };

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            zIndex: 2000,
            backdropFilter: 'blur(5px)'
        }}>
            <div style={{
                backgroundColor: 'white',
                borderRadius: '16px',
                width: '600px',
                maxHeight: '80vh',
                display: 'flex', flexDirection: 'column',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
            }}>
                {/* Header */}
                <div style={{
                    padding: '20px', borderBottom: '1px solid #e5e7eb',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 10 }}>
                        <User size={24} />
                        Select Avatar
                    </h2>
                    <button onClick={onClose} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>
                        <X size={24} color="#6b7280" />
                    </button>
                </div>

                {/* Content */}
                <div style={{ padding: '20px', overflowY: 'auto' }}>
                    
                    {/* Active Info */}
                    <div style={{ marginBottom: 20, padding: 10, backgroundColor: '#f3f4f6', borderRadius: 8 }}>
                        <strong>Current Character:</strong> {activeCharacter?.name} <br/>
                        <span style={{ fontSize: '0.8em', color: '#666' }}>{activeCharacter?.modelPath}</span>
                    </div>

                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 10 }}>Available Models</h3>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 15 }}>
                        {AVAILABLE_MODELS.map((model, idx) => (
                            <div 
                                key={idx}
                                onClick={() => handleSelect(model.path)}
                                style={{
                                    border: activeCharacter?.modelPath === model.path ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                                    borderRadius: 12,
                                    padding: 10,
                                    cursor: 'pointer',
                                    textAlign: 'center',
                                    backgroundColor: activeCharacter?.modelPath === model.path ? '#eff6ff' : 'white',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <div style={{ 
                                    width: 48, height: 48, borderRadius: '50%', backgroundColor: '#e5e7eb', 
                                    margin: '0 auto 10px', display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    {model.type === 'vrm' ? <Box size={24} /> : 
                                     model.type === 'sprite' ? <ImageIcon size={24} /> :
                                     <Layers size={24} />}
                                </div>
                                <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{model.name}</div>
                                <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: 4 }}>{model.type.toUpperCase()}</div>
                            </div>
                        ))}
                    </div>

                    <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #e5e7eb' }} />

                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 10 }}>Custom Path</h3>
                    <div style={{ display: 'flex', gap: 10 }}>
                        <input 
                            type="text" 
                            placeholder="/models/my_avatar.vrm" 
                            value={customPath}
                            onChange={e => setCustomPath(e.target.value)}
                            style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db' }}
                        />
                        <button 
                            onClick={() => handleSelect(customPath)}
                            disabled={!customPath}
                            style={{
                                padding: '8px 16px', borderRadius: 6, border: 'none',
                                backgroundColor: '#3b82f6', color: 'white', cursor: 'pointer',
                                opacity: customPath ? 1 : 0.5
                            }}
                        >
                            Load
                        </button>
                    </div>
                     <p style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: 5 }}>
                        Supports <code>.vrm</code> (3D), <code>.model3.json</code> (Live2D), or folder path (Sprite).
                    </p>

                </div>
            </div>
        </div>
    );
};

export default AvatarSelectorModal;
