@echo off
title EventPay - Full Stack Launcher
echo ============================================
echo   EventPay - Starting All Services
echo ============================================
echo.

set BACKEND_DIR=%~dp0backend
set FRONTEND_DIR=%~dp0frontend

:: Start MongoDB
echo [1/5] Starting MongoDB...
start "EventPay-MongoDB" cmd /c "mongod"
echo       MongoDB starting on localhost:27017

:: Start n8n (npm global)
echo [2/5] Starting n8n...
start "EventPay-n8n" cmd /c "set N8N_BASIC_AUTH_ACTIVE=true&& set N8N_BASIC_AUTH_USER=admin&& set N8N_BASIC_AUTH_PASSWORD=changeme&& n8n start"

:: Start Backend
echo [3/5] Starting Backend...
start "EventPay-Backend" cmd /c "cd /d %BACKEND_DIR% && pip install -r requirements.txt -q && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to initialize
timeout /t 4 /nobreak >nul

:: Start Frontend
echo [4/5] Starting Frontend...
start "EventPay-Frontend" cmd /c "cd /d %FRONTEND_DIR% && npm install && npm start"

:: Start ngrok
echo [5/5] Starting ngrok...
where ngrok >nul 2>&1 && (
    start "EventPay-ngrok" cmd /c "ngrok http 8000"
) || echo       [SKIP] ngrok not found in PATH

echo.
echo ============================================
echo   All services launched!
echo ============================================
echo   MongoDB:   localhost:27017
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:4200
echo   n8n:       http://localhost:5678
echo   ngrok:     check ngrok window
echo ============================================
pause
