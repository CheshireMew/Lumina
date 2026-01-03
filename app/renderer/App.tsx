import React, { useState } from 'react'
import Live2DViewer, { Live2DViewerRef } from './live2d-view/Live2DViewer'
import ChatBubble from './components/ChatBubble'
import InputBox from './components/InputBox'
import VoiceInput from './components/VoiceInput'
import SettingsModal from './components/SettingsModal'

function App() {
    const [currentMessage, setCurrentMessage] = useState<string>('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [chatMode, setChatMode] = useState<'text' | 'voice'>('text');
    const live2dRef = React.useRef<Live2DViewerRef>(null);

    const handleSend = async (text: string) => {
        setIsProcessing(true);
        // Optimistic UI updates could go here if we had a chat history

        try {
            // 1. Send to LLM
            const response = await (window as any).llm.chat(text);
            setCurrentMessage(response);

            // 2. Trigger Live2D Motion
            // Simple logic: random motion for now
            if (live2dRef.current) {
                live2dRef.current.motion('TapBody');
            }

        } catch (error) {
            console.error('Chat error:', error);
            setCurrentMessage('Sorry, I had a glitch...');
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div style={{ width: '100vw', height: '100vh', backgroundColor: 'transparent', position: 'relative', overflow: 'hidden' }}>

            {/* Live2D Layer */}
            <Live2DViewer
                ref={live2dRef}
                modelPath="/live2d/Hiyori/Hiyori.model3.json"
            />

            {/* UI Layer */}
            <ChatBubble message={currentMessage} />

            {chatMode === 'text' ? (
                <InputBox onSend={handleSend} disabled={isProcessing} />
            ) : (
                <VoiceInput onSend={handleSend} disabled={isProcessing} />
            )}

            <div style={{ position: 'absolute', bottom: 20, right: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Toggle Mode Button */}
                <button
                    onClick={() => setChatMode(prev => prev === 'text' ? 'voice' : 'text')}
                    style={{
                        background: 'rgba(0,0,0,0.6)',
                        border: 'none',
                        borderRadius: '50%',
                        width: 40,
                        height: 40,
                        cursor: 'pointer',
                        zIndex: 20,
                        fontSize: 20,
                        color: 'white',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        transition: 'all 0.3s ease',
                        boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
                    }}
                    title={chatMode === 'text' ? "Switch to Voice" : "Switch to Text"}
                >
                    {chatMode === 'text' ? '🎤' : '⌨️'}
                </button>

                {/* Settings Button */}
                <button
                    onClick={() => setIsSettingsOpen(true)}
                    style={{
                        background: 'rgba(255,255,255,0.8)',
                        border: 'none',
                        borderRadius: '50%',
                        width: 40,
                        height: 40,
                        cursor: 'pointer',
                        zIndex: 20,
                        fontSize: 20,
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
                    }}
                    title="Settings"
                >
                    ⚙️
                </button>
            </div>

            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        </div>
    )
}

export default App
