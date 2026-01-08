/**
 * Voice Tab - 语音识别(STT)、音频设备、声纹过滤设置
 */
import React from 'react';
import { inputStyle, sectionTitleStyle } from '../styles';
import { WhisperModelInfo, AudioDevice, STT_SERVER_URL } from '../types';

interface VoiceTabProps {
    // Audio Devices
    audioDevices: AudioDevice[];
    currentAudioDevice: string | null;
    onAudioDeviceChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
    
    // STT Models
    sttEngineType: string;
    setSttEngineType: (type: string) => void;
    whisperModels: WhisperModelInfo[];
    currentWhisperModel: string;
    loadingStatus: string;
    onSttModelChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
    
    // Voiceprint
    voiceprintEnabled: boolean;
    voiceprintThreshold: number;
    voiceprintProfile: string;
    voiceprintStatus: string;
    onVoiceprintToggle: (enabled: boolean) => void;
    onVoiceprintThresholdChange: (threshold: number) => void;
    setVoiceprintProfile: (profile: string) => void;
}

export const VoiceTab: React.FC<VoiceTabProps> = ({
    audioDevices, currentAudioDevice, onAudioDeviceChange,
    sttEngineType, setSttEngineType, whisperModels, currentWhisperModel, loadingStatus, onSttModelChange,
    voiceprintEnabled, voiceprintThreshold, voiceprintProfile, voiceprintStatus,
    onVoiceprintToggle, onVoiceprintThresholdChange, setVoiceprintProfile
}) => {

    const handleEngineChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const newEngine = e.target.value;
        setSttEngineType(newEngine);
        
        // Auto-switch model based on engine
        let defaultModel = 'base';
        if (newEngine === 'sense_voice') defaultModel = 'sense-voice';
        else if (newEngine === 'paraformer_zh') defaultModel = 'paraformer-zh';
        else if (newEngine === 'paraformer_en') defaultModel = 'paraformer-en';
        
        onSttModelChange({ target: { value: defaultModel } } as any);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {/* Audio Input Device */}
            <div>
                <h3 style={sectionTitleStyle}>Audio Input Device</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                        Microphone
                    </label>
                    <select
                        value={currentAudioDevice || ''}
                        onChange={onAudioDeviceChange}
                        style={inputStyle}
                    >
                        {audioDevices.length > 0 ? audioDevices.map(dev => (
                            <option key={dev.index} value={dev.name}>
                                {dev.name} ({dev.channels} ch)
                            </option>
                        )) : <option>No devices found</option>}
                    </select>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                        💡 Select your physical microphone to avoid system audio loopback
                    </div>
                </div>
            </div>

            {/* Voice Recognition (STT) */}
            <div>
                <h3 style={sectionTitleStyle}>Voice Recognition (STT)</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    {/* Engine Selection */}
                    <div style={{ marginBottom: '10px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                            STT Engine (方案)
                        </label>
                        <select value={sttEngineType} onChange={handleEngineChange} style={inputStyle}>
                            <option value="sense_voice">SenseVoice (推荐 - 多语言/情感)</option>
                            <option value="paraformer_zh">Paraformer (中文专用/会议级)</option>
                            <option value="paraformer_en">Paraformer (English Only)</option>
                            <option value="faster_whisper">Faster-Whisper (通用 - 可选大小)</option>
                        </select>
                    </div>

                    {/* Model Selection */}
                    <div style={{ marginBottom: '5px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                            Model (模型)
                        </label>
                        <select
                            value={currentWhisperModel}
                            onChange={onSttModelChange}
                            disabled={loadingStatus === 'loading'}
                            style={inputStyle}
                        >
                            {whisperModels.filter(m => {
                                if (sttEngineType === 'faster_whisper') return m.engine === 'faster_whisper';
                                if (sttEngineType === 'sense_voice') return m.name === 'sense-voice';
                                if (sttEngineType === 'paraformer_zh') return m.name === 'paraformer-zh';
                                if (sttEngineType === 'paraformer_en') return m.name === 'paraformer-en';
                                return false;
                            }).map(m => (
                                <option key={m.name} value={m.name}>
                                    {m.name} ({m.desc})
                                    {m.download_status === 'downloading' ? ' [Downloading...]' : ''}
                                </option>
                            ))}
                        </select>
                    </div>

                    {loadingStatus === 'loading' && (
                        <div style={{ 
                            fontSize: '12px', color: '#2563eb', marginTop: '8px', 
                            backgroundColor: '#eff6ff', padding: '8px', borderRadius: '6px',
                            display: 'flex', alignItems: 'center', gap: '6px'
                        }}>
                            <span>⏳</span>
                            <span>正在切换/下载模型，请留意控制台日志...</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Voiceprint Filter */}
            <div>
                <h3 style={sectionTitleStyle}>声纹过滤 (Voiceprint Filter)</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    {/* Enable Toggle */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                        <input
                            type="checkbox"
                            checked={voiceprintEnabled}
                            onChange={(e) => onVoiceprintToggle(e.target.checked)}
                            style={{ height: '16px', width: '16px', cursor: 'pointer' }}
                        />
                        <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>启用声纹验证</div>
                            <div style={{ fontSize: '12px', color: '#6b7280' }}>只接受你的声音，过滤环境噪声和他人语音</div>
                        </div>
                    </div>

                    {/* Threshold Slider */}
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '6px' }}>
                            相似度阈值: <strong style={{ color: '#1f2937' }}>{voiceprintThreshold.toFixed(2)}</strong>
                        </label>
                        <input
                            type="range"
                            min="0.1"
                            max="0.9"
                            step="0.05"
                            value={voiceprintThreshold}
                            onChange={(e) => onVoiceprintThresholdChange(Number(e.target.value))}
                            disabled={!voiceprintEnabled}
                            style={{ width: '100%', accentColor: '#4f46e5' }}
                        />
                        <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                            低阈值=容易通过 | 高阈值=严格过滤
                        </div>
                    </div>

                    {/* Profile Name */}
                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                            Profile 名称
                        </label>
                        <input
                            type="text"
                            value={voiceprintProfile}
                            onChange={(e) => setVoiceprintProfile(e.target.value)}
                            style={inputStyle}
                            placeholder="default"
                        />
                    </div>

                    {/* Status */}
                    {voiceprintStatus && (
                        <div style={{
                            fontSize: '12px',
                            padding: '8px',
                            borderRadius: '6px',
                            backgroundColor: voiceprintStatus.includes('✓') ? '#d1fae5' : '#fef3c7',
                            color: voiceprintStatus.includes('✓') ? '#065f46' : '#92400e',
                            textAlign: 'center',
                            marginBottom: '10px'
                        }}>
                            {voiceprintStatus}
                        </div>
                    )}

                    <div style={{ fontSize: '11px', color: '#9ca3af', lineHeight: '1.4' }}>
                        💡 <strong>使用提示：</strong><br />
                        1. 运行 <code>python python_backend/register_voiceprint.py</code><br />
                        2. 启用声纹验证开关<br />
                        3. 调整阈值以达到最佳效果<br />
                        4. 重启 stt_server.py 使配置生效
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VoiceTab;
