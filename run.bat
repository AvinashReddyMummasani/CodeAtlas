@echo off
title CodeAtlas — AI Code Explorer
echo.
echo   ==========================================
echo      CodeAtlas — AI Code Explorer
echo   ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install Python 3.9+
    pause
    exit /b 1
)

echo   Installing/verifying dependencies...
python -m pip install -r requirements.txt -q --disable-pip-version-check 2>nul
echo   Dependencies ready.
echo.
echo   Starting server at http://localhost:8000
echo   Press Ctrl+C to stop
echo.

REM Open browser after delay (background)
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM Start server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend
pause
