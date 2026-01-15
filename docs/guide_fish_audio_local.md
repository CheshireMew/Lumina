# Fish Audio (Fish Speech) 本地部署指南

Fish Speech 是一个强大的开源 TTS/SVC 模型,支持本地部署。以下是基于 Docker 的最简部署方案。

## 前置要求

- **NVIDIA 显卡**: 显存建议 8GB 以上 (4GB 可能仅能运行量化版)。
- **Docker**: 请确保已安装 Docker Desktop。
- **CUDA**: 建议安装 CUDA 11.8 或 12.x 驱动。

## 部署步骤

### 1. 拉取代码

在您的工作目录(非 Lumina 项目内,建议在一个新的文件夹)执行:

```powershell
git clone https://github.com/fishaudio/fish-speech.git
cd fish-speech
```

### 2. 启动 API 服务 (Docker Compose)

Fish Speech 官方尚未提供一键 Compose,但您可以使用以下命令启动 API 服务器(兼容 OpenAI 格式):

- **下载模型**:

  ```powershell
  huggingface-cli download fishaudio/fish-speech-1.5 --local-dir checkpoints/fish-speech-1.5
  ```

  _(如果没有 huggingface-cli,请先 pip install huggingface_hub)_

- **运行容器**:
  ```powershell
  docker run -it --gpus all -p 8080:8080 -v ${PWD}/checkpoints:/app/checkpoints fishaudio/fish-speech:latest \
  python -m tools.api_server \
  --listen 0.0.0.0:8080 \
  --llama-checkpoint-path checkpoints/fish-speech-1.5 \
  --decoder-checkpoint-path checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-10.2s.pth
  ```
  _注意:具体 checkpoint 路径可能会随版本更新,请参考官方 GitHub 的最新文档。_

### 3. 连接 Lumina

如果你不想使用 Docker,也可以直接用 Conda 环境运行:

```powershell
conda create -n fish-speech python=3.10
conda activate fish-speech
pip install -e .
python -m tools.api_server --listen 0.0.0.0:8080 ...
```

### 3. 连接 Lumina (无需 Docker/Conda 方案)

如果您不想使用 Docker 或 Conda,也可以使用标准的 Python 虚拟环境 (`venv`):

1.  **创建虚拟环境**:

    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  **安装 PyTorch (必须带 CUDA)**:

    - _重要_: 请访问 [PyTorch 官网](https://pytorch.org/get-started/locally/) 获取最新的安装命令。
    - 例如 (CUDA 12.1):

    ```powershell
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```

3.  **安装 Fish Speech**:

    ```powershell
    pip install -e .
    ```

    _注意:如果 Windows 下安装 `flash-attn` 报错,可以尝试跳过它(不影响运行,只是推理速度稍慢)。_

4.  **启动 API**:
    ```powershell
    python -m tools.api_server --listen 0.0.0.0:8080 ...
    ```

### 4. 配置 Lumina

一旦服务在 `http://127.0.0.1:8080` 启动成功(看到 Swagger UI 即可):

1. 打开 Lumina **Plugin Store**。
2. 找到 **Fish Audio** 插件(或进入 `app_config.py`)。
3. 修改配置:
   - `API URL`: `http://127.0.0.1:8080/v1`
   - `API Key`: (本地通过通常留空或任意填写即可)

## 常见问题

- **显存不足**: 尝试搜索 "fish speech int8" 或 "quantized" 模型。
- **端口冲突**: 如果 8080 被占用,请修改 docker 命令中的 `-p 8081:8080`,并在 Lumina 中对应修改端口。
