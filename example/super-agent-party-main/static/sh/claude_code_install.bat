@echo off
chcp 65001 >nul
title Claude Code 安装工具

echo ===== Claude Code 安装工具 =====
echo.

echo [INFO] 检查 Node.js 安装情况...
node --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=1 delims=v" %%i in ('node --version 2^>nul') do set "current_version=%%i"
    echo [SUCCESS] Node.js 已安装: v!current_version!
) else (
    echo [WARNING] Node.js 未安装，开始安装...
    call :install_nodejs
)

echo.
echo [INFO] 检查 Claude Code 安装情况...
where claude >nul 2>&1
if %errorlevel% == 0 (
    echo [SUCCESS] Claude Code 已安装
) else (
    echo [WARNING] Claude Code 未安装，开始安装...
    call :install_claude
)

echo.
echo [INFO] 配置 Claude Code 跳过 onboarding...
node -e "const fs=require('fs'),os=require('os'),path=require('path'),homeDir=os.homedir(),filePath=path.join(homeDir,'.claude.json');try{let config={};if(fs.existsSync(filePath))config=JSON.parse(fs.readFileSync(filePath,'utf8'));config.hasCompletedOnboarding=true;fs.writeFileSync(filePath,JSON.stringify(config,null,2),'utf8');console.log('Onboarding configuration updated successfully');}catch(e){console.log('Onboarding configuration completed');}" >nul 2>&1

echo.
echo [INFO] 配置环境变量...
call :configure_env

echo.
echo [SUCCESS] 配置已完成！
echo.
echo [INFO] 请重启终端或运行以下命令使配置生效：
echo    refreshenv 或 重新启动命令行
echo.
echo [INFO] 然后可以使用以下命令启动 Claude Code：
echo    claude
pause
exit /b 0

:install_nodejs
echo.
echo [INFO] 正在安装 Node.js...
where nvm >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 安装 nvm-windows...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/coreybutler/nvm-windows/releases/download/1.1.12/nvm-setup.exe' -OutFile '%TEMP%\nvm-setup.exe'" >nul 2>&1
    if exist "%TEMP%\nvm-setup.exe" (
        start /wait "" "%TEMP%\nvm-setup.exe" /S
        del "%TEMP%\nvm-setup.exe" >nul 2>&1
    ) else (
        echo [ERROR] 下载 nvm 失败
        echo [INFO] 请手动安装 Node.js: https://nodejs.org/
        pause
        exit /b 1
    )
)

echo [INFO] 安装 Node.js...
nvm install latest >nul 2>&1
nvm use latest >nul 2>&1

node --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=1 delims=v" %%i in ('node --version 2^>nul') do set "new_version=%%i"
    echo [SUCCESS] Node.js 安装完成: v!new_version!
) else (
    echo [ERROR] Node.js 安装失败
    echo [INFO] 请手动安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)
exit /b 0

:install_claude
echo [INFO] 安装 Claude Code...
npm install -g @anthropic-ai/claude-code >nul 2>&1

where claude >nul 2>&1
if %errorlevel% == 0 (
    echo [SUCCESS] Claude Code 安装完成
) else (
    echo [WARNING] Claude Code 可能安装成功但命令未找到，请手动验证
    echo [INFO] 尝试手动运行: npx @anthropic-ai/claude-code
)
exit /b 0

:configure_env
setlocal enabledelayedexpansion

set "existing_config=0"
set "current_url="
set "current_key="
set "current_model="

reg query "HKCU\Environment" /v ANTHROPIC_BASE_URL >nul 2>&1
if %errorlevel% == 0 (
    for /f "skip=2 tokens=2,*" %%a in ('reg query "HKCU\Environment" /v ANTHROPIC_BASE_URL 2^>nul') do set "current_url=%%b"
    set "existing_config=1"
)

reg query "HKCU\Environment" /v ANTHROPIC_API_KEY >nul 2>&1
if %errorlevel% == 0 (
    for /f "skip=2 tokens=2,*" %%a in ('reg query "HKCU\Environment" /v ANTHROPIC_API_KEY 2^>nul') do set "current_key=%%b"
    set "existing_config=1"
)

reg query "HKCU\Environment" /v ANTHROPIC_MODEL >nul 2>&1
if %errorlevel% == 0 (
    for /f "skip=2 tokens=2,*" %%a in ('reg query "HKCU\Environment" /v ANTHROPIC_MODEL 2^>nul') do set "current_model=%%b"
    set "existing_config=1"
)

if !existing_config! equ 1 (
    echo [WARNING] 检测到已有配置：
    if defined current_url echo   - API URL: !current_url!
    if defined current_key echo   - API Key: !current_key:~0,4!****!current_key:~-4!
    if defined current_model echo   - Model: !current_model!
    
    set /p "modify_config=是否要修改配置? (Y/N): "
    if /i "!modify_config!" neq "Y" (
        echo [INFO] 保留当前配置
        endlocal
        exit /b 0
    )
    
    echo.
    echo [INFO] 请选择要修改的配置项：
    echo 1. API URL
    echo 2. API Key
    echo 3. Model
    echo 4. 全部修改
    set /p "choice=输入你的选择 (1-4): "
    
    if "!choice!"=="1" (
        set "api_url=!current_url!"
        set "api_key=!current_key!"
        set "model=!current_model!"
        set /p "api_url=输入新的 API URL (当前: !current_url!): "
    ) else if "!choice!"=="2" (
        set "api_url=!current_url!"
        set "api_key=!current_key!"
        set "model=!current_model!"
        set /p "api_key=输入新的 API Key: "
    ) else if "!choice!"=="3" (
        set "api_url=!current_url!"
        set "api_key=!current_key!"
        set "model=!current_model!"
        set /p "model=输入新的模型名称 (当前: !current_model!): "
    ) else if "!choice!"=="4" (
        set "api_url=!current_url!"
        set "api_key=!current_key!"
        set "model=!current_model!"
        set /p "api_url=输入新的 API URL (当前: !current_url!): "
        set /p "api_key=输入新的 API Key: "
        set /p "model=输入新的模型名称 (当前: !current_model!): "
    ) else (
        echo [ERROR] 无效的选择
        endlocal
        exit /b 1
    )
) else (
    echo.
    echo [INFO] 请配置 Claude Code 参数
    
    set /p "api_url=输入 API URL (例如 https://api.deepseek.com/anthropic/): "
    if "!api_url!"=="" (
        echo [ERROR] API URL 不能为空
        endlocal
        exit /b 1
    )
    
    set /p "api_key=输入 API Key: "
    if "!api_key!"=="" (
        echo [ERROR] API Key 不能为空
        endlocal
        exit /b 1
    )
    
    set /p "model=输入模型名称 (例如 deepseek-chat): "
    if "!model!"=="" (
        echo [ERROR] 模型名称不能为空
        endlocal
        exit /b 1
    )
)

echo.
echo [INFO] 正在更新环境变量...

reg add "HKCU\Environment" /v ANTHROPIC_BASE_URL /t REG_SZ /d "!api_url!" /f >nul
reg add "HKCU\Environment" /v ANTHROPIC_API_KEY /t REG_SZ /d "!api_key!" /f >nul
reg add "HKCU\Environment" /v ANTHROPIC_MODEL /t REG_SZ /d "!model!" /f >nul

echo [SUCCESS] 环境变量已更新

endlocal
exit /b 0