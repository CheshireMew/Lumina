import asyncio, aiohttp, io, base64, json, logging, re, time
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from py.get_setting import get_port, load_settings

class TelegramClient:
    def __init__(self):
        self.TelegramAgent = "super-model"
        self.memoryLimit = 10
        self.memoryList: Dict[int, List[Dict]] = {}  # chat_id -> messages
        self.asyncToolsID: Dict[int, List[str]] = {}
        self.fileLinks: Dict[int, List[str]] = {}
        self.separators = ["。", "\n", "？", "！"]
        self.reasoningVisible = False
        self.quickRestart = True
        self.enableTTS = False
        self.wakeWord = None
        self.bot_token: str = ""
        self._is_ready = False
        self._manager_ref = None
        self._ready_callback = None
        self._shutdown_requested = False
        self.offset = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.port = get_port()

    # -------------------- 生命周期 --------------------
    async def run(self):
        # Add a session timeout slightly above the polling timeout
        timeout = aiohttp.ClientTimeout(total=35)  # 5s buffer
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        self._is_ready = True
        if self._manager_ref:
            manager = self._manager_ref()
            if manager:
                manager._ready_complete.set()
                manager.is_running = True

        logging.info("Telegram 轮询开始")
        try:
            while not self._shutdown_requested:
                try:
                    updates = await self._get_updates()
                    for u in updates:
                        await self._handle_update(u)
                except asyncio.TimeoutError:
                    # Normal when shutdown happens during long poll
                    pass
                
                # Prevent tight loop when no updates
                if not updates:
                    await asyncio.sleep(0.1)
        finally:
            await self.session.close()

    async def _get_updates(self):
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        # CRITICAL: Reduce from 30s to 5s for responsive shutdown
        async with self.session.get(url, params={"offset": self.offset, "timeout": 5}) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            if not data.get("ok"):
                return []
            return data["result"]

    # -------------------- 消息入口 --------------------
    async def _handle_update(self, u: dict):
        if "message" not in u:
            return
        msg = u["message"]
        self.offset = u["update_id"] + 1
        chat_id = msg["chat"]["id"]

        # 文字
        if "text" in msg:
            await self._handle_text(chat_id, msg)
        # 图片（任意尺寸）
        elif "photo" in msg:
            await self._handle_photo(chat_id, msg)
        # 语音 / 音频
        elif "voice" in msg or "audio" in msg:
            await self._handle_voice(chat_id, msg)

    # -------------------- 文字 --------------------
    async def _handle_text(self, chat_id: int, msg: dict):
        text = msg["text"]
        if self.quickRestart:
            if text in {"/restart", "/重启"}:
                self.memoryList[chat_id] = []
                await self._send_text(chat_id, "对话记录已重置。")
                return
        if self.wakeWord:
            if self.wakeWord not in text:
                logging.info(f"未检测到唤醒词: {self.wakeWord}")
                return
        await self._process_llm(chat_id, text, [], msg.get("message_id"))

    # -------------------- 图片 --------------------
    async def _handle_photo(self, chat_id: int, msg: dict):
        photos = msg["photo"]  # 数组，尺寸升序
        file_id = photos[-1]["file_id"]
        file_info = await self._get_file(file_id)
        if not file_info:
            await self._send_text(chat_id, "下载图片失败")
            return
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_info['file_path']}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                await self._send_text(chat_id, "下载图片失败")
                return
            img_bytes = await resp.read()
        base64_data = base64.b64encode(img_bytes).decode()
        data_uri = f"data:image/jpeg;base64,{base64_data}"
        user_content = [
            {"type": "image_url", "image_url": {"url": data_uri}},
            {"type": "text", "text": "用户发送了一张图片"}
        ]
        await self._process_llm(chat_id, "", user_content, msg.get("message_id"))

    # -------------------- 语音 --------------------
    async def _handle_voice(self, chat_id: int, msg: dict):
        voice = msg.get("voice") or msg.get("audio")
        file_id = voice["file_id"]
        file_info = await self._get_file(file_id)
        if not file_info:
            await self._send_text(chat_id, "下载语音失败")
            return
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_info['file_path']}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                await self._send_text(chat_id, "下载语音失败")
                return
            voice_bytes = await resp.read()
        # 调用本地 ASR
        text = await self._transcribe(voice_bytes)
        if self.wakeWord:
            if self.wakeWord not in text:
                logging.info(f"未检测到唤醒词: {self.wakeWord}")
                return

        if not text:
            await self._send_text(chat_id, "语音转文字失败")
            return  
        await self._process_llm(chat_id, text, [], msg.get("message_id"))

    # -------------------- LLM 统一处理 --------------------
    async def _process_llm(self, chat_id: int, text: str, extra_content: List[dict], reply_to_msg_id: Optional[int]):
        if chat_id not in self.memoryList:
            self.memoryList[chat_id] = []
        if chat_id not in self.asyncToolsID:
            self.asyncToolsID[chat_id] = []
        if chat_id not in self.fileLinks:
            self.fileLinks[chat_id] = []

        # 构造 user 消息
        if extra_content:
            user_msg = {"role": "user", "content": extra_content}
        else:
            user_msg = {"role": "user", "content": text}
        self.memoryList[chat_id].append(user_msg)

        settings = await load_settings()
        client = AsyncOpenAI(api_key="super-secret-key", base_url=f"http://127.0.0.1:{get_port()}/v1")

        state = {"text_buffer": "", "image_cache": []}
        full_response = []

        stream = await client.chat.completions.create(
            model=self.TelegramAgent,
            messages=self.memoryList[chat_id],
            stream=True,
            extra_body={
                "asyncToolsID": self.asyncToolsID[chat_id],
                "fileLinks": self.fileLinks[chat_id],
            },
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            content = getattr(delta, 'content', '') or ""
            reasoning = getattr(delta, 'reasoning_content', '') or ""
            tool_link = getattr(delta, 'tool_link', '') or ""
            async_tool_id = getattr(delta, 'async_tool_id', '') or ""

            if tool_link and settings["tools"]["toolMemorandum"]["enabled"]:
                self.fileLinks[chat_id].append(tool_link)
            if async_tool_id:
                lst = self.asyncToolsID[chat_id]
                if async_tool_id not in lst:
                    lst.append(async_tool_id)
                else:
                    lst.remove(async_tool_id)

            seg = reasoning if self.reasoningVisible and reasoning else content
            state["text_buffer"] += seg
            full_response.append(content)

            # 分段发送
            if self.separators:
                while True:
                    buf = state["text_buffer"]
                    split_pos = -1
                    for i, ch in enumerate(buf):
                        if ch in self.separators:
                            split_pos = i + 1
                            break
                    if split_pos <= 0:
                        break
                    send_chunk = buf[:split_pos]
                    state["text_buffer"] = buf[split_pos:]
                    clean = self._clean_text(send_chunk)
                    if clean:
                        if self.enableTTS:
                            pass
                        else:
                            await self._send_text(chat_id, clean)

        # 剩余文本
        if state["text_buffer"]:
            clean = self._clean_text(state["text_buffer"])
            if clean:
                if self.enableTTS:
                    pass
                else:
                    await self._send_text(chat_id, clean)

        # 提取并发送图片
        self._extract_images("".join(full_response), state)
        for img_url in state["image_cache"]:
            await self._send_photo(chat_id, img_url)

        # 记忆
        assistant_text = "".join(full_response)
        self.memoryList[chat_id].append({"role": "assistant", "content": assistant_text})

        # 记忆长度限制
        if self.memoryLimit > 0:
            while len(self.memoryList[chat_id]) > self.memoryLimit * 2:
                self.memoryList[chat_id].pop(0)
                if self.memoryList[chat_id]:
                    self.memoryList[chat_id].pop(0)

        # TTS
        if self.enableTTS and assistant_text:
            await self._send_voice(chat_id, assistant_text)

    # -------------------- 发送 API 封装 --------------------
    async def _send_text(self, chat_id: int, text: str, reply_to_msg_id: Optional[int] = None):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_to_msg_id:
            payload["reply_to_message_id"] = reply_to_msg_id
        await self.session.post(url, json=payload)

    async def _send_photo(self, chat_id: int, image_url: str):
        # 先下载
        async with self.session.get(image_url) as resp:
            if resp.status != 200:
                return
            img_bytes = await resp.read()
        #  multipart 上传
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("photo", io.BytesIO(img_bytes), filename="image.jpg")
        await self.session.post(url, data=data)

    def clean_markdown(self, buffer):
        # Remove heading marks (#, ##, ### etc.)
        buffer = re.sub(r'#{1,6}\s', '', buffer, flags=re.MULTILINE)
        
        # Remove single Markdown formatting characters (*_~`) but keep if they appear consecutively
        buffer = re.sub(r'[*_~`]+', '', buffer)
        
        # Remove list item marks (- or * at line start)
        buffer = re.sub(r'^\s*[-*]\s', '', buffer, flags=re.MULTILINE)
        
        # Remove emoji and other Unicode symbols
        buffer = re.sub(r'[\u2600-\u27BF\u2700-\u27BF\U0001F300-\U0001F9FF]', '', buffer)
        
        # Remove Unicode surrogate pairs
        buffer = re.sub(r'[\uD800-\uDBFF][\uDC00-\uDFFF]', '', buffer)
        
        # Remove image marks (![alt](url))
        buffer = re.sub(r'!\[.*?\]\(.*?\)', '', buffer)
        
        # Remove link marks ([text](url)), keeping the text
        buffer = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', buffer)
        
        # Remove leading/trailing whitespace
        return buffer.strip()

    async def _send_voice(self, chat_id: int, text: str):
        from py.get_setting import load_settings
        settings = await load_settings()
        tts_settings = settings.get("ttsSettings", {})
        index = 0
        text = self.clean_markdown(text)
        payload = {
            "text": text,
            "voice": "default",
            "ttsSettings": tts_settings,
            "index": index,
            "mobile_optimized": True,  # 飞书优化标志
            "format": "opus"           # 明确请求opus格式
        }

        logging.info(f"发送TTS请求（opus格式），文本长度: {len(text)}，引擎: {tts_settings.get('engine', 'edgetts')}")

        timeout = aiohttp.ClientTimeout(total=90, connect=30, sock_read=60)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"http://127.0.0.1:{self.port}/tts",
                json=payload
            ) as resp:
                if resp.status != 200:
                    logging.error(f"TTS 请求失败: {resp.status}")
                    error_text = await resp.text()
                    logging.error(f"TTS 错误响应: {error_text}")
                    await self._send_text(chat_id, "语音生成失败，请稍后重试")
                    return

                opus_data = await resp.read()
                audio_format = resp.headers.get("X-Audio-Format", "unknown")
                
                logging.info(f"TTS响应成功，opus大小: {len(opus_data) / 1024:.1f}KB，格式: {audio_format}")
        # 上传语音
        url = f"https://api.telegram.org/bot{self.bot_token}/sendVoice"
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("voice", io.BytesIO(opus_data), filename="voice.opus")
        await self.session.post(url, data=data)

    # -------------------- 工具 --------------------
    async def _get_file(self, file_id: str) -> Optional[dict]:
        url = f"https://api.telegram.org/bot{self.bot_token}/getFile"
        async with self.session.get(url, params={"file_id": file_id}) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data.get("result")

    async def _transcribe(self, audio_bytes: bytes) -> Optional[str]:
        form = aiohttp.FormData()
        form.add_field("audio", io.BytesIO(audio_bytes), filename="voice.ogg")
        form.add_field("format", "auto")
        async with self.session.post(f"http://127.0.0.1:{get_port()}/asr", data=form) as resp:
            if resp.status != 200:
                return None
            res = await resp.json()
            return res.get("text") if res.get("success") else None

    def _clean_text(self, text):
        """清理文本中的特殊标记"""
        # 移除图片标记
        clean = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # 移除超链接
        clean = re.sub(r'\[.*?\]\(.*?\)', '', clean)
        # 移除纯URL
        clean = re.sub(r'https?://\S+', '', clean)
        return clean.strip()

    def _extract_images(self, full_text: str, state: dict):
        for m in re.finditer(r"!\[.*?\]\((https?://[^\s)]+)", full_text):
            state["image_cache"].append(m.group(1))