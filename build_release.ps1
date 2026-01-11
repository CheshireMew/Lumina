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
# Security: Redact API Key in-place to GUARANTEE safety
$ConfigPath = "python_backend/memory_config.json"
$OriginalContent = ""
$Redacted = $false

if (Test-Path $ConfigPath) {
    Write-Host "🔒 Securing API Key: In-place redaction..." -ForegroundColor Yellow
    try {
        # 1. Redact Memory Config
        $OriginalContent = Get-Content $ConfigPath -Raw -Encoding UTF8
        $Json = $OriginalContent | ConvertFrom-Json
        
        # Redact valid keys
        if ($Json.PSObject.Properties.Match("api_key")) {
            $Json.api_key = ""
        }
        
        $Json | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8
        $Redacted = $true
    }
    catch {
        Write-Warning "Failed to parse config for redaction. Proceeding with caution."
    }
}

# 2. Redact LLM Registry (NEW Security Check)
$LLMConfigPath = "python_backend/llm_registry.json"
$OriginalLLMContent = ""
$LLMRedacted = $false

if (Test-Path $LLMConfigPath) {
    Write-Host "🔒 Securing LLM Registry: Redacting Keys..." -ForegroundColor Yellow
    try {
        $OriginalLLMContent = Get-Content $LLMConfigPath -Raw -Encoding UTF8
        $LLMJson = $OriginalLLMContent | ConvertFrom-Json
        
        # Iterate providers and clear keys
        if ($LLMJson.providers) {
            foreach ($key in $LLMJson.providers.PSObject.Properties.Name) {
                $LLMJson.providers.$key.api_key = ""
            }
        }
        
        $LLMJson | ConvertTo-Json -Depth 10 | Set-Content $LLMConfigPath -Encoding UTF8
        $LLMRedacted = $true
    }
    catch {
        Write-Warning "Failed to parse llm_registry for redaction: $_"
    }
}

try {
    # Ensure hooks are visible
    $env:PYTHONPATH = "python_backend" 
    pyinstaller --distpath dist_backend --workpath build_backend --clean build_backend.spec
}
finally {
    if ($Redacted) {
        Write-Host "🔓 Restoring original memory config..." -ForegroundColor Gray
        Set-Content $ConfigPath $OriginalContent -Encoding UTF8
    }
    if ($LLMRedacted) {
        Write-Host "🔓 Restoring original LLM registry..." -ForegroundColor Gray
        Set-Content $LLMConfigPath $OriginalLLMContent -Encoding UTF8
    }
}

if (-not (Test-Path "dist_backend/lumina_backend/lumina_backend.exe")) {
    Write-Error "❌ Backend Build Failed! No exe found."
    exit 1
}

# ⚡ Portable Mode: Create Data Directory by default
$PortableDataDir = "dist_backend/lumina_backend/Lumina_Data"
if (-not (Test-Path $PortableDataDir)) {
    Write-Host "📂 Creating Portable Data Directory: $PortableDataDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $PortableDataDir | Out-Null
    # Add a README to explain
    Set-Content -Path "$PortableDataDir/README.txt" -Value "Data stored here will make Lumina run in Portable Mode (Green Version).`nDelete this folder to use System AppData (%APPDATA%/Lumina) instead."
}

Write-Host "✅ Backend Compiled Successfully." -ForegroundColor Green

# --- 4. Build Electron App ---
Write-Host "📦 Building Electron Frontend & Installer..." -ForegroundColor Yellow
npm run build

Write-Host "🎉 Build Complete! Check 'release/' folder." -ForegroundColor Green
