
Write-Host "🚀 Starting Lumina MVP Backend..."

$ROOT = ".."
$PYTHON = "python" # Or specific venv python
$PORTS = Get-Content "$ROOT\config\ports.json" | ConvertFrom-Json

# Launch Services
$BACKEND_DIR = "$ROOT\python_backend"
$env:PYTHONPATH = $BACKEND_DIR

# Function to launch async
function Launch-Service ($name) {
    Write-Host "启动 $name Service..."
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "& { $env:PYTHONPATH='$BACKEND_DIR'; $PYTHON $BACKEND_DIR/backend_launcher.py $name }"
}

Launch-Service "memory"
Start-Sleep -Seconds 2
Launch-Service "stt"
Start-Sleep -Seconds 1
Launch-Service "tts"

Write-Host "✅ All Services Launched. Check valid ports:"
Write-Host "  - Memory: $($PORTS.memory_port)"
Write-Host "  - STT:    $($PORTS.stt_port)"
Write-Host "  - TTS:    $($PORTS.tts_port)"
Write-Host "  - Vision: $($PORTS.vision_port)"
