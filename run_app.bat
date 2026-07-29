@echo off
title EL Solar Panel Cell Cropper
echo ==========================================================
echo  Starting EL Solar Panel Cell Cropper Application...
echo  Open browser at: http://localhost:8000
echo ==========================================================
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
