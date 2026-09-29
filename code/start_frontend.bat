@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo  AI-Driven Multi-Vendor Network Security Compliance Auditor
echo  Starting Frontend Web Interface - React 19 + Vite
echo ================================================================

cd /d "%~dp0frontend"

REM Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    if exist "C:\Program Files\nodejs\node.exe" (
        set "PATH=C:\Program Files\nodejs;!PATH!"
    ) else (
        echo [ERROR] Node.js was not found in PATH!
        echo Please install Node.js v18 or newer from https://nodejs.org
        pause
        exit /b 1
    )
)

REM Check if node_modules exists, install if missing
if not exist "node_modules\" (
    echo [INFO] First-time setup: installing node packages...
    call npm.cmd install
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] npm install failed!
        pause
        exit /b 1
    )
)

echo [INFO] Starting Vite development server on http://localhost:5173 ...
echo ================================================================

if exist "node_modules\.bin\vite.cmd" (
    call "node_modules\.bin\vite.cmd"
) else (
    call npm.cmd run dev
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Frontend server terminated with error code %ERRORLEVEL%.
    pause
)
