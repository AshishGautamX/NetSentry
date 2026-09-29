#!/usr/bin/env bash
set -e

echo "================================================================"
echo " AI-Driven Multi-Vendor Network Security Compliance Auditor"
echo " Starting Backend API Server (FastAPI + Uvicorn)"
echo "================================================================"

# Move to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure python3 is available
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 command not found! Please install Python 3.10+."
    exit 1
fi

# Set PYTHONPATH to repo root
export PYTHONPATH="."

# Check dependencies
if ! python3 -c "import fastapi, uvicorn, sqlalchemy, reportlab" &>/dev/null; then
    echo "[INFO] Installing backend dependencies from backend/requirements.txt..."
    python3 -m pip install -r backend/requirements.txt
fi

echo "[INFO] Starting FastAPI application on http://127.0.0.1:8000 ..."
echo "[INFO] Interactive Swagger Documentation: http://127.0.0.1:8000/docs"
echo "================================================================"
exec python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
