import { VoiceManagerData } from '../../hooks/useVoiceManager';
import { inputStyle } from './styles';

export const VoiceTab: React.FC<VoiceManagerData> = (props) => {
    const {
        whisperModels, currentWhisperModel, loadingStatus,
        audioDevices, currentAudioDevice,
        vadAggressiveness, vadStartThreshold, vadEndThreshold,
        handleSttModelChange,
        handleAudioDeviceChange,
        handleVadChange,
    } = props;

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
                                {dev.name}
                                {dev.channels ? ` (${dev.channels} ch)` : ''}
                                {!dev.channels && dev.host_api ? ` (${dev.host_api})` : ''}
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
                    <div style={{ marginBottom: '5px' }}>
                        <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>Model (模型)</label>
                        <select
                            value={currentWhisperModel}
                            onChange={(e) => handleSttModelChange(e.target.value)}
                            disabled={loadingStatus === 'loading' || whisperModels.length === 0}
                            style={inputStyle}
                        >
                            {whisperModels.length === 0 && (
                                <option value="">No STT models available</option>
                            )}
                            {whisperModels.map(m => (
                                <option key={m.id} value={m.id}>
                                    {m.name}
                                    {m.description ? ` (${m.description})` : ''}
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
                                噪声过滤强度 (WebRTC VAD)
                            </label>
                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                {vadAggressiveness}
                            </span>
                        </div>
                        <select
                            value={vadAggressiveness}
                            onChange={(e) => handleVadChange('vad_aggressiveness', Number(e.target.value))}
                            style={inputStyle}
                        >
                            <option value={0}>0 - 最宽松</option>
                            <option value={1}>1 - 宽松</option>
                            <option value={2}>2 - 严格</option>
                            <option value={3}>3 - 最严格</option>
                        </select>
                        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                            环境噪声误触发时优先调高这个值，建议桌面麦克风使用 3。
                        </div>
                    </div>
                    
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
                            min="0.07"
                            max="0.3"
                            step="0.01"
                            value={vadEndThreshold}
                            onChange={(e) => handleVadChange('speech_end_threshold', parseFloat(e.target.value))}
                            style={{ width: '100%', cursor: 'pointer' }}
                        />
                         <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                            <span>容忍停顿 (0.07)</span>
                            <span>快速切断 (0.3)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                            ⚠️ 值越小，允许的停顿越长 (更不容易被打断)。建议 0.10 - 0.15。
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
};
