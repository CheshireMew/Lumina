import logging
import os
import sys
import re

# ANSI 颜色去除正则
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class TeeOutput:
    """
    双重输出流:同时写入 stdout/stderr 和 文件。
    写入文件时会自动去除 ANSI 颜色代码。
    """
    def __init__(self, stream, file_handle):
        self.stream = stream
        self.file_handle = file_handle

    def write(self, data):
        # 写入原始流 (通常是控制台,保留颜色)
        try:
            self.stream.write(data)
            self.stream.flush()
        except UnicodeEncodeError:
            # Fallback for terminals that can't handle the char
            try:
                self.stream.write(data.encode('utf-8').decode(sys.stdout.encoding, errors='ignore'))
                self.stream.flush()
            except:
                pass # Give up on writing this chunk to console
        
        # 写入文件 (去除颜色)
        if self.file_handle:
            clean_data = ANSI_ESCAPE.sub('', data)
            self.file_handle.write(clean_data)
            self.file_handle.flush()

    def flush(self):
        self.stream.flush()
        if self.file_handle:
            self.file_handle.flush()

    def isatty(self):
        return hasattr(self.stream, 'isatty') and self.stream.isatty()

    def fileno(self):
        return self.stream.fileno()

def setup_logger(log_filename="server.log"):
    """
    配置全局日志和标准输出重定向。
    """
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    # 打开日志文件 (追加模式)
    log_file = open(log_path, 'a', encoding='utf-8')

    # [FIX] Force Windows stdout to UTF-8
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception as e:
            print(f"Warning: Failed to set utf-8 encoding: {e}")

    # 重定向 stdout 和 stderr
    sys.stdout = TeeOutput(sys.stdout, log_file)
    sys.stderr = TeeOutput(sys.stderr, log_file)

    # 配置 logging 模块
    # [Observability] Request ID Filter
    # [Observability] LogRecordFactory Injection
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get()
        return record
    logging.setLogRecordFactory(record_factory)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s')
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    logger = logging.getLogger("LuminaCore")
    logger.info(f"Logger initialized. Writing to {log_path}")
    return logger

import contextvars

# Global Context ContextVar for Request ID
request_id_ctx = contextvars.ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    """
    Log Filter that injects the current Request ID from ContextVar.
    """
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True
