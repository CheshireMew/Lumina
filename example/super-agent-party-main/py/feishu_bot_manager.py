# feishu_bot_manager.py
import asyncio
import json
import threading
import os
from typing import Optional, List, Dict, Any
import weakref
import aiohttp
import io
import base64
import logging
import re
import time
from pydantic import BaseModel
import requests
from PIL import Image
from openai import AsyncOpenAI

import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.api.im.v1 import GetMessageResourceRequest as ResReq
from lark_oapi.api.im.v1 import GetMessageResourceResponse as ResResp

from py.get_setting import get_port, load_settings


# 飞书机器人配置模型
class FeishuBotConfig(BaseModel):
    FeishuAgent: str          # LLM模型名
    memoryLimit: int          # 记忆条数限制
    appid: str                # 飞书APP_ID
    secret: str               # 飞书APP_SECRET
    separators: List[str]     # 消息分段符
    reasoningVisible: bool    # 是否显示推理过程
    quickRestart: bool        # 快速重启指令开关
    enableTTS: bool         # 是否启用TTS
    wakeWord: str              # 唤醒词


class FeishuBotManager:
    def __init__(self):
        self.bot_thread: Optional[threading.Thread] = None
        self.bot_client: Optional[FeishuClient] = None
        self.is_running = False
        self.config = None
        self.loop = None
        self._shutdown_event = threading.Event()
        self._startup_complete = threading.Event()
        self._ready_complete = threading.Event()
        self._startup_error = None
        self.ws = None  # 飞书长连接客户端
        self._stop_requested = False  # 添加停止请求标志
        
    def start_bot(self, config):
        """在新线程中启动飞书机器人"""
        if self.is_running:
            raise Exception("飞书机器人已在运行")
            
        self.config = config
        self._shutdown_event.clear()
        self._startup_complete.clear()
        self._ready_complete.clear()
        self._startup_error = None
        self._stop_requested = False
        
        # 使用线程方式启动
        self.bot_thread = threading.Thread(
            target=self._run_bot_thread,
            args=(config,),
            daemon=True,
            name="FeishuBotThread"
        )
        self.bot_thread.start()
        
        # 等待启动确认
        if not self._startup_complete.wait(timeout=30):
            self.stop_bot()
            raise Exception("飞书机器人连接超时")
            
        # 检查是否有启动错误
        if self._startup_error:
            self.stop_bot()
            raise Exception(f"飞书机器人启动失败: {self._startup_error}")
        
        # 等待机器人就绪
        if not self._ready_complete.wait(timeout=30):
            self.stop_bot()
            raise Exception("飞书机器人就绪超时，请检查网络连接和配置")
            
        if not self.is_running:
            self.stop_bot()
            raise Exception("飞书机器人未能正常运行")
    
    def _run_bot_thread(self, config):
        """线程中运行飞书机器人"""
        self.loop = None
        
        try:
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 创建飞书客户端
            self.bot_client = FeishuClient()
            self.bot_client.FeishuAgent = config.FeishuAgent
            self.bot_client.memoryLimit = config.memoryLimit
            self.bot_client.separators = config.separators if config.separators else ['。', '\n', '？', '！']
            self.bot_client.reasoningVisible = config.reasoningVisible
            self.bot_client.quickRestart = config.quickRestart
            self.bot_client.appid = config.appid
            self.bot_client.secret = config.secret
            self.bot_client.enableTTS = config.enableTTS
            self.bot_client.wakeWord = config.wakeWord
            
            # 设置弱引用以避免循环引用
            self.bot_client._manager_ref = weakref.ref(self)
            # 设置就绪回调
            self.bot_client._ready_callback = self._on_bot_ready
            
            # 初始化飞书长连接相关
            lark_client = lark.Client.builder()\
                .app_id(config.appid)\
                .app_secret(config.secret)\
                .log_level(lark.LogLevel.INFO)\
                .build()
                
            self.bot_client.lark_client = lark_client
            
            # 创建事件处理程序
            event_dispatcher = lark.EventDispatcherHandler.builder("", "")\
                .register_p2_im_message_receive_v1(self.bot_client.sync_handle_message)\
                .build()
                
            # 创建长连接
            self.ws = lark.ws.Client(
                config.appid, 
                config.secret,
                event_handler=event_dispatcher,
                log_level=lark.LogLevel.INFO,
                auto_reconnect=False  # 禁用自动重连，便于控制
            )
            
            # 在事件循环中运行WebSocket客户端
            self.loop.run_until_complete(self._async_run_websocket())
            
        except Exception as e:
            if not self._stop_requested:  # 只有非主动停止的错误才记录
                logging.error(f"飞书机器人线程异常: {e}")
                # 确保错误被记录并传递
                if not self._startup_error:
                    self._startup_error = str(e)
            # 确保启动等待被解除
            if not self._startup_complete.is_set():
                self._startup_complete.set()
            if not self._ready_complete.is_set():
                self._ready_complete.set()
        finally:
            self._cleanup()
    
    async def _async_run_websocket(self):
        """异步运行WebSocket连接"""
        try:
            # 建立连接
            await self.ws._connect()
            
            # 设置启动完成标志
            self._startup_complete.set()
            self._ready_complete.set()
            self.is_running = True
            logging.info("飞书机器人WebSocket连接已建立")
            
            # 启动ping循环
            ping_task = asyncio.create_task(self.ws._ping_loop())
            
            # 启动消息接收循环
            receive_task = asyncio.create_task(self._message_receive_loop())
            
            # 等待任务完成或停止信号
            try:
                await asyncio.gather(ping_task, receive_task, return_exceptions=True)
            except asyncio.CancelledError:
                logging.info("WebSocket任务被取消")
            except Exception as e:
                if not self._stop_requested:
                    logging.error(f"WebSocket任务异常: {e}")
                    
        except Exception as e:
            if not self._stop_requested:
                logging.error(f"WebSocket连接失败: {e}")
                self._startup_error = str(e)
            raise
    
    async def _message_receive_loop(self):
        """消息接收循环"""
        try:
            while not self._stop_requested and not self._shutdown_event.is_set():
                if self.ws._conn is None:
                    break
                    
                try:
                    # 设置超时接收消息
                    msg = await asyncio.wait_for(self.ws._conn.recv(), timeout=1.0)
                    # 处理消息
                    asyncio.create_task(self.ws._handle_message(msg))
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue
                except Exception as e:
                    if not self._stop_requested:
                        logging.error(f"接收消息异常: {e}")
                    break
                    
        except asyncio.CancelledError:
            logging.info("消息接收循环被取消")
        except Exception as e:
            if not self._stop_requested:
                logging.error(f"消息接收循环异常: {e}")
    
    def _on_bot_ready(self):
        """机器人就绪回调"""
        self.is_running = True
        if not self._ready_complete.is_set():
            self._ready_complete.set()
        logging.info("飞书机器人已完全就绪")

    def _cleanup(self):
        """清理资源"""
        self.is_running = False
        logging.info("开始清理飞书机器人资源...")
        
        # 关闭长连接
        if self.ws and self.loop and not self.loop.is_closed():
            try:
                # 在事件循环中异步关闭连接
                if asyncio.iscoroutinefunction(self.ws._disconnect):
                    self.loop.run_until_complete(self.ws._disconnect())
                logging.info("飞书长连接已关闭")
            except Exception as e:
                logging.warning(f"关闭飞书长连接时出错: {e}")
        
        # 清理事件循环
        if self.loop and not self.loop.is_closed():
            try:
                # 获取所有未完成的任务
                try:
                    pending = asyncio.all_tasks(self.loop)
                except RuntimeError:
                    # 如果事件循环已经关闭，可能会抛出RuntimeError
                    pending = []
                
                # 取消所有未完成的任务
                for task in pending:
                    if not task.done():
                        task.cancel()
                
                # 等待任务完成或被取消
                if pending:
                    try:
                        self.loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    except Exception as e:
                        logging.warning(f"等待任务取消时出错: {e}")
                
                # 关闭事件循环
                self.loop.close()
                logging.info("事件循环已关闭")
            except Exception as e:
                logging.warning(f"关闭事件循环时出错: {e}")
                
        self.bot_client = None
        self.loop = None
        self.ws = None
        self._shutdown_event.set()
        logging.info("飞书机器人资源清理完成")
            
    def stop_bot(self):
        """停止飞书机器人"""
        if not self.is_running and not self.bot_thread:
            logging.info("飞书机器人未在运行")
            return
            
        logging.info("正在停止飞书机器人...")
        
        # 设置停止标志
        self._stop_requested = True
        self._shutdown_event.set()
        self.is_running = False
        
        # 如果有事件循环，尝试优雅停止
        if self.loop and not self.loop.is_closed():
            try:
                # 获取所有任务并取消它们
                try:
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        if not task.done():
                            task.cancel()
                except RuntimeError:
                    pass  # 事件循环可能已经关闭
                    
                # 关闭WebSocket连接
                if self.ws and hasattr(self.ws, '_disconnect'):
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.ws._disconnect(), 
                            self.loop
                        )
                        future.result(timeout=2)
                        logging.info("WebSocket连接已关闭")
                    except Exception as e:
                        logging.warning(f"关闭WebSocket连接时出错: {e}")
                        
            except Exception as e:
                logging.warning(f"优雅停止过程中出错: {e}")
        
        # 等待线程结束
        if self.bot_thread and self.bot_thread.is_alive():
            try:
                logging.info("等待飞书机器人线程结束...")
                self.bot_thread.join(timeout=5)
                if self.bot_thread.is_alive():
                    logging.warning("飞书机器人线程在5秒超时后仍在运行，但这是预期的清理行为")
                else:
                    logging.info("飞书机器人线程已正常结束")
            except Exception as e:
                logging.warning(f"等待线程结束时出错: {e}")
        
        # 重置停止标志
        self._stop_requested = False
        logging.info("飞书机器人停止操作完成")

    def get_status(self):
        """获取机器人状态"""
        return {
            "is_running": self.is_running,
            "thread_alive": self.bot_thread.is_alive() if self.bot_thread else False,
            "client_ready": self.bot_client._is_ready if self.bot_client else False,
            "config": self.config.model_dump() if self.config else None,
            "loop_running": self.loop and not self.loop.is_closed() if self.loop else False,
            "startup_error": self._startup_error,
            "connection_established": self._startup_complete.is_set(),
            "ready_completed": self._ready_complete.is_set(),
            "stop_requested": self._stop_requested
        }

    def __del__(self):
        """析构函数确保资源清理"""
        try:
            self.stop_bot()
        except:
            pass


class FeishuClient:
    def __init__(self):
        self.FeishuAgent = "super-model"
        self.memoryLimit = 10
        self.memoryList = {}
        self.asyncToolsID = {}
        self.fileLinks = {}
        self.separators = ['。', '\n', '？', '！']
        self.reasoningVisible = False
        self.quickRestart = True
        self._is_ready = False
        self.appid = None
        self.secret = None
        self.lark_client = None
        self.port = get_port()
        self._shutdown_requested = False
        self._manager_ref = None
        self._ready_callback = None
        self.enableTTS = False
        self.wakeWord = None
        
    def sync_handle_message(self, data: P2ImMessageReceiveV1) -> None:
        """同步消息处理函数，用于注册到飞书事件分发器"""
        # 检查是否已请求停止
        if self._shutdown_requested:
            return
            
        # 检查管理器是否请求停止
        if self._manager_ref:
            manager = self._manager_ref()
            if manager and manager._stop_requested:
                return
        
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果当前线程没有事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 检查事件循环是否已关闭
            if loop.is_closed():
                return
            
            # 在事件循环中运行异步函数
            future = asyncio.run_coroutine_threadsafe(
                self.handle_message(data), 
                loop
            )
            
            # 可选：等待结果（如果需要）
            # future.result(timeout=30)
        except Exception as e:
            if not self._shutdown_requested:
                logging.error(f"处理消息时发生异常: {e}")

    async def handle_message(self, data: P2ImMessageReceiveV1) -> None:
        """处理飞书消息的主函数"""
        # 多重检查停止状态
        if self._shutdown_requested:
            return
        
        if self._manager_ref:
            manager = self._manager_ref()
            if manager and (manager._stop_requested or not manager.is_running):
                return
        
        # 标记为就绪状态
        if not self._is_ready:
            self._is_ready = True
            if self._ready_callback:
                self._ready_callback()
        
        msg = data.event.message
        msg_type = msg.message_type
        chat_type = msg.chat_type
        logging.info(f"收到 {chat_type} 消息，类型：{msg_type}")
        
        # 准备OpenAI客户端
        settings = await load_settings()
        client = AsyncOpenAI(
            api_key="super-secret-key",
            base_url=f"http://127.0.0.1:{self.port}/v1"
        )
        
        # 处理消息内容
        user_content = []  # 这是一个列表，用于多模态内容
        user_text = ""     # 这是一个字符串，用于纯文本内容
        has_image = False  # 标记是否包含图片
        
        # 获取聊天ID并初始化记忆
        chat_id = msg.chat_id
        if chat_id not in self.memoryList:
            self.memoryList[chat_id] = []
        
        # 文本消息处理
        if msg_type == "text":
            try:
                text = json.loads(msg.content).get("text", "")
                
                # 处理快速重启命令
                if self.quickRestart and text:
                    if "/重启" in text:
                        self.memoryList[chat_id] = []
                        await self._send_text(msg, "对话记录已重置。")
                        return
                    if "/restart" in text:
                        self.memoryList[chat_id] = []
                        await self._send_text(msg, "The conversation record has been reset.")
                        return
                
                # 记录文本内容
                user_text = text
                if self.wakeWord:
                    if self.wakeWord not in user_text:
                        logging.info(f"未检测到唤醒词: {self.wakeWord}")
                        return

            except Exception as e:
                logging.error(f"文本解析失败：{e}")
                await self._send_text(msg, f"文本解析失败：{e}")
                return
        
        # 图片消息处理
        elif msg_type == "image":
            try:
                image_key = json.loads(msg.content).get("image_key", "")
                if not image_key:
                    await self._send_text(msg, "无效的图片消息")
                    return
                
                # 下载图片
                res_req = ResReq.builder()\
                    .message_id(msg.message_id)\
                    .file_key(image_key)\
                    .type("image")\
                    .build()
                
                res_resp = self.lark_client.im.v1.message_resource.get(res_req)
                if not res_resp.success():
                    await self._send_text(msg, f"下载图片失败：{res_resp.msg}")
                    return
                
                # 获取图片二进制数据
                img_bin = res_resp.file.read()
                
                # 转换为Base64以传给模型
                content_type = "image/jpeg"  # 假设为JPEG格式，可根据实际情况修改
                base64_data = base64.b64encode(img_bin).decode("utf-8")
                data_uri = f"data:{content_type};base64,{base64_data}"
                
                # 标记包含图片
                has_image = True
                
                # 添加图片内容
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": data_uri
                    }
                })
                
                # 如果用户还有文本，也一并处理
                if "text" in json.loads(msg.content):
                    text = json.loads(msg.content).get("text", "")
                    user_text = text
                    
            except Exception as e:
                logging.error(f"图片处理失败：{e}")
                await self._send_text(msg, f"图片处理失败：{e}")
                return
                
        # 富文本消息处理（包含图片）
        elif msg_type == "post":
            try:
                # 解析富文本内容
                content_json = json.loads(msg.content)
                logging.info(f"收到富文本消息: {content_json}")
                
                # 获取post内容
                post_content = content_json
                
                # 提取文本内容
                extracted_text = self._extract_text_from_post(post_content)
                if extracted_text:
                    user_text = extracted_text
                    logging.info(f"成功提取文本: {user_text}")
                
                # 提取图片内容
                image_keys = self._extract_images_from_post(post_content)
                
                for image_key in image_keys:
                    try:
                        logging.info(f"处理富文本图片: {image_key}")
                        # 下载图片
                        res_req = ResReq.builder()\
                            .message_id(msg.message_id)\
                            .file_key(image_key)\
                            .type("image")\
                            .build()
                        
                        res_resp = self.lark_client.im.v1.message_resource.get(res_req)
                        if not res_resp.success():
                            logging.warning(f"下载富文本图片失败: {res_resp.msg}")
                            continue
                        
                        # 获取图片二进制数据
                        img_bin = res_resp.file.read()
                        logging.info(f"下载图片成功: {len(img_bin)} 字节")
                        
                        # 转换为Base64
                        content_type = "image/jpeg"
                        base64_data = base64.b64encode(img_bin).decode("utf-8")
                        data_uri = f"data:{content_type};base64,{base64_data}"
                        
                        # 标记包含图片
                        has_image = True
                        
                        # 添加图片内容
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri
                            }
                        })
                        logging.info("图片处理成功并添加到用户内容")
                    except Exception as e:
                        logging.warning(f"处理富文本中的图片失败: {e}")
                        import traceback
                        logging.debug(traceback.format_exc())
                
            except Exception as e:
                logging.error(f"富文本处理失败: {e}")
                import traceback
                logging.debug(traceback.format_exc())
                await self._send_text(msg, f"富文本处理失败: {e}")
                return
        
        # 音频消息处理
        elif msg_type == "audio":
            try:
                # 解析音频消息内容
                content_json = json.loads(msg.content)
                file_key = content_json.get("file_key", "")
                duration = content_json.get("duration", 0)
                
                if not file_key:
                    await self._send_text(msg, "无效的音频消息")
                    return
                
                logging.info(f"收到音频消息，file_key: {file_key}, duration: {duration}ms")
                
                # 下载音频文件
                res_req = ResReq.builder()\
                    .message_id(msg.message_id)\
                    .file_key(file_key)\
                    .type("file")\
                    .build()
                
                res_resp = self.lark_client.im.v1.message_resource.get(res_req)
                if not res_resp.success():
                    await self._send_text(msg, f"下载音频失败：{res_resp.msg}")
                    return
                
                # 获取音频二进制数据
                audio_data = res_resp.file.read()
                logging.info(f"音频下载成功，大小: {len(audio_data)} 字节")
                
                # 调用本地ASR接口转换为文字
                transcribed_text = await self._transcribe_audio(audio_data, file_key)
                
                if not transcribed_text:
                    await self._send_text(msg, "语音转文字失败，请重试")
                    return
                
                logging.info(f"语音识别结果: {transcribed_text}")
                
                # 将识别结果作为文本消息处理
                user_text = transcribed_text
                
                if self.wakeWord and user_text:
                    if self.wakeWord not in user_text:
                        logging.info(f"未检测到唤醒词: {self.wakeWord}")
                        return
                
            except Exception as e:
                logging.error(f"音频处理失败：{e}")
                import traceback
                logging.debug(traceback.format_exc())
                await self._send_text(msg, f"音频处理失败：{e}")
                return

        # 不支持的消息类型
        else:
            await self._send_text(msg, f"暂不支持的消息类型：{msg_type}")
            return
        
        # 构建最终的用户消息
        logging.info(f"处理结果 - has_image: {has_image}, user_text长度: {len(user_text) if user_text else 0}, user_content长度: {len(user_content)}")

        if has_image:
            # 如果有文本，添加到多模态内容中
            if user_text:
                user_content.append({
                    "type": "text",
                    "text": user_text
                })
            
            # 检查是否有有效内容
            if user_content:
                self.memoryList[chat_id].append({
                    "role": "user", 
                    "content": user_content
                })
                logging.info(f"已添加多模态内容到对话记忆，总数: {len(user_content)}")
            else:
                await self._send_text(msg, "未能提取有效内容，请重试")
                return
        else:
            # 纯文本消息
            if user_text:
                self.memoryList[chat_id].append({
                    "role": "user", 
                    "content": user_text
                })
                logging.info(f"已添加纯文本内容到对话记忆: {user_text[:50]}...")
            else:
                await self._send_text(msg, "未检测到有效的消息内容")
                return
                
            self.memoryList[chat_id].append({
                "role": "user", 
                "content": user_text
            })
        
        # 初始化消息状态
        state = {
            "text_buffer": "",
            "image_buffer": "",
            "image_cache": []
        }
        
        try:
            # 准备上下文工具ID和文件链接
            asyncToolsID = self.asyncToolsID.get(chat_id, [])
            fileLinks = self.fileLinks.get(chat_id, [])
            
            if chat_id not in self.asyncToolsID:
                self.asyncToolsID[chat_id] = []
            if chat_id not in self.fileLinks:
                self.fileLinks[chat_id] = []
            
            # 流式调用API
            stream = await client.chat.completions.create(
                model=self.FeishuAgent,
                messages=self.memoryList[chat_id],
                stream=True,
                extra_body={
                    "asyncToolsID": asyncToolsID,
                    "fileLinks": fileLinks,
                }
            )
            
            full_response = []
            async for chunk in stream:
                reasoning_content = ""
                tool_content = ""
                
                if chunk.choices:
                    chunk_dict = chunk.model_dump()
                    delta = chunk_dict["choices"][0].get("delta", {})
                    
                    if delta:
                        reasoning_content = delta.get("reasoning_content", "")
                        tool_content = delta.get("tool_content", "")
                        async_tool_id = delta.get("async_tool_id", "")
                        tool_link = delta.get("tool_link", "")
                        
                        # 处理工具链接
                        if tool_link and settings["tools"]["toolMemorandum"]["enabled"]:
                            self.fileLinks[chat_id].append(tool_link)
                        
                        # 处理异步工具ID
                        if async_tool_id:
                            if async_tool_id not in self.asyncToolsID[chat_id]:
                                self.asyncToolsID[chat_id].append(async_tool_id)
                            else:
                                self.asyncToolsID[chat_id].remove(async_tool_id)
                
                # 获取当前文本块
                content = chunk.choices[0].delta.content or ""
                full_response.append(content)
                
                # 如果开启推理可视，则显示推理内容
                if reasoning_content and self.reasoningVisible:
                    content = reasoning_content
                
                # 更新缓冲区
                state["text_buffer"] += content
                state["image_buffer"] += content
                
                # 处理文本实时发送
                if self.separators:
                    while True:
                        # 查找分隔符
                        buffer = state["text_buffer"]
                        split_pos = -1
                        for i, c in enumerate(buffer):
                            if c in self.separators:
                                split_pos = i + 1
                                break
                                
                        # 有分段符，发送当前段落
                        if split_pos > 0:
                            current_chunk = buffer[:split_pos]
                            state["text_buffer"] = buffer[split_pos:]
                            
                            # 清洗并发送文本
                            clean_text = self._clean_text(current_chunk)
                            if clean_text:
                                if self.enableTTS:
                                    pass
                                else:
                                    await self._send_text(msg, clean_text)
                        else:
                            break
            
            # 提取图片链接
            self._extract_images(state)
            
            # 处理剩余文本
            if state["text_buffer"]:
                clean_text = self._clean_text(state["text_buffer"])
                if clean_text:
                    if self.enableTTS:
                        pass
                    else:
                        await self._send_text(msg, clean_text)
            
            # 发送图片
            for img_url in state["image_cache"]:
                await self._send_image(msg, img_url)
            
            # 更新记忆
            full_content = "".join(full_response)
            if self.enableTTS:
                await self._send_voice(msg, full_content)
            self.memoryList[chat_id].append({"role": "assistant", "content": full_content})
            
            # 限制记忆长度
            if self.memoryLimit > 0:
                while len(self.memoryList[chat_id]) > self.memoryLimit * 2:  # 成对移除
                    self.memoryList[chat_id].pop(0)  # 移除最早的用户消息
                    if self.memoryList[chat_id]:  # 确保还有元素
                        self.memoryList[chat_id].pop(0)  # 移除最早的助手回复
            
        except Exception as e:
            logging.error(f"处理消息异常: {e}")
            await self._send_text(msg, f"处理消息失败: {e}")

    async def _transcribe_audio(self, audio_data: bytes, file_key: str) -> str:
        """调用本地ASR接口转换音频为文字"""
        try:
            # 准备音频文件
            audio_file = io.BytesIO(audio_data)
            
            # 根据file_key或其他信息推断音频格式，飞书通常使用ogg或m4a格式
            # 这里我们让ASR接口自动检测格式
            filename = f"{file_key}.ogg"  # 飞书音频通常是ogg格式
            
            # 准备multipart/form-data请求
            form_data = aiohttp.FormData()
            form_data.add_field('audio', 
                            audio_file, 
                            filename=filename, 
                            content_type='audio/ogg')
            form_data.add_field('format', 'auto')  # 让ASR自动检测格式
            
            # 调用本地ASR接口
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://127.0.0.1:{self.port}/asr",
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=60)  # 设置超时时间
                ) as response:
                    
                    if response.status != 200:
                        logging.error(f"ASR请求失败，状态码: {response.status}")
                        response_text = await response.text()
                        logging.error(f"ASR错误响应: {response_text}")
                        return None
                    
                    # 解析响应
                    result = await response.json()
                    
                    if result.get("success", False):
                        transcribed_text = result.get("text", "").strip()
                        if transcribed_text:
                            logging.info(f"ASR识别成功，引擎: {result.get('engine', 'unknown')}, "
                                    f"格式: {result.get('format', 'unknown')}")
                            return transcribed_text
                        else:
                            logging.warning("ASR识别结果为空")
                            return None
                    else:
                        error_msg = result.get("error", "未知错误")
                        logging.error(f"ASR识别失败: {error_msg}")
                        return None
                        
        except asyncio.TimeoutError:
            logging.error("ASR请求超时")
            return None
        except Exception as e:
            logging.error(f"ASR转换异常: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            return None



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


    async def _send_voice(self, original_msg, text):
        """发送语音消息（opus专用版本）"""
        try:
            from py.get_setting import load_settings
            settings = await load_settings()
            tts_settings = settings.get("ttsSettings", {})
            index = 0
            text = self.clean_markdown(text)
            # 专门为飞书请求opus格式
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
                        await self._send_text(original_msg, "语音生成失败，请稍后重试")
                        return

                    opus_data = await resp.read()
                    audio_format = resp.headers.get("X-Audio-Format", "unknown")
                    
                    logging.info(f"TTS响应成功，opus大小: {len(opus_data) / 1024:.1f}KB，格式: {audio_format}")

                    if len(opus_data) < 100:
                        logging.error(f"opus数据异常，大小仅 {len(opus_data)} 字节")
                        await self._send_text(original_msg, "语音生成异常，请重试")
                        return

                    # 检查文件大小（飞书限制）
                    max_size = 10 * 1024 * 1024  # 10MB
                    if len(opus_data) > max_size:
                        logging.error(f"opus文件过大: {len(opus_data) / (1024*1024):.1f}MB")
                        await self._send_text(original_msg, "语音文件过大，请尝试较短的文本")
                        return

                    # 上传opus文件到飞书
                    opus_file = io.BytesIO(opus_data)
                    
                    logging.info("开始上传opus语音文件到飞书...")
                    
                    try:
                        upload_req = CreateFileRequest.builder() \
                            .request_body(
                                CreateFileRequestBody.builder()
                                .file_type("opus")           # 飞书要求的opus类型
                                .file_name("voice.opus")     # opus文件名
                                .file(opus_file)
                                .build()
                            ).build()

                        upload_resp = self.lark_client.im.v1.file.create(upload_req)
                        
                    except Exception as upload_error:
                        logging.error(f"构建opus上传请求失败: {upload_error}")
                        await self._send_text(original_msg, "语音上传失败，请重试")
                        return

                    # 检查上传结果
                    if not upload_resp.success():
                        logging.error(f"上传opus语音失败: {upload_resp.code} - {upload_resp.msg}")
                        
                        # 详细的错误处理
                        if upload_resp.code == 234001:
                            await self._send_text(original_msg, "语音格式错误，请联系管理员")
                        elif upload_resp.code == 234002:
                            await self._send_text(original_msg, "语音文件过大，请尝试较短的文本")
                        elif upload_resp.code == 99991663:
                            await self._send_text(original_msg, "机器人权限不足，请检查应用权限")
                        else:
                            await self._send_text(original_msg, f"语音上传失败: {upload_resp.msg}")
                        return

                    file_key = upload_resp.data.file_key
                    logging.info(f"opus语音上传成功，file_key: {file_key}")

                    # 发送语音消息
                    chat_type = original_msg.chat_type
                    audio_content = json.dumps({"file_key": file_key})
                    
                    try:
                        if chat_type == "p2p":
                            req = CreateMessageRequest.builder() \
                                .receive_id_type("chat_id") \
                                .request_body(
                                    CreateMessageRequestBody.builder()
                                    .receive_id(original_msg.chat_id)
                                    .msg_type("audio")
                                    .content(audio_content)
                                    .build()
                                ).build()
                            
                            send_resp = self.lark_client.im.v1.message.create(req)
                        else:
                            req = ReplyMessageRequest.builder() \
                                .message_id(original_msg.message_id) \
                                .request_body(
                                    ReplyMessageRequestBody.builder()
                                    .msg_type("audio")
                                    .content(audio_content)
                                    .build()
                                ).build()
                            
                            send_resp = self.lark_client.im.v1.message.reply(req)

                        if not send_resp.success():
                            logging.error(f"发送opus语音消息失败: {send_resp.code} - {send_resp.msg}")
                            
                            if send_resp.code == 230002:
                                await self._send_text(original_msg, "语音消息格式不支持")
                            elif send_resp.code == 99991663:
                                await self._send_text(original_msg, "机器人无发送消息权限")
                            else:
                                await self._send_text(original_msg, f"语音发送失败: {send_resp.msg}")
                        else:
                            logging.info(f"opus语音消息发送成功，消息ID: {send_resp.data.message_id}")

                    except Exception as send_error:
                        logging.error(f"发送opus语音消息异常: {send_error}")
                        await self._send_text(original_msg, "语音消息发送失败")

        except asyncio.TimeoutError:
            logging.error("opus TTS请求超时")
            await self._send_text(original_msg, "语音生成超时，请稍后重试")
        except Exception as e:
            logging.error(f"发送opus语音异常: {e}")
            import traceback
            logging.debug(traceback.format_exc())
            await self._send_text(original_msg, "语音功能暂时不可用，请稍后重试")


    # 修改 _extract_text_from_post 方法
    def _extract_text_from_post(self, post_content):
        """从富文本中提取文本内容"""
        extracted_text = []
        
        try:
            # 提取标题
            if isinstance(post_content, dict):
                title = post_content.get("title", "")
                if title:
                    extracted_text.append(title)
                
                # 提取内容
                if "content" in post_content and isinstance(post_content["content"], list):
                    for paragraph in post_content["content"]:
                        paragraph_text = []
                        
                        if isinstance(paragraph, list):
                            for element in paragraph:
                                if isinstance(element, dict) and "tag" in element:
                                    tag = element["tag"]
                                    
                                    # 处理文本元素
                                    if tag == "text" and "text" in element:
                                        paragraph_text.append(element["text"])
                                    
                                    # 处理超链接
                                    elif tag == "a" and "text" in element:
                                        paragraph_text.append(element.get("text", ""))
                                    
                                    # 处理@用户
                                    elif tag == "at":
                                        user_name = element.get("user_name", "")
                                        paragraph_text.append(f"@{user_name}")
                        
                        # 添加当前段落文本
                        if paragraph_text:
                            extracted_text.append(" ".join(paragraph_text))
                            
            # 打印提取结果的日志
            logging.info(f"提取的文本内容: {extracted_text}")
        except Exception as e:
            logging.warning(f"从富文本提取文本失败: {e}")
            import traceback
            logging.debug(traceback.format_exc())
        
        return "\n".join(extracted_text)

    # 修改 _extract_images_from_post 方法
    def _extract_images_from_post(self, post_content):
        """从富文本中提取图片key"""
        image_keys = []
        
        try:
            if isinstance(post_content, dict) and "content" in post_content:
                content_array = post_content["content"]
                
                if isinstance(content_array, list):
                    for paragraph in content_array:
                        if isinstance(paragraph, list):
                            for element in paragraph:
                                if isinstance(element, dict) and "tag" in element:
                                    tag = element["tag"]
                                    
                                    # 处理图片元素
                                    if tag == "img" and "image_key" in element:
                                        image_keys.append(element["image_key"])
                                        logging.info(f"找到图片key: {element['image_key']}")
                                    
                                    # 处理媒体元素
                                    elif tag == "media" and "image_key" in element:
                                        image_keys.append(element["image_key"])
                                        logging.info(f"找到媒体图片key: {element['image_key']}")
            
            logging.info(f"提取的图片keys: {image_keys}")
        except Exception as e:
            logging.warning(f"从富文本提取图片失败: {e}")
            import traceback
            logging.debug(traceback.format_exc())
        
        return image_keys



    
    def _extract_images(self, state):
        """从文本中提取图片链接"""
        buffer = state["image_buffer"]
        # 匹配Markdown图片格式
        pattern = r'!\[.*?\]\((https?://[^\s\)]+)'
        matches = re.finditer(pattern, buffer)
        for match in matches:
            state["image_cache"].append(match.group(1))
    
    def _clean_text(self, text):
        """清理文本中的特殊标记"""
        # 移除图片标记
        clean = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # 移除超链接
        clean = re.sub(r'\[.*?\]\(.*?\)', '', clean)
        # 移除纯URL
        clean = re.sub(r'https?://\S+', '', clean)
        return clean.strip()
    
    async def _send_text(self, original_msg, text):
        """发送文本消息"""
        try:
            if not text:
                return
                
            chat_type = original_msg.chat_type
            
            if chat_type == "p2p":  # 私聊
                req = CreateMessageRequest.builder()\
                    .receive_id_type("chat_id")\
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(original_msg.chat_id)
                        .msg_type("text")
                        .content(json.dumps({"text": text}))
                        .build()
                    ).build()
                
                resp = self.lark_client.im.v1.message.create(req)
                
            else:  # 群聊
                req = ReplyMessageRequest.builder()\
                    .message_id(original_msg.message_id)\
                    .request_body(
                        ReplyMessageRequestBody.builder()
                        .msg_type("text")
                        .content(json.dumps({"text": text}))
                        .build()
                    ).build()
                
                resp = self.lark_client.im.v1.message.reply(req)
            
            if not resp.success():
                logging.error(f"发送文本失败: {resp.code} {resp.msg}")
                
        except Exception as e:
            logging.error(f"发送文本异常: {e}")
    
    async def _send_image(self, original_msg, image_url):
        """发送图片消息"""
        try:
            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        logging.error(f"下载图片失败: {image_url}")
                        return
                    
                    image_data = await response.read()
            
            # 转换为文件对象
            img_file = io.BytesIO(image_data)
            
            # 上传图片
            upload_req = CreateImageRequest.builder()\
                .request_body(
                    CreateImageRequestBody.builder()
                    .image_type("message")
                    .image(img_file)
                    .build()
                ).build()
            
            upload_resp = self.lark_client.im.v1.image.create(upload_req)
            
            if not upload_resp.success():
                logging.error(f"上传图片失败: {upload_resp.msg}")
                return
            
            image_key = upload_resp.data.image_key
            
            # 发送图片消息
            chat_type = original_msg.chat_type
            
            if chat_type == "p2p":  # 私聊
                req = CreateMessageRequest.builder()\
                    .receive_id_type("chat_id")\
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(original_msg.chat_id)
                        .msg_type("image")
                        .content(json.dumps({"image_key": image_key}))
                        .build()
                    ).build()
                
                resp = self.lark_client.im.v1.message.create(req)
                
            else:  # 群聊
                req = ReplyMessageRequest.builder()\
                    .message_id(original_msg.message_id)\
                    .request_body(
                        ReplyMessageRequestBody.builder()
                        .msg_type("image")
                        .content(json.dumps({"image_key": image_key}))
                        .build()
                    ).build()
                
                resp = self.lark_client.im.v1.message.reply(req)
            
            if not resp.success():
                logging.error(f"发送图片失败: {resp.code} {resp.msg}")
                
        except Exception as e:
            logging.error(f"发送图片异常: {e}")
