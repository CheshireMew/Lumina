import logging
import os
import sys
import re
import contextvars

# Global Context for Request ID
request_id_ctx = contextvars.ContextVar("request_id", default="-")
# Global Context for Session ID (User-facing session)
session_id_ctx = contextvars.ContextVar("session_id", default="-")

def _inject_context_to_record(record):
    """Utility to inject request/session context into a LogRecord."""
    if not hasattr(record, "request_id"):
        val = request_id_ctx.get()
        record.request_id = val if val else "-"
    
    if not hasattr(record, "session_id"):
        s_val = session_id_ctx.get()
        record.session_id = s_val if s_val else "-"
    
    # Force into __dict__ for PercentStyle formatters used by libraries
    if "request_id" not in record.__dict__:
        record.__dict__["request_id"] = record.request_id
    if "session_id" not in record.__dict__:
        record.__dict__["session_id"] = record.session_id

_original_factory = logging.getLogRecordFactory()

def record_factory(*args, **kwargs):
    record = _original_factory(*args, **kwargs)
    _inject_context_to_record(record)
    return record

# Apply global factory immediately on module load
logging.setLogRecordFactory(record_factory)

class RequestIdFilter(logging.Filter):
    """
    Log Filter that injects the current Request ID from ContextVar.
    """
    def filter(self, record):
        if not hasattr(record, "request_id"):
            val = request_id_ctx.get()
            record.request_id = val if val else "-"
        return True

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

    def reconfigure(self, *args, **kwargs):
        """Pass through reconfigure calls to the underlying stream (Python 3.7+)."""
        if hasattr(self.stream, 'reconfigure'):
            return self.stream.reconfigure(*args, **kwargs)

def setup_logger(log_filename="server.log"):
    """
    配置全局日志和标准输出重定向。
    """
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    # 打开日志文件 (追加模式)
    log_file = open(log_path, 'a', encoding='utf-8')

    # Force Windows stdout to UTF-8
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
    # Check for ENV var or Config (Lazy load config to avoid circular import)
    use_json = os.environ.get("LUMINA_LOG_FORMAT", "text").lower() == "json"
    
    if use_json:
        formatter = JSONFormatter()
    else:
        # Use SafeFormatter to guarantee request_id/session_id exists
        formatter = SafeFormatter('%(asctime)s [%(levelname)s] [%(request_id)s] [%(session_id)s] %(name)s: %(message)s')
    
    root_logger = logging.getLogger()
    # Adjustable Level via ENV
    log_level = os.environ.get("LUMINA_LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # [FIX] Global factory is now set at module load level
    # No need to reset here unless we want to wrap again (not recommended)
    
    # handler.addFilter(RequestIdFilter()) # Not needed if factory is used
    
    root_logger.addHandler(handler)
    
    logger = logging.getLogger("LuminaCore")
    # logger.info(f"Logger initialized. Writing to {log_path}") # Avoid noise in JSON mode?
    if not use_json:
        logger.info(f"Logger initialized. Writing to {log_path}")

    # [Noise Reduction] Apply Filters and Level Overrides
    # 1. Reduce Chatty Libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    # 2. Filter Specific Paths from Access Log (even if level is INFO/WARNING)
    class LogFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            # Ignore Registry Heartbeats and Slot Checks
            if "/plugins/registry" in msg or "/plugins/slots" in msg:
                return False
            return True

    logging.getLogger("uvicorn.access").addFilter(LogFilter())

    return logger

class SafeFormatter(logging.Formatter):
    """
    Formatter that ensures request_id exists to prevent KeyError.
    """
    def format(self, record):
        _inject_context_to_record(record)
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for structured logging.
    """
    def format(self, record):
        import json
        
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "session_id": getattr(record, "session_id", "-")
        }
        
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)
