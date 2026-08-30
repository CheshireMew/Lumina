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
        sttLoadState, sttError, ttsLoadState, ttsError,
        ttsEngines, activeTtsEngines, refreshVoiceData,
    } = props;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', padding: '20px', overflowY: 'auto' }}>
            {(sttLoadState !== 'ready' || ttsLoadState !== 'ready') && (
                <div role={sttLoadState === 'error' || ttsLoadState === 'error' ? 'alert' : 'status'} style={{ padding: 12, borderRadius: 8, background: sttLoadState === 'error' || ttsLoadState === 'error' ? '#fef2f2' : '#eff6ff', color: sttLoadState === 'error' || ttsLoadState === 'error' ? '#991b1b' : '#1d4ed8', fontSize: 12 }}>
                    <div>{sttError || ttsError || '正在读取语音服务状态…'}</div>
                    {(sttLoadState === 'error' || ttsLoadState === 'error') && (
                        <button type="button" onClick={() => void refreshVoiceData()} style={{ marginTop: 8, border: '1px solid currentColor', background: 'transparent', borderRadius: 6, padding: '5px 9px', color: 'inherit', cursor: 'pointer' }}>重新加载</button>
                    )}
                </div>
            )}

            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>回复语音</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: 13, color: '#4b5563' }}>
                    {ttsLoadState === 'ready'
                        ? ttsEngines.length
                            ? `可用服务：${ttsEngines.map((engine) => `${engine.name}${activeTtsEngines.includes(engine.id) ? '（当前）' : ''}`).join('、')}`
                            : '没有可用的语音合成服务。'
                        : '语音合成服务尚未就绪。'}
                </div>
            </div>
            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>音频输入设备</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <label htmlFor="voice-audio-device" style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>麦克风</label>
                    <select
                        id="voice-audio-device"
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
                        )) : <option>未找到音频输入设备</option>}
                    </select>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                        请选择实际使用的麦克风，避免把系统播放声音再次录入。
                    </div>
                </div>
            </div>

            <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>语音识别</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                    <div style={{ marginBottom: '5px' }}>
                        <label htmlFor="voice-stt-model" style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>识别模型</label>
                        <select
                            id="voice-stt-model"
                            value={currentWhisperModel}
                            onChange={(e) => handleSttModelChange(e.target.value)}
                            disabled={loadingStatus === 'loading' || whisperModels.length === 0}
                            style={inputStyle}
                        >
                            {whisperModels.length === 0 && (
                                <option value="">没有可用的语音识别模型</option>
                            )}
                            {whisperModels.map(m => (
                                <option key={m.id} value={m.id}>
                                    {m.name}
                                    {m.description ? ` (${m.description})` : ''}
                                    {m.download_status === 'downloading' ? ' [正在下载]' : ''}
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
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#374151', marginBottom: '10px' }}>语音活动检测</h3>
                <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <label htmlFor="voice-vad-aggressiveness" style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                噪声过滤强度
                            </label>
                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                {vadAggressiveness}
                            </span>
                        </div>
                        <select
                            id="voice-vad-aggressiveness"
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
                            <label htmlFor="voice-vad-start" style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                触发灵敏度
                            </label>
                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                {vadStartThreshold.toFixed(2)}
                            </span>
                        </div>
                        <input
                            id="voice-vad-start"
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
                            <label htmlFor="voice-vad-end" style={{ fontSize: '13px', fontWeight: 600, color: '#4b5563' }}>
                                断句延迟
                            </label>
                            <span style={{ fontSize: '12px', color: '#6b7280', fontFamily: 'monospace' }}>
                                {vadEndThreshold.toFixed(2)}
                            </span>
                        </div>
                        <input
                            id="voice-vad-end"
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
                            值越小，允许的停顿越长，也越不容易被打断。建议使用 0.10～0.15。
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
};
