from typing import Optional, Tuple
from llm import LLMService
from tts import TTSService
from config import Config
from main_agent import MainAgent
from conversation import ConversationHistory

class ChatService:
    def __init__(self):
        # 初始化LLM服务
        self.llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)
        
        # 只在启用TTS时初始化TTS服务
        self.tts_service = TTSService(Config.FISH_API_KEY, Config.FISH_REFERENCE_ID) if Config.is_tts_enabled() else None
         
        # 初始化对话历史和主Agent
        self.conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        self.main_agent = MainAgent(self.llm_service, self.conversation_history)

    async def generate_reply(self, message: str, session_id: str) -> Tuple[str, Optional[bytes], str]:
        """
        生成回复
        :param message: 用户消息
        :param session_id: 会话ID
        :return: (回复文本, 语音数据, 表情)
        """
        try:
            # 使用 MainAgent 生成回复和表情
            reply, expression = await self.main_agent.reply(message)
            
            # 生成语音 (如果TTS服务已启用)
            audio_data = None   
            if reply and self.tts_service:
                try:
                    audio_data = self.tts_service.generate_audio(reply)
                except Exception as e:
                    print(f"生成语音时出错了喵: {e}")
            
            return reply, audio_data, expression
            
        except Exception as e:
            print(f"生成回复时出错了喵: {e}")
            return "对不起，我现在有点累了，能稍后再聊吗？", None, "生气"