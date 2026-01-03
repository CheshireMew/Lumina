import React, { useState, useEffect } from 'react';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
    const [apiKey, setApiKey] = useState('');
    const [apiBaseUrl, setApiBaseUrl] = useState('https://api.deepseek.com/v1');
    const [modelName, setModelName] = useState('deepseek-chat');

    useEffect(() => {
        if (isOpen) {
            // Load current settings
            (window as any).settings.get('apiKey').then((val: string) => setApiKey(val || ''));
            (window as any).settings.get('apiBaseUrl').then((val: string) => setApiBaseUrl(val || 'https://api.deepseek.com/v1'));
            (window as any).settings.get('modelName').then((val: string) => setModelName(val || 'deepseek-chat'));
        }
    }, [isOpen]);

    const handleSave = async () => {
        await (window as any).settings.set('apiKey', apiKey);
        await (window as any).settings.set('apiBaseUrl', apiBaseUrl);
        await (window as any).settings.set('modelName', modelName);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
            <div style={{
                backgroundColor: 'white', padding: 20, borderRadius: 10, width: 400,
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
            }}>
                <h2>Settings</h2>

                <div style={{ marginBottom: 15 }}>
                    <label style={{ display: 'block', marginBottom: 5 }}>API Key</label>
                    <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ccc' }}
                        placeholder="sk-..."
                    />
                </div>

                <div style={{ marginBottom: 15 }}>
                    <label style={{ display: 'block', marginBottom: 5 }}>API Base URL</label>
                    <input
                        type="text"
                        value={apiBaseUrl}
                        onChange={(e) => setApiBaseUrl(e.target.value)}
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ccc' }}
                    />
                </div>

                <div style={{ marginBottom: 15 }}>
                    <label style={{ display: 'block', marginBottom: 5 }}>Model Name</label>
                    <input
                        type="text"
                        value={modelName}
                        onChange={(e) => setModelName(e.target.value)}
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #ccc' }}
                    />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                    <button onClick={onClose} style={{ padding: '8px 16px', borderRadius: 4, border: '1px solid #ccc', background: 'white', cursor: 'pointer' }}>Cancel</button>
                    <button onClick={handleSave} style={{ padding: '8px 16px', borderRadius: 4, border: 'none', background: '#007bff', color: 'white', cursor: 'pointer' }}>Save</button>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
