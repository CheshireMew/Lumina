import asyncio
import base64
import io
import json
import logging
import re
import threading
import weakref
from typing import Dict, List, Optional, Any

import aiohttp
import discord
from discord.ext import commands, tasks
from openai import AsyncOpenAI
from pydantic import BaseModel

from py.get_setting import get_port, load_settings

# ------------------ 配置模型 ------------------
class DiscordBotConfig(BaseModel):
    token: str
    llm_model: str = "super-model"
    memory_limit: int = 10
    separators: List[str] = ["。", "\n", "？", "！"]
    reasoning_visible: bool = False
    quick_restart: bool = True
    enable_tts: bool = True
    wakeWord: str              # 唤醒词

# ------------------ 管理器 ------------------
class DiscordBotManager:
    def __init__(self):
        self.bot_thread: Optional[threading.Thread] = None
        self.bot_client: Optional["DiscordClient"] = None
        self.is_running = False
        self.config: Optional[DiscordBotConfig] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event = threading.Event()
        self._ready_complete = threading.Event()
        self._startup_error: Optional[str] = None
        self._stop_requested = False

    # ---------- 生命周期 ----------
    def start_bot(self, config: DiscordBotConfig):
        if self.is_running:
            raise RuntimeError("Discord 机器人已在运行")
        self.config = config
        self._shutdown_event.clear()
        self._ready_complete.clear()
        self._startup_error = None
        self._stop_requested = False

        self.bot_thread = threading.Thread(
            target=self._run_bot_thread, args=(config,), daemon=True, name="DiscordBotThread"
        )
        self.bot_thread.start()

        if not self._ready_complete.wait(timeout=30):
            self.stop_bot()
            raise RuntimeError("Discord 机器人就绪超时")

        if self._startup_error:
            self.stop_bot()
            raise RuntimeError(f"Discord 机器人启动失败: {self._startup_error}")

    def _run_bot_thread(self, config: DiscordBotConfig):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.bot_client = DiscordClient(config, manager=self)
            self.loop.run_until_complete(self.bot_client.start(config.token))
        except Exception as e:
            if not self._stop_requested:
                self._startup_error = str(e)
                logging.exception("Discord 机器人线程异常")
        finally:
            self._cleanup()

    def stop_bot(self):
        if not self.is_running and not self.bot_thread:
            return
        self._stop_requested = True
        self._shutdown_event.set()
        self.is_running = False
        if self.bot_client:
            asyncio.run_coroutine_threadsafe(self.bot_client.close(), self.loop)
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=5)
        self._cleanup()

    def _cleanup(self):
        self.is_running = False
        if self.loop and not self.loop.is_closed():
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self.loop.close()
            except Exception:
                pass
        logging.info("Discord 机器人资源已清理")

    def get_status(self):
        return {
            "is_running": self.is_running,
            "thread_alive": self.bot_thread.is_alive() if self.bot_thread else False,
            "ready_completed": self._ready_complete.is_set(),
            "startup_error": self._startup_error,
            "config": self.config.model_dump() if self.config else None,
        }


# ------------------ Discord Client ------------------
class DiscordClient(discord.Client):
    def __init__(self, config: DiscordBotConfig, manager: DiscordBotManager):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.config = config
        self.manager = manager
        self.memory: Dict[int, List[dict]] = {}  # channel_id -> msgs
        self.async_tools: Dict[int, List[str]] = {}
        self.file_links: Dict[int, List[str]] = {}
        self._shutdown_requested = False

    async def on_ready(self):
        self.manager.is_running = True
        self.manager._ready_complete.set()
        logging.info(f"✅ Discord 机器人已上线：{self.user}")

    async def on_message(self, msg: discord.Message):
        if self._shutdown_requested or msg.author == self.user:
            return
        # 统一入口
        try:
            await self._handle_message(msg)
        except Exception as e:
            logging.exception("处理 Discord 消息失败")
            await msg.channel.send(f"处理消息失败：{e}")

    # ---------- 消息主处理 ----------
    async def _handle_message(self, msg: discord.Message):
        cid = msg.channel.id
        if cid not in self.memory:
            self.memory[cid] = []
            self.async_tools[cid] = []
            self.file_links[cid] = []

        # 1. 快速重启
        if self.config.quick_restart and msg.content:
            if msg.content.strip() in {"/重启", "/restart"}:
                self.memory[cid].clear()
                await msg.reply("对话记录已重置。")
                return

        # 2. 拼装用户内容
        user_content = []
        user_text = ""
        has_media = False

        # 2.1 文本
        if msg.content:
            user_text = msg.content

        # 2.2 图片
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("image"):
                b64data = base64.b64encode(await att.read()).decode()
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{att.content_type};base64,{b64data}"}
                })
                has_media = True

        # 2.3 语音（任意音频当文件收）
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("audio"):
                audio_bytes = await att.read()
                asr_text = await self._transcribe_audio(audio_bytes, att.filename)
                if asr_text:
                    user_text += f"\n[语音转写] {asr_text}"
                else:
                    user_text += "\n[语音转写失败]"
        if self.config.wakeWord:
            if self.config.wakeWord not in user_text: # 唤醒词检测
                logging.info(f"未检测到唤醒词: {self.config.wakeWord}")
                return
        # 2.4 最终 user 消息
        if has_media and user_text:
            user_content.append({"type": "text", "text": user_text})
        if not has_media and not user_text:
            return  # 空消息

        self.memory[cid].append({"role": "user", "content": user_content or user_text})

        # 3. 请求 LLM
        settings = await load_settings()
        client = AsyncOpenAI(api_key="super-secret-key", base_url=f"http://127.0.0.1:{get_port()}/v1")

        # —— 与飞书完全对齐：取上下文工具 & 文件链接 —— #
        async_tools = self.async_tools.get(cid, [])
        file_links = self.file_links.get(cid, [])
        if cid not in self.async_tools:
            self.async_tools[cid] = []
        if cid not in self.file_links:
            self.file_links[cid] = []

        try:
            stream = await client.chat.completions.create(
                model=self.config.llm_model,
                messages=self.memory[cid],
                stream=True,
                extra_body={
                    "asyncToolsID": async_tools,
                    "fileLinks": file_links,
                },
            )
        except Exception as e:          # 捕获任意网络/超时异常
            logging.warning(f"LLM 请求失败: {e}")
            await msg.channel.send("LLM 响应超时，请稍后再试。")
            return

        # 4. 流式解析
        state = {"text_buffer": "", "image_buffer": "", "image_cache": []}
        full_response = []

        async for chunk in stream:
            delta_raw = chunk.choices[0].delta
            # ⭐ 安全取推理字段（对齐飞书）
            reasoning_content = getattr(delta_raw, "reasoning_content", None) or ""
            tool_content = getattr(delta_raw, "tool_content", None) or ""
            async_tool_id = getattr(delta_raw, "async_tool_id", None) or ""
            tool_link = getattr(delta_raw, "tool_link", None) or ""

            # —— 工具链路更新（完全等价飞书） —— #
            if tool_link and settings.get("tools", {}).get("toolMemorandum", {}).get("enabled"):
                if tool_link not in self.file_links[cid]:
                    self.file_links[cid].append(tool_link)

            if async_tool_id:
                if async_tool_id not in self.async_tools[cid]:
                    self.async_tools[cid].append(async_tool_id)
                else:
                    self.async_tools[cid].remove(async_tool_id)

            # 当前文本块
            content = delta_raw.content or ""
            if reasoning_content and self.config.reasoning_visible:
                content = reasoning_content

            full_response.append(content)
            state["text_buffer"] += content
            state["image_buffer"] += content

            # —— 分段发送（与飞书逻辑一致） —— #
            if self.config.separators:
                while True:
                    buffer = state["text_buffer"]
                    split_pos = -1
                    for sep in self.config.separators:
                        p = buffer.find(sep)
                        if p != -1:
                            split_pos = p + len(sep)
                            break
                    if split_pos == -1:
                        break
                    seg, state["text_buffer"] = buffer[:split_pos], buffer[split_pos:]
                    seg = self._clean_text(seg)
                    if seg:
                        await self._send_segment(msg, seg)

        # 5. 剩余文本
        if state["text_buffer"]:
            seg = self._clean_text(state["text_buffer"])
            if seg:
                await self._send_segment(msg, seg)

        # 6. 图片
        self._extract_images(state)
        for img_url in state["image_cache"]:
            await self._send_image(msg, img_url)

        # 7. TTS & 记忆
        full_content = "".join(full_response)
        if self.config.enable_tts:
            await self._send_voice(msg, full_content)

        self.memory[cid].append({"role": "assistant", "content": full_content})
        if self.config.memory_limit > 0:
            while len(self.memory[cid]) > self.config.memory_limit * 2:
                self.memory[cid].pop(0)

    # ---------- 工具 ----------
    async def _transcribe_audio(self, audio_bytes: bytes, filename: str) -> Optional[str]:
        form = aiohttp.FormData()
        form.add_field("audio", io.BytesIO(audio_bytes), filename=filename, content_type="audio/ogg")
        form.add_field("format", "auto")
        async with aiohttp.ClientSession() as s:
            async with s.post(f"http://127.0.0.1:{get_port()}/asr", data=form) as r:
                if r.status != 200:
                    return None
                res = await r.json()
                return res.get("text") if res.get("success") else None

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"https?://\S+", "", text)
        return text.strip()

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

    async def _send_segment(self, msg: discord.Message, seg: str):
        if self.config.enable_tts:
            pass
        else:
            await msg.channel.send(seg)

    async def _send_voice(self, msg: discord.Message, text: str):
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
            "mobile_optimized": True,  
            "format": "opus"           # 明确请求opus格式
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(f"http://127.0.0.1:{get_port()}/tts", json=payload) as r:
                if r.status != 200:
                    await msg.channel.send("语音生成失败")
                    return
                opus = await r.read()
                file = discord.File(io.BytesIO(opus), filename="voice.opus")
                await msg.channel.send(file=file)

    async def close(self):
        self._shutdown_requested = True
        await super().close()

    def _extract_images(self, state: Dict[str, Any]):
        """从缓冲区提取 markdown 图片链接"""
        buffer = state["image_buffer"]
        pattern = r'!\[.*?\]\((https?://[^\s)]+)'
        for m in re.finditer(pattern, buffer):
            state["image_cache"].append(m.group(1))

    async def _send_image(self, msg: discord.Message, img_url: str):
        """下载并发送图片到当前频道"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(img_url) as resp:
                    if resp.status != 200:
                        logging.warning(f"下载图片失败: {img_url}")
                        return
                    data = await resp.read()
                    ext = img_url.split("?")[0].split(".")[-1][:4]  # 简单取后缀
                    ext = ext if ext.lower() in {"png", "jpg", "jpeg", "gif", "webp"} else "png"
                    file = discord.File(io.BytesIO(data), filename=f"image.{ext}")
                    await msg.channel.send(file=file)
        except Exception as e:
            logging.exception(f"发送图片失败: {img_url}")