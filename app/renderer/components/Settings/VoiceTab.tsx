import React from 'react';
import { useVoiceManager } from '../../hooks/useVoiceManager';
import { inputStyle } from './styles';

export const VoiceTab: React.FC = () => {
    const {
        whisperModels, currentWhisperModel, loadingStatus, sttEngineType,
        audioDevices, currentAudioDevice,
        voiceprintEnabled, voiceprintThreshold, voiceprintProfile, voiceprintStatus,
        vadStartThreshold, vadEndThreshold,
        handleSttModelChange,
        handleEngineChange,
        handleAudioDeviceChange,
        handleVoiceprintToggle,
        handleVoiceprintThresholdChange,
        handleVadChange,
        setVoiceprintProfile
    } = useVoiceManager(true);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', padding: '20px', overflowY: 'auto' }}>
            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Audio Input Device</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Microphone</label>
                    <select
                        value={currentAudioDevice || ''}
                        onChange={(e) => handleAudioDeviceChange(e.target.value)}
                        style={inputStyle}
                        disabled={!audioDevices.length}
                    >
                        {audioDevices.length > 0 ? audioDevices.map((dev, idx) => (
                            <option key={`${dev.index}-${dev.name}`} value={dev.name}>
                                {dev.name} ({dev.channels} ch)
                            </option>
                        )) : <option>No devices found</option>}
                    </select>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                        💡 Select your physical microphone to avoid system audio loopback
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>Voice Recognition (STT)</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <div style={{ marginBottom: '10px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>STT Engine (方案)</label>
                        <select
                            value={sttEngineType}
                            onChange={(e) => handleEngineChange(e.target.value)}
                            style={inputStyle}
                        >
                            <option value="sense_voice">SenseVoice (推荐 - 多语言/情感)</option>
                            <option value="paraformer_zh">Paraformer (中文专用/会议级)</option>
                            <option value="paraformer_en">Paraformer (English Only)</option>
                            <option value="faster_whisper">Faster-Whisper (通用 - 可选大小)</option>
                        </select>
                    </div>

                    <div style={{ marginBottom: '5px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Model (模型)</label>
                        <select
                            value={currentWhisperModel}
                            onChange={(e) => handleSttModelChange(e.target.value)}
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

                    {loadingStatus === 'loading' && <div style={{ 
                        fontSize: '12px', color: '#2563eb', marginTop: '8px', 
                        backgroundColor: '#eff6ff', padding: '8px', borderRadius: '6px',
                        display: 'flex', alignItems: 'center', gap: '6px'
                    }}>
                        <span className="spinner">⏳</span> 
                        <span>正在切换/下载模型，请留意控制台日志...</span>
                    </div>}
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>语音活动检测 (VAD Settings)</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <label style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                触发灵敏度 (Start Threshold)
                            </label>
                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                {vadStartThreshold.toFixed(2)}
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0.3"
                            max="0.95"
                            step="0.05"
                            value={vadStartThreshold}
                            onChange={(e) => handleVadChange('speech_start_threshold', parseFloat(e.target.value))}
                            style={{ width: '100%', cursor: 'pointer' }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                            <span>容易触发 (0.3)</span>
                            <span>严格过滤 (0.95)</span>
                        </div>
                    </div>

                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <label style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                断句延迟 (End Threshold)
                            </label>
                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                {vadEndThreshold.toFixed(2)}
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0.01"
                            max="0.3"
                            step="0.01"
                            value={vadEndThreshold}
                            onChange={(e) => handleVadChange('speech_end_threshold', parseFloat(e.target.value))}
                            style={{ width: '100%', cursor: 'pointer' }}
                        />
                         <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                            <span>容忍停顿 (0.01)</span>
                            <span>快速切断 (0.3)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                            ⚠️ 值越小，允许的停顿越长 (更不容易被打断)。建议 0.05 - 0.15。
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>声纹过滤 (Voiceprint Filter)</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                        <input
                            type="checkbox"
                            checked={voiceprintEnabled}
                            onChange={(e) => handleVoiceprintToggle(e.target.checked)}
                            style={{ height: '16px', width: '16px', cursor: 'pointer' }}
                        />
                         <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>启用声纹验证</div>
                            <div style={{ fontSize: '12px', color: '#6b7280' }}>只接受你的声音，过滤环境噪声和他人语音</div>
                        </div>
                    </div>

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
                            onChange={(e) => handleVoiceprintThresholdChange(Number(e.target.value))}
                            disabled={!voiceprintEnabled}
                            style={{ width: '100%', accentColor: '#4f46e5' }}
                        />
                         <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                            低阈值=容易通过 | 高阈值=严格过滤
                        </div>
                    </div>

                    <div style={{ marginBottom: '15px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Profile 名称</label>
                        <input
                            type="text"
                            value={voiceprintProfile}
                            onChange={(e) => setVoiceprintProfile(e.target.value)}
                            style={inputStyle}
                            placeholder="default"
                        />
                    </div>

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
