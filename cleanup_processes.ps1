
Write-Host "🧹 Starting Lumina Process Cleanup..." -ForegroundColor Cyan

# 1. Kill Python Processes (Backend)
$python = Get-Process python -ErrorAction SilentlyContinue
if ($python) {
    Write-Host "Found $($python.Count) Python processes. Terminating..." -ForegroundColor Yellow
    Stop-Process -Name python -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "No stray Python processes found." -ForegroundColor Green
}

# 2. Kill Node Processes (Frontend / Electron)
$node = Get-Process node -ErrorAction SilentlyContinue
if ($node) {
    Write-Host "Found $($node.Count) Node processes. Terminating..." -ForegroundColor Yellow
    Stop-Process -Name node -Force -ErrorAction SilentlyContinue
}

# 3. Kill SurrealDB (Database)
$surreal = Get-Process surreal -ErrorAction SilentlyContinue
if ($surreal) {
    Write-Host "Found SurrealDB. Terminating..." -ForegroundColor Yellow
    Stop-Process -Name surreal -Force -ErrorAction SilentlyContinue
}

Write-Host "✅ Cleanup Complete! You can now restart the system cleanly." -ForegroundColor Green
