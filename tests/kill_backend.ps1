
Write-Host "🔪 Killing all Python and Node processes..." -ForegroundColor Yellow
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
Write-Host "✅ All processes terminated. You can now restart cleanly." -ForegroundColor Green
exit 0
