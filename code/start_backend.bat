@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo  AI-Driven Multi-Vendor Network Security Compliance Auditor
echo  Starting Backend API Server (FastAPI + Uvicorn)
echo ================================================================

cd /d "%~dp0"

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

REM Set PYTHONPATH to repository root
set PYTHONPATH=.

REM Check if dependencies are installed, install if needed
echo [INFO] Checking Python backend dependencies...
python -c "import fastapi, uvicorn, sqlalchemy, reportlab" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing required backend packages from backend/requirements.txt...
    python -m pip install -r backend/requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install backend dependencies!
        pause
        exit /b 1
    )
)

echo [INFO] Starting FastAPI application on http://127.0.0.1:8000 ...
echo [INFO] Interactive Swagger Documentation: http://127.0.0.1:8000/docs
echo ================================================================
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
