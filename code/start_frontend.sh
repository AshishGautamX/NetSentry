#!/usr/bin/env bash
set -e

echo "================================================================"
echo " AI-Driven Multi-Vendor Network Security Compliance Auditor"
echo " Starting Frontend Web Interface (React 19 + Vite)"
echo "================================================================"

# Move to script frontend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/frontend"

# Ensure npm is available
if ! command -v npm &>/dev/null; then
    echo "[ERROR] npm command not found! Please install Node.js (v18+)."
    exit 1
fi

# Check node_modules
if [ ! -d "node_modules" ]; then
    echo "[INFO] First-time setup: installing node packages..."
    npm install
fi

echo "[INFO] Starting Vite development server on http://localhost:5173 ..."
echo "================================================================"
exec npm run dev
