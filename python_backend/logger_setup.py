import logging
import os
import sys
import re

# ANSI 颜色去除正则
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class TeeOutput:
    """
    双重输出流：同时写入 stdout/stderr 和 文件。
    写入文件时会自动去除 ANSI 颜色代码。
    """
    def __init__(self, stream, file_handle):
        self.stream = stream
        self.file_handle = file_handle

    def write(self, data):
        # 写入原始流 (通常是控制台，保留颜色)
        self.stream.write(data)
        self.stream.flush()
        
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

    # 重定向 stdout 和 stderr
    # 注意：这会捕获所有的 print() 输出
    sys.stdout = TeeOutput(sys.stdout, log_file)
    sys.stderr = TeeOutput(sys.stderr, log_file)

    # 配置 logging 模块
    #由于 stdout 已经被重定向，StreamHandler 会自动走 TeeOutput
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("LuminaCore")
    logger.info(f"Logger initialized. Writing to {log_path}")
    return logger
