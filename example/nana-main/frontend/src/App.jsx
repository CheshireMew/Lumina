import { useState, useRef, useEffect } from 'react'
import Live2DDisplay from './components/Live2DModel'
import './App.css'
import LoadingDots from './components/LoadingDots'

function App() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const live2dRef = useRef(null)
  const [isTracking, setIsTracking] = useState(true)

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
        e.preventDefault() // 防止空格键触发其他操作
        setIsTracking(!isTracking)
        if (live2dRef.current) {
          live2dRef.current.setTracking(!isTracking)
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [isTracking])

  const handleSubmit = async () => {
    if (!input.trim()) return
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: input,
          session_id: 'default' 
        }),
      })
      
      const data = await response.json()
      
      // 设置表情
      if (data.expression && live2dRef.current) {
        live2dRef.current.showExpression(data.expression)
      }
      
      // 检查音频数据是否存在且有效
      if (data.audio && data.audio.length > 0) {
        try {
          const audioBlob = new Blob(
            [Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))],
            { type: 'audio/mpeg' }
          )
          const audioUrl = URL.createObjectURL(audioBlob)
          
          const audio = new Audio(audioUrl)
          audio.onerror = (e) => {
            console.error('Audio playback error:', e)
          }
          
          await audio.play()
          
          // 播放完成后释放 URL
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl)
            // 音频播放结束后延迟1秒重置表情
            setTimeout(() => {
              if (live2dRef.current) {
                live2dRef.current.showExpression(data.expression, false)
              }
            }, 1000)  // 1000ms = 1秒
          }
        } catch (audioError) {
          console.error('Audio processing error:', audioError)
        }
      }
      
      // 更新消息
      setMessages([
        ...messages,
        { type: 'user', content: input },
        { type: 'assistant', content: data.message }
      ])
      setInput('')
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSendMessage = async () => {
    // 原有的消息发送逻辑
    handleSubmit()
  }

  // 获取最后一条助手消息
  const lastAssistantMessage = messages
    .filter(msg => msg.type === 'assistant')
    .at(-1)

  return (
    <div className="app">
      <div className="live2d-main">
        <Live2DDisplay ref={live2dRef} />
        <div className="subtitles">
          {loading ? (
            <div className="subtitle-text loading">
              ...
            </div>
          ) : lastAssistantMessage && (
            <div className="subtitle-text">
              {lastAssistantMessage.content}
            </div>
          )}
        </div>
      </div>

      {/* 输入区域 */}
      <div className="chat-input-container">
        <input
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="输入消息..."
        />
      </div>
    </div>
  )
}

export default App