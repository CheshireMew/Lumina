param(
    [switch]$Dev
)

$OutputEncoding = [System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Test-BuiltFilesFresh {
    param(
        [string]$DistIndex,
        [string]$MainBundle
    )

    if (-not ((Test-Path $DistIndex) -and (Test-Path $MainBundle))) {
        return $false
    }

    $sourceFiles = @()
    foreach ($root in @("app", "core")) {
        $sourceRoot = Join-Path $PSScriptRoot $root
        if (Test-Path $sourceRoot) {
            $sourceFiles += Get-ChildItem -Path $sourceRoot -Recurse -File -Include *.ts,*.tsx,*.mts
        }
    }
    foreach ($file in @("vite.config.mts", "package.json")) {
        $sourceFile = Join-Path $PSScriptRoot $file
        if (Test-Path $sourceFile) {
            $sourceFiles += Get-Item $sourceFile
        }
    }

    if (-not $sourceFiles) {
        return $true
    }

    $latestSource = ($sourceFiles | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1).LastWriteTimeUtc
    $oldestBuild = (@(Get-Item $DistIndex, $MainBundle) | Sort-Object LastWriteTimeUtc | Select-Object -First 1).LastWriteTimeUtc

    return $oldestBuild -ge $latestSource
}

Set-Location $PSScriptRoot
$env:LUMINA_DATA_PATH = Join-Path $PSScriptRoot "Lumina_Data"

Write-Host "正在启动 Lumina…" -ForegroundColor Cyan

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "未找到 npm。请先安装 Node.js 20 或更高版本。"
}

if (-not (Test-Path (Join-Path $PSScriptRoot "node_modules"))) {
    throw "前端依赖尚未安装。请先在项目目录运行 npm install。"
}

function Start-LuminaDesktop {
    if ($Dev) {
        Write-Host "正在启动 Electron 与 Vite 开发环境…" -ForegroundColor Cyan
        npm run dev
        return
    }

    $distIndex = Join-Path $PSScriptRoot "dist\index.html"
    $mainBundle = Join-Path $PSScriptRoot "dist-electron\main.js"
    $electronCmd = Join-Path $PSScriptRoot "node_modules\.bin\electron.cmd"

    if ((Test-BuiltFilesFresh -DistIndex $distIndex -MainBundle $mainBundle) -and (Test-Path $electronCmd)) {
        Write-Host "正在使用现有构建文件启动 Electron…" -ForegroundColor Cyan
        & $electronCmd .
        return
    }

    Write-Host "构建文件不存在或早于源码，改用开发模式启动。" -ForegroundColor Yellow
    npm run dev
}

Start-LuminaDesktop
