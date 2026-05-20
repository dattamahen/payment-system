@echo off
echo ============================================
echo   Importing n8n Workflows
echo ============================================
echo.

set WORKFLOWS_DIR=%~dp0n8n-workflows

echo [1/3] Importing Registration Flow...
n8n import:workflow --input="%WORKFLOWS_DIR%\registration-flow.json"

echo [2/3] Importing Payment Confirmation...
n8n import:workflow --input="%WORKFLOWS_DIR%\payment-confirmation.json"

echo [3/3] Importing Webhook Verify...
n8n import:workflow --input="%WORKFLOWS_DIR%\webhook-verify.json"

echo.
echo ============================================
echo   All workflows imported!
echo   Open http://localhost:5678 and ACTIVATE each workflow.
echo ============================================
pause
