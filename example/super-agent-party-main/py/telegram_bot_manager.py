import asyncio, threading, weakref, logging, time
from typing import Optional, Dict, Any
from pydantic import BaseModel
from py.telegram_client import TelegramClient

class TelegramBotConfig(BaseModel):
    TelegramAgent: str        # LLM 模型名
    memoryLimit: int
    separators: list[str]
    reasoningVisible: bool
    quickRestart: bool
    enableTTS: bool
    bot_token: str            # Telegram 必填
    wakeWord: str              # 唤醒词

class TelegramBotManager:
    def __init__(self):
        self.bot_thread: Optional[threading.Thread] = None
        self.bot_client: Optional[TelegramClient] = None
        self.is_running = False
        self.config = None
        self.loop = None
        self._shutdown_event = threading.Event()
        self._startup_complete = threading.Event()
        self._ready_complete = threading.Event()
        self._startup_error: Optional[str] = None
        self._stop_requested = False

    # 以下四个接口与 FeishuBotManager 完全一致，直接复用路由
    def start_bot(self, config: TelegramBotConfig):
        # ADD: Check if previous thread is still alive
        if self.bot_thread and self.bot_thread.is_alive():
            raise Exception("Telegram 机器人线程正在清理中，请稍后再试")
        
        if self.is_running:
            raise Exception("Telegram 机器人已在运行")
        
        self.config = config
        self._shutdown_event.clear()
        self._startup_complete.clear()
        self._ready_complete.clear()
        self._startup_error = None
        self._stop_requested = False

        self.bot_thread = threading.Thread(
            target=self._run_bot_thread, args=(config,), daemon=True, name="TelegramBotThread"
        )
        self.bot_thread.start()

        if not self._startup_complete.wait(timeout=30):
            self.stop_bot()
            raise Exception("Telegram 机器人连接超时")
        if self._startup_error:
            self.stop_bot()
            raise Exception(f"Telegram 机器人启动失败: {self._startup_error}")
        if not self._ready_complete.wait(timeout=30):
            self.stop_bot()
            raise Exception("Telegram 机器人就绪超时")
        if not self.is_running:
            self.stop_bot()
            raise Exception("Telegram 机器人未能正常运行")


    def _run_bot_thread(self, config: TelegramBotConfig):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.bot_client = TelegramClient()
            self.bot_client.TelegramAgent = config.TelegramAgent
            self.bot_client.memoryLimit = config.memoryLimit
            self.bot_client.separators = config.separators or ["。", "\n", "？", "！"]
            self.bot_client.reasoningVisible = config.reasoningVisible
            self.bot_client.quickRestart = config.quickRestart
            self.bot_client.enableTTS = config.enableTTS
            self.bot_client.wakeWord = config.wakeWord
            self.bot_client.bot_token = config.bot_token
            self.bot_client._manager_ref = weakref.ref(self)
            self.bot_client._ready_callback = self._on_bot_ready


            self._startup_complete.set()
            self.loop.run_until_complete(self.bot_client.run())
        except Exception as e:
            if not self._stop_requested:
                logging.error(f"Telegram 机器人线程异常: {e}")
                self._startup_error = str(e)
            if not self._startup_complete.is_set():
                self._startup_complete.set()
            if not self._ready_complete.is_set():
                self._ready_complete.set()
        finally:
            self._cleanup()

    def _on_bot_ready(self):
        """机器人就绪回调（普通函数）"""
        self.is_running = True
        if not self._ready_complete.is_set():
            self._ready_complete.set()
        logging.info("Telegram 机器人已完全就绪")

    def _cleanup(self):
        self.is_running = False
        logging.info("开始清理 Telegram 机器人资源...")
        
        if self.loop and not self.loop.is_closed():
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                
                # Stop loop if running
                if self.loop.is_running():
                    self.loop.stop()
                
                # Close loop
                if not self.loop.is_closed():
                    self.loop.close()
            except Exception as e:
                logging.warning(f"关闭事件循环时出错: {e}")
        
        self.bot_client = None
        self.loop = None
        self._shutdown_event.set()
        logging.info("Telegram 机器人资源清理完成")

    def stop_bot(self):
        if not self.is_running and not self.bot_thread:
            logging.info("Telegram 机器人未在运行")
            return
        
        logging.info("正在停止 Telegram 机器人...")
        self._stop_requested = True
        self.is_running = False
        
        if self.bot_client:
            self.bot_client._shutdown_requested = True
        
        self._shutdown_event.set()
        
        # Increase to 15s (must be > polling timeout)
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=15)
            
            if self.bot_thread.is_alive():
                logging.warning("Telegram 机器人线程未能在15秒内停止")
                # Force cleanup as last resort
                self._cleanup()
        
        self._stop_requested = False
        logging.info("Telegram 机器人停止操作完成")

    def get_status(self):
        return {
            "is_running": self.is_running,
            "thread_alive": self.bot_thread.is_alive() if self.bot_thread else False,
            "client_ready": self.bot_client._is_ready if self.bot_client else False,
            "config": self.config.model_dump() if self.config else None,
            "loop_running": self.loop and not self.loop.is_closed() if self.loop else False,
            "startup_error": self._startup_error,
            "connection_established": self._startup_complete.is_set(),
            "ready_completed": self._ready_complete.is_set(),
            "stop_requested": self._stop_requested,
        }