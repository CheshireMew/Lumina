import React, { useState, useEffect, useRef } from 'react';

/**
 * 音频调试工具 - 用于诊断麦克风捕获系统音频的问题
 */
const AudioDebugger: React.FC = () => {
    const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
    const [isCapturing, setIsCapturing] = useState(false);
    const [audioLevel, setAudioLevel] = useState(0);
    const [streamInfo, setStreamInfo] = useState<any>(null);
    const [debugLog, setDebugLog] = useState<string[]>([]);

    const audioContextRef = useRef<AudioContext | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const animationFrameRef = useRef<number>(0);

    const addLog = (message: string) => {
        setDebugLog(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
        console.log('[AudioDebugger]', message);
    };

    useEffect(() => {
        enumerateDevices();
        return () => {
            // Cleanup on unmount
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
            if (audioContextRef.current) {
                audioContextRef.current.close();
            }
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, []);

    const enumerateDevices = async () => {
        try {
            const allDevices = await navigator.mediaDevices.enumerateDevices();
            const audioInputs = allDevices.filter(d => d.kind === 'audioinput');
            setDevices(audioInputs);
            addLog(`Found ${audioInputs.length} audio input devices`);
            audioInputs.forEach((d, i) => {
                addLog(`  [${i}] ${d.label || 'Unlabeled'} (ID: ${d.deviceId.substring(0, 20)}...)`);
            });
        } catch (err: any) {
            addLog(`ERROR enumerating devices: ${err.message}`);
        }
    };

    const startCapture = async () => {
        try {
            addLog(`Requesting audio stream from device: ${selectedDeviceId || 'default'}`);

            const constraints: MediaStreamConstraints = {
                audio: selectedDeviceId ? {
                    deviceId: { exact: selectedDeviceId },
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                } : {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            };

            addLog(`Constraints: ${JSON.stringify(constraints, null, 2)}`);

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            streamRef.current = stream;

            // 获取实际使用的设备信息
            const tracks = stream.getAudioTracks();
            if (tracks.length === 0) {
                addLog('ERROR: No audio tracks in stream!');
                return;
            }

            const track = tracks[0];
            const settings = track.getSettings();
            const capabilities = track.getCapabilities();

            addLog(`Stream obtained successfully!`);
            addLog(`  Label: ${track.label}`);
            addLog(`  Enabled: ${track.enabled}`);
            addLog(`  Muted: ${track.muted}`);
            addLog(`  ReadyState: ${track.readyState}`);
            addLog(`  Settings: ${JSON.stringify(settings, null, 2)}`);

            setStreamInfo({
                label: track.label,
                enabled: track.enabled,
                muted: track.muted,
                readyState: track.readyState,
                settings,
                capabilities
            });

            // 创建音频分析器
            addLog('Creating AudioContext...');
            const audioContext = new AudioContext();
            audioContextRef.current = audioContext;
            addLog(`AudioContext created, state: ${audioContext.state}, sampleRate: ${audioContext.sampleRate}`);

            const source = audioContext.createMediaStreamSource(stream);
            addLog('MediaStreamSource created');

            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            analyser.smoothingTimeConstant = 0.3;
            addLog(`Analyser created, fftSize: ${analyser.fftSize}`);

            source.connect(analyser);
            addLog('Source connected to analyser');

            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            addLog(`Data array size: ${dataArray.length}`);

            let frameCount = 0;
            let isRunning = true; // 使用局部变量而不是state

            const updateLevel = () => {
                if (!isRunning) return;

                analyser.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                setAudioLevel(average);

                frameCount++;
                if (frameCount % 60 === 0) {
                    addLog(`Audio level: ${average.toFixed(2)} (frame ${frameCount})`);
                }

                animationFrameRef.current = requestAnimationFrame(updateLevel);
            };

            setIsCapturing(true);
            updateLevel();
            addLog('Started audio level monitoring');

            // 保存停止函数的引用
            streamRef.current = Object.assign(stream, {
                stopMonitoring: () => {
                    isRunning = false;
                }
            });

        } catch (err: any) {
            addLog(`ERROR starting capture: ${err.name} - ${err.message}`);
            if (err.name === 'NotAllowedError') {
                addLog('  Microphone permission was denied!');
            } else if (err.name === 'NotFoundError') {
                addLog('  No microphone device found!');
            }
        }
    };

    const stopCapture = () => {
        setIsCapturing(false);
        setAudioLevel(0);

        if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => {
                track.stop();
                addLog(`Stopped track: ${track.label}`);
            });
            streamRef.current = null;
        }

        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        addLog('Capture stopped and resources cleaned up');
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(0,0,0,0.95)',
            color: 'white',
            padding: '20px',
            overflowY: 'auto',
            zIndex: 9999,
            fontFamily: 'monospace'
        }}>
            <h2>🔍 Audio Capture Debugger</h2>

            <div style={{ marginBottom: '20px' }}>
                <h3>1. 选择设备</h3>
                <select
                    value={selectedDeviceId}
                    onChange={(e) => setSelectedDeviceId(e.target.value)}
                    style={{ width: '100%', padding: '8px', fontSize: '14px' }}
                >
                    <option value="">Default Device</option>
                    {devices.map(d => (
                        <option key={d.deviceId} value={d.deviceId}>
                            {d.label || `Device ${d.deviceId.substring(0, 10)}`}
                        </option>
                    ))}
                </select>
            </div>

            <div style={{ marginBottom: '20px' }}>
                <h3>2. 开始捕获</h3>
                {!isCapturing ? (
                    <button onClick={startCapture} style={{ padding: '10px 20px', fontSize: '16px' }}>
                        Start Capture
                    </button>
                ) : (
                    <button onClick={stopCapture} style={{ padding: '10px 20px', fontSize: '16px' }}>
                        Stop Capture
                    </button>
                )}
            </div>

            <div style={{ marginBottom: '20px' }}>
                <h3>3. 音频电平</h3>
                <div style={{
                    width: '100%',
                    height: '40px',
                    backgroundColor: '#333',
                    position: 'relative',
                    border: '1px solid #666'
                }}>
                    <div style={{
                        width: `${(audioLevel / 255) * 100}%`,
                        height: '100%',
                        backgroundColor: audioLevel > 50 ? '#ff4757' : '#2ed573',
                        transition: 'width 0.1s'
                    }} />
                    <span style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        color: 'white',
                        fontWeight: 'bold'
                    }}>
                        {audioLevel.toFixed(0)} / 255
                    </span>
                </div>
                <p style={{ fontSize: '12px', color: '#888' }}>
                    测试: 保持完全安静，如果电平仍然跳动，说明在捕获系统音频
                </p>
            </div>

            {streamInfo && (
                <div style={{ marginBottom: '20px' }}>
                    <h3>4. Stream 信息</h3>
                    <pre style={{
                        backgroundColor: '#1a1a1a',
                        padding: '10px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        overflow: 'auto'
                    }}>
                        {JSON.stringify(streamInfo, null, 2)}
                    </pre>
                </div>
            )}

            <div style={{ marginBottom: '20px' }}>
                <h3>5. Debug Log</h3>
                <div style={{
                    backgroundColor: '#1a1a1a',
                    padding: '10px',
                    borderRadius: '4px',
                    maxHeight: '200px',
                    overflow: 'auto',
                    fontSize: '12px'
                }}>
                    {debugLog.map((log, i) => (
                        <div key={i}>{log}</div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default AudioDebugger;
