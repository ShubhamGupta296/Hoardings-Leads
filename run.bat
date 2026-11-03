@echo off
title Smart Leads Agent - Hoardings
cd /d "%~dp0"

echo ===================================================
echo   Starting Smart Leads Agent for Hoardings...
echo ===================================================

set PYTHONPATH=backend

:: 1. Launch FastAPI backend in a new window
start "Hoardings API Server" cmd /k "title Hoardings API Server && cd /d %~dp0 && python -m uvicorn app.main:app --reload --app-dir backend --port 8000"

:: 2. Wait 2 seconds for server to initialize
timeout /t 2 /nobreak >nul

:: 3. Open the visual frontend dashboard
start "" "%~dp0frontend\index.html"

:: 4. Open Swagger Interactive Docs
start "" "http://127.0.0.1:8000/docs"

echo.
echo [OK] Backend server started at http://127.0.0.1:8000
echo [OK] Interactive Swagger Docs: http://127.0.0.1:8000/docs
echo [OK] Visual Dashboard opened: frontend\index.html
echo.
pause
