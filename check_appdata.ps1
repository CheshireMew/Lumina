# Check AppData Database Content
# Steps:
# 1. Stop existing Surreal instance.
# 2. Start temporary instance pointing to AppData.
# 3. Run inspect_db.py.
# 4. Stop temporary instance.
# 5. Restart original instance (Optional, or leave for user).

Write-Host "🛑 Stopping existing SurrealDB..." -ForegroundColor Cyan
Stop-Process -Name "surreal" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$AppDataDB = "$env:APPDATA\Lumina\lumina.db"
Write-Host "🚀 Starting Check on: $AppDataDB" -ForegroundColor Cyan

# Start Surreal in background
$proc = Start-Process -FilePath "surreal" -ArgumentList "start --log info --user root --pass root --bind 0.0.0.0:8001 --allow-all file:$AppDataDB" -PassThru -NoNewWindow
Start-Sleep -Seconds 5

Write-Host "🔍 Inspecting Record Count..." -ForegroundColor Cyan
python debug_count.py

Write-Host "🛑 Stopping Temporary Instance..." -ForegroundColor Cyan
Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue

Write-Host "Done."
