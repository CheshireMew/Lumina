
# Start-Lumina.ps1
# 启动所有 Lumina 服务 (TTS, STT, Memory, Frontend)
$OutputEncoding = [System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "🚀 Starting Lumina System..." -ForegroundColor Cyan

# 0. 启动 SurrealDB (Port 8000) - 持久化存储
Write-Host "🗄️ Starting SurrealDB..." -ForegroundColor Green
Start-Process -FilePath "surreal" -ArgumentList "start --log info --user root --pass root --bind 0.0.0.0:8000 --allow-all file:lumina_surreal.db" -WindowStyle Minimized
Start-Sleep -Seconds 5

# 1. 启动 TTS Server (Port 5050)
Write-Host "🎙️ Starting TTS Server..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "python_backend/tts_server.py" -WindowStyle Minimized
# 等待几秒确保端口占用
Start-Sleep -Seconds 2

# 2. 启动 STT Server (Port 8765)
Write-Host "👂 Starting STT Server..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "python_backend/stt_server.py" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 3. 启动 Memory Server (Port 8001)
Write-Host "🧠 Starting Memory Server...    " -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "python_backend/main.py" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 4. 启动 Frontend (Electron/React)
Write-Host "🖥️ Starting App..." -ForegroundColor Cyan
npm run dev
