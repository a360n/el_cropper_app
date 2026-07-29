#!/bin/bash
# EL Solar Panel Cell Cropper Launcher Script
# Starts local FastAPI backend server on macOS

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo " Starting EL Solar Panel Cell Cropper Application..."
echo " Open browser at: http://localhost:8000"
echo "=========================================================="

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
