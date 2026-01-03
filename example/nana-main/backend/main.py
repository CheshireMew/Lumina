from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import base64
from chat_service import ChatService
from tts import TTSService
from config import Config

app = FastAPI()

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

chat_service = ChatService()
tts_service = TTSService(Config.FISH_API_KEY, Config.FISH_REFERENCE_ID)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await normal_chat_flow(request)

async def normal_chat_flow(request: ChatRequest):
    reply, audio_data, expression = await chat_service.generate_reply(
        request.message, 
        request.session_id
    )
    
    print("-- /api/chat --")
    print("reply:", reply)
    print("expression:", expression)

    audio_base64 = base64.b64encode(audio_data).decode('ascii') if audio_data else ''
    
    return JSONResponse(
        content={
            "message": reply,
            "audio": audio_base64,
            "expression": expression
        }
    )