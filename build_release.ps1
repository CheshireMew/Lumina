# build_release.ps1
# Automating the build process for Lumina Lite

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Lumina Lite Build Process..." -ForegroundColor Cyan

# --- 1. Environment Checks ---
Write-Host "Checking prerequisites..."

# Check SurrealDB
if (-not (Test-Path "python_backend/bin/surreal.exe")) {
    Write-Warning "surreal.exe not found in python_backend/bin/"
    # Try to find in PATH
    $sysSurreal = Get-Command surreal -ErrorAction SilentlyContinue
    if ($sysSurreal) {
        Write-Host "Found surreal globally at $($sysSurreal.Source). Copying..."
        Copy-Item $sysSurreal.Source "python_backend/bin/surreal.exe"
    }
    else {
        Write-Error "❌ Missing 'surreal.exe'. Please put it in 'python_backend/bin/'"
        exit 1
    }
}

# Check FFmpeg
if (-not (Test-Path "GPT-SoVITS/runtime/ffmpeg.exe")) {
    Write-Warning "ffmpeg.exe not found in GPT-SoVITS/runtime/"
    # Try to find in PATH
    $sysFFmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($sysFFmpeg) {
        # Create dir if needed
        New-Item -ItemType Directory -Force -Path "GPT-SoVITS/runtime" | Out-Null
        Write-Host "Found ffmpeg globally at $($sysFFmpeg.Source). Copying..."
        Copy-Item $sysFFmpeg.Source "GPT-SoVITS/runtime/ffmpeg.exe"
    }
    else {
        Write-Error "❌ Missing 'ffmpeg.exe'. Please put it in 'GPT-SoVITS/runtime/'"
        exit 1
    }
}

# --- 2. Clean Previous Builds ---
Write-Host "Cleaning previous builds..."
Remove-Item -Recurse -Force dist_backend -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build_backend -ErrorAction SilentlyContinue
# Remove-Item -Recurse -Force release -ErrorAction SilentlyContinue # Optional

# --- 3. Build Python Backend ---
Write-Host "📦 Building Python Backend (PyInstaller)..." -ForegroundColor Yellow
# Ensure hooks are visible
$env:PYTHONPATH = "python_backend" 
pyinstaller --distpath dist_backend --workpath build_backend --clean build_backend.spec

if (-not (Test-Path "dist_backend/lumina_backend/lumina_backend.exe")) {
    Write-Error "❌ Backend Build Failed! No exe found."
    exit 1
}
Write-Host "✅ Backend Compiled Successfully." -ForegroundColor Green

# --- 4. Build Electron App ---
Write-Host "📦 Building Electron Frontend & Installer..." -ForegroundColor Yellow
npm run build

Write-Host "🎉 Build Complete! Check 'release/' folder." -ForegroundColor Green
