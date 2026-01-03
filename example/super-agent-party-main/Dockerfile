FROM python:3.12-slim

# 1. 安装系统依赖
RUN apt-get update && \
    apt-get install -y gcc curl git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. 先只复制依赖文件 (利用缓存)
COPY pyproject.toml uv.lock ./

# 3. 安装 Python 依赖
RUN pip install uv && \
    uv venv && \
    uv sync

# 5. 最后再复制源代码 (这样改代码不会触发重新安装依赖)
COPY . .

# 6. 设置权限和目录
RUN mkdir -p uploaded_files && \
    chmod 755 uploaded_files

EXPOSE 3456
ENV HOST=0.0.0.0 PORT=3456 PYTHONUNBUFFERED=1

CMD [".venv/bin/python", "server.py", "--host", "0.0.0.0", "--port", "3456"]