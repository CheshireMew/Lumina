/**
 * General Tab - LLM 配置、用户设置、视觉设置
 */
import React from 'react';
import { inputStyle, sectionTitleStyle } from '../styles';

interface GeneralTabProps {
    userName: string;
    setUserName: (name: string) => void;
    apiBaseUrl: string;
    setApiBaseUrl: (url: string) => void;
    apiKey: string;
    setApiKey: (key: string) => void;
    modelName: string;
    setModelName: (name: string) => void;
    highDpiEnabled: boolean;
    setHighDpiEnabled: (enabled: boolean) => void;
}

export const GeneralTab: React.FC<GeneralTabProps> = ({
    userName, setUserName,
    apiBaseUrl, setApiBaseUrl,
    apiKey, setApiKey,
    modelName, setModelName,
    highDpiEnabled, setHighDpiEnabled
}) => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {/* User Profile */}
            <section>
                <h3 style={sectionTitleStyle}>User Profile</h3>
                <div style={{ marginBottom: 15 }}>
                    <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                        Your Name (What AI calls you)
                    </label>
                    <input
                        value={userName}
                        onChange={(e) => setUserName(e.target.value)}
                        style={inputStyle}
                        placeholder="Master"
                    />
                </div>
            </section>

            {/* LLM Configuration */}
            <section>
                <h3 style={sectionTitleStyle}>LLM Configuration</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                            API Host
                        </label>
                        <input
                            value={apiBaseUrl}
                            onChange={(e) => setApiBaseUrl(e.target.value)}
                            style={inputStyle}
                            placeholder="https://api.deepseek.com/v1"
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                            API Key
                        </label>
                        <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            style={inputStyle}
                            placeholder="sk-..."
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                            Model Name
                        </label>
                        <input
                            value={modelName}
                            onChange={(e) => setModelName(e.target.value)}
                            style={inputStyle}
                            placeholder="deepseek-chat"
                        />
                    </div>
                </div>
            </section>

            {/* Visual Settings */}
            <section>
                <h3 style={sectionTitleStyle}>Visual Settings</h3>
                <div style={{ 
                    display: 'flex', alignItems: 'center', gap: '10px', 
                    backgroundColor: 'white', padding: '12px', borderRadius: '8px', 
                    border: '1px solid #e5e7eb' 
                }}>
                    <input
                        type="checkbox"
                        checked={highDpiEnabled}
                        onChange={(e) => setHighDpiEnabled(e.target.checked)}
                        style={{ height: '16px', width: '16px', cursor: 'pointer' }}
                    />
                    <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>
                            Enable High-DPI (Retina) Rendering
                        </div>
                        <div style={{ fontSize: '12px', color: '#6b7280' }}>
                            Significantly improves quality on high-res screens but increases GPU usage.
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default GeneralTab;
