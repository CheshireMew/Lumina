import React, { useState, useEffect } from 'react';
import { Video, VideoOff, Camera } from 'lucide-react';
import { faceTracker } from '../core/avatar/FaceTracker';

interface VTuberModeToggleProps {
    onToggle?: (enabled: boolean) => void;
}

const VTuberModeToggle: React.FC<VTuberModeToggleProps> = ({ onToggle }) => {
    const [isEnabled, setIsEnabled] = useState(false);
    const [isInitializing, setIsInitializing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const toggle = async () => {
        if (isInitializing) return;
        setError(null);
        setIsInitializing(true);

        try {
            if (isEnabled) {
                faceTracker.stop();
                setIsEnabled(false);
                if (onToggle) onToggle(false);
            } else {
                await faceTracker.start();
                setIsEnabled(true);
                if (onToggle) onToggle(true);
            }
        } catch (e: any) {
            console.error('[VTuberToggle] Failed:', e);
            setError(e.message || 'Camera Error');
            setIsEnabled(false); // Revert UI
        } finally {
            setIsInitializing(false);
        }
    };

    return (
        <div style={{ position: 'relative' }}>
             <button
                onClick={toggle}
                title={isEnabled ? "Disable VTuber Mode (Face Tracking)" : "Enable VTuber Mode (Face Tracking)"}
                style={{
                    width: 48, height: 48, borderRadius: '50%',
                    backgroundColor: isEnabled ? 'rgba(76,175,80,0.8)' : 'rgba(0,0,0,0.3)',
                    color: 'white',
                    border: isEnabled ? '2px solid #4CAF50' : '1px solid rgba(255,255,255,0.3)',
                    backdropFilter: 'blur(10px)',
                    display: 'flex', justifyContent: 'center', alignItems: 'center',
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    transition: 'all 0.3s ease'
                }}
            >
                {isInitializing ? (
                    <div className="spinner" style={{width: 20, height: 20, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite'}} />
                ) : isEnabled ? (
                    <Video size={24} />
                ) : (
                    <Camera size={24} />
                )}
            </button>
            {error && (
                <div style={{
                    position: 'absolute', right: 60, top: 10,
                    backgroundColor: '#ff4444', color: 'white',
                    padding: '4px 8px', borderRadius: 4, whiteSpace: 'nowrap',
                    fontSize: 12
                }}>
                    {error}
                </div>
            )}
            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
};

export default VTuberModeToggle;
