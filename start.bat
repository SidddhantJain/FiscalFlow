@echo off
echo ==========================================
echo FiscalFlow Startup Utility
echo ==========================================

echo [1/3] Stopping any existing process on port 8000...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

echo [2/3] Launching FiscalFlow browser tab...
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8000

echo [3/3] Starting FiscalFlow backend and frontend server...
cd /d "%~dp0backend"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause

