param(
    [switch]$Dev
)

$OutputEncoding = [System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Test-TcpPort {
    param(
        [string]$Address,
        [int]$Port
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $task = $client.ConnectAsync($Address, $Port)
        $connected = $task.Wait(500)
        if ($connected -and $client.Connected) {
            $client.Dispose()
            return $true
        }
        $client.Dispose()
    }
    catch {
    }

    return $false
}

function Wait-TcpPort {
    param(
        [string]$Address,
        [int]$Port,
        [int]$TimeoutSeconds,
        [string]$Name
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -Address $Address -Port $Port) {
            Write-Host "✅ $Name is ready on $Address`:$Port" -ForegroundColor Green
            return
        }
        Start-Sleep -Milliseconds 250
    }

    throw "$Name did not become ready on $Address`:$Port within $TimeoutSeconds seconds."
}

function Get-LuminaRuntimeConfig {
    $rootPath = $PSScriptRoot.Replace('\', '\\')
    $script = @"
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

root = Path(r"$rootPath")
config = {
    "pg_host": "127.0.0.1",
    "pg_port": 5432,
    "pg_user": "lumina_user",
    "pg_password": "lumina_password",
    "pg_database": "lumina_db",
}

config_path = root / "Lumina_Data" / "config.yaml"
if yaml and config_path.exists():
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    pg = ((data.get("memory") or {}).get("postgres") or {})
    config["pg_host"] = pg.get("host", config["pg_host"])
    config["pg_port"] = int(pg.get("port", config["pg_port"]))
    config["pg_user"] = pg.get("user", config["pg_user"])
    config["pg_password"] = pg.get("password", config["pg_password"])
    config["pg_database"] = pg.get("database", config["pg_database"])

print(json.dumps(config))
"@

    return ($script | python - | ConvertFrom-Json)
}

Set-Location $PSScriptRoot
$env:LUMINA_DATA_PATH = Join-Path $PSScriptRoot "Lumina_Data"

Write-Host "🚀 Starting Lumina..." -ForegroundColor Cyan

$runtime = Get-LuminaRuntimeConfig
$env:LUMINA_PG_PORT = "$($runtime.pg_port)"
$env:LUMINA_PG_USER = "$($runtime.pg_user)"
$env:LUMINA_PG_PASSWORD = "$($runtime.pg_password)"
$env:LUMINA_PG_DATABASE = "$($runtime.pg_database)"

if (-not (Test-TcpPort -Address $runtime.pg_host -Port $runtime.pg_port)) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "PostgreSQL is not running on $($runtime.pg_host):$($runtime.pg_port), and docker is not available to start it automatically."
    }
    Write-Host "🗄️ Starting PostgreSQL container..." -ForegroundColor Green
    docker compose up -d db | Out-Host
    Wait-TcpPort -Address $runtime.pg_host -Port $runtime.pg_port -TimeoutSeconds 60 -Name "PostgreSQL"
}
else {
    Write-Host "✅ PostgreSQL already running on $($runtime.pg_host):$($runtime.pg_port)" -ForegroundColor Green
}

function Start-LuminaDesktop {
    if ($Dev) {
        Write-Host "🖥️ Starting Electron + Vite (dev mode)..." -ForegroundColor Cyan
        npm run dev
        return
    }

    $distIndex = Join-Path $PSScriptRoot "dist\index.html"
    $mainBundle = Join-Path $PSScriptRoot "dist-electron\main.js"
    $electronCmd = Join-Path $PSScriptRoot "node_modules\.bin\electron.cmd"

    if ((Test-Path $distIndex) -and (Test-Path $mainBundle) -and (Test-Path $electronCmd)) {
        Write-Host "🖥️ Starting Electron from built files..." -ForegroundColor Cyan
        & $electronCmd .
        return
    }

    Write-Host "⚠️ Built files not found. Falling back to dev mode." -ForegroundColor Yellow
    Write-Host "   Run npm run build once to enable faster normal startup." -ForegroundColor Yellow
    npm run dev
}

Start-LuminaDesktop
