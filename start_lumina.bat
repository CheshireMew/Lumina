@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1_FILE=%SCRIPT_DIR%start_lumina.ps1"

if not exist "%PS1_FILE%" (
    echo [Lumina] Missing startup script: "%PS1_FILE%"
    pause
    exit /b 1
)

where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "POWERSHELL_EXE=pwsh"
) else (
    set "POWERSHELL_EXE=powershell"
)

pushd "%SCRIPT_DIR%" >nul
"%POWERSHELL_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [Lumina] Startup failed with exit code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
