@echo off
title Spousteni serveru Jidelna PWA
echo ===========================================
echo   Spoustim backend server Jidelna PWA...
echo ===========================================
cd /d "%~dp0backend"
python -m pip install -r requirements.txt
powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue" >nul 2>&1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause

