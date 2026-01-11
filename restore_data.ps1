# Restore Data from Packaged App
# This script copies the database from AppData (Packaged App) to the local dev folder.

$Source = "$env:APPDATA\Lumina\lumina.db"
$Dest = "$PSScriptRoot\lumina_surreal.db"

Write-Host "⚠️  This will OVERWRITE your local development database with data from the Packaged App." -ForegroundColor Yellow
Write-Host "Source: $Source"
Write-Host "Dest:   $Dest"
Write-Host ""

# 1. Check if Source exists
if (-not (Test-Path $Source)) {
    Write-Error "Source database not found at $Source"
    exit
}

# 2. Stop SurrealDB if running
Write-Host "🛑 Stopping any running SurrealDB processes..." -ForegroundColor Cyan
try {
    Stop-Process -Name "surreal" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
catch {
    Write-Host "No running surreal process found."
}

# 3. Copy Data
Write-Host "📦 Copying database files..." -ForegroundColor Cyan
if (Test-Path $Dest) {
    Remove-Item -Path $Dest -Recurse -Force
}
Copy-Item -Path $Source -Destination $Dest -Recurse -Force

Write-Host "✅ Data Restored Successfully!" -ForegroundColor Green
Write-Host "You can now run 'surreal start ...' to see your old history."
