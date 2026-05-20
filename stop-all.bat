@echo off
title EventPay - Stop All Services
echo Stopping all EventPay services...

taskkill /FI "WINDOWTITLE eq EventPay-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq EventPay-Frontend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq EventPay-ngrok" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq EventPay-MongoDB" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq EventPay-n8n" /F >nul 2>&1
taskkill /IM mongod.exe /F >nul 2>&1

echo All services stopped.
pause
