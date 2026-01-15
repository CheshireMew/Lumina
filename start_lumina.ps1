
# Start-Lumina.ps1
# 启动所有 Lumina 服务 (TTS, STT, Memory, Frontend)
$OutputEncoding = [System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "🚀 Starting Lumina System..." -ForegroundColor Cyan

# Load Config
$ConfigPath = Join-Path $PSScriptRoot "config\ports.json"
if (Test-Path $ConfigPath) {
    $ports = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    Write-Host "✅ Loaded configuration from ports.json" -ForegroundColor Green
}
else {
    Write-Warning "⚠️ config/ports.json not found, using defaults."
    $ports = @{
        memory_port  = 8010
        stt_port     = 8765
        tts_port     = 8766
        surreal_port = 8001
        host         = "127.0.0.1"
    }
}

# 0. 清理旧进程 (防止端口冲突)
Write-Host "🧹 Cleaning up old processes..." -ForegroundColor Yellow
Stop-Process -Name "surreal" -ErrorAction SilentlyContinue
Stop-Process -Name "uvicorn" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1


# 0. 启动 SurrealDB
Write-Host "🗄️ Starting SurrealDB (Port $($ports.surreal_port))..." -ForegroundColor Green
Start-Process -FilePath "surreal" -ArgumentList "start --log info --user root --pass root --bind 0.0.0.0:$($ports.surreal_port) --allow-all file:lumina_surreal.db" -WindowStyle Minimized
Start-Sleep -Seconds 5

# 1. 启动 TTS Server
Write-Host "🎙️ Starting TTS Server (Port $($ports.tts_port))..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "python_backend/tts_server.py" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 2. 启动 STT Server
Write-Host "👂 Starting STT Server (Port $($ports.stt_port))..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "python_backend/stt_server.py" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 3. 启动 Memory Server
Write-Host "🧠 Starting Memory Server (Port $($ports.memory_port))..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "python_backend/main.py" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 4. 启动 Frontend (Electron/React)
Write-Host "🖥️ Starting App..." -ForegroundColor Cyan
npm run dev
