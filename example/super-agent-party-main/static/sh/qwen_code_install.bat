@echo off
:: -------------- 强制 UTF-8 编码 --------------
chcp 65001 >nul
setlocal enabledelayedexpansion

:: -------------- 颜色宏 --------------
set "RED=91"
set "GREEN=92"
set "YELLOW=93"
set "RESET=0"

:: 彩色输出函数
:echo_color
:: %1 颜色码  %2 文本
powershell -nop -c "write-host \"%~2\" -fore %{%~1%}"
exit /b

:: -------------- Node 安装函数 --------------
:install_nodejs
call :echo_color %YELLOW% "📥 正在下载并安装 Node.js 22（LTS）x64 …"
:: 临时目录
set "NODE_MSI=%TEMP%\node-v22.msi"
:: 官方 MSI 直链（可换国内镜像）
set "MSI_URL=https://nodejs.org/dist/latest-v22.x/node-v22.11.0-x64.msi"
powershell -nop -c "Invoke-WebRequest -Uri '%MSI_URL%' -OutFile '%NODE_MSI%'"
if not exist "%NODE_MSI%" (
    call :echo_color %RED% "❌ 下载 Node.js 安装包失败"
    pause & exit /b 1
)
:: 静默安装 /quiet 不弹界面
msiexec /i "%NODE_MSI%" /quiet /norestart
if errorlevel 1 (
    call :echo_color %RED% "❌ Node.js 安装失败，请手动安装"
    pause & exit /b 1
)
del "%NODE_MSI%" 2>nul
call :echo_color %GREEN% "✅ Node.js 22 安装完成"
exit /b

:: -------------- 主流程 --------------
call :echo_color %YELLOW% "检查 Node.js 环境 …"

where node >nul 2>nul
if %errorlevel% neq 0 (
    call :echo_color %YELLOW% "Node.js 未检测到，即将自动安装 …"
    goto :do_install
)

:: 已安装，检查版本
for /f "tokens=1 delims=v" %%v in ('node -v') do set "VER=%%v"
for /f "tokens=1 delims=." %%m in ("!VER!") do set "MAJOR=%%m"
if !MAJOR! GEQ 18 (
    call :echo_color %GREEN% "✅ Node.js 已满足要求：v!VER!"
    goto :check_qwen
) else (
    call :echo_color %YELLOW% "Node.js 版本过低（v!VER!），将升级至 22 …"
    goto :do_install
)

:do_install
call :install_nodejs
:: 刷新当前会话 PATH
call :echo_color %YELLOW% "刷新环境变量 …"
set "PATH=%ProgramFiles%\nodejs;%PATH%"

:check_qwen
call :echo_color %YELLOW% "检查 Qwen Code …"
where qwen >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('qwen --version 2^>nul') do set "QV=%%v"
    call :echo_color %GREEN% "✅ Qwen Code 已安装：!QV!"
    goto :finish
)

call :echo_color %YELLOW% "📦 正在全局安装 Qwen Code …"
call npm install -g @qwen-code/qwen-code
if %errorlevel% neq 0 (
    call :echo_color %RED% "❌ 安装 Qwen Code 失败"
    pause & exit /b 1
)

:finish
call :echo_color %GREEN% "🎉 安装完成！"
call :echo_color %RESET% "使用命令：  qwen   即可启动 Qwen Code"
pause