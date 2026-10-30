@echo off
cd /d "C:\Users\sandeep\.gemini\antigravity\scratch\personal-finance-analyzer"

curl -s -m 1 http://127.0.0.1:8000/api/sample >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start http://127.0.0.1:8000
    exit /b 0
)

start /b python -m uvicorn app:app --host 127.0.0.1 --port 8000
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000
