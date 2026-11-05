@echo off
title AuraVitals Mobile Testing
color 0A

echo ======================================================================
echo          AuraVitals - Mobile Camera Testing via Cloudflare
echo ======================================================================
echo.
echo [1/3] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "AuraVitals Backend" cmd /k "python run.py"

echo [2/3] Launching Vite Frontend on http://localhost:5173 ...
start "AuraVitals Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Waiting 4 seconds for local servers to start...
timeout /t 4 /nobreak > nul

echo.
echo [3/3] Starting Cloudflare HTTPS Tunnel to http://localhost:5173 ...
echo.
echo ----------------------------------------------------------------------
echo  LOOK BELOW for the line that says:
echo    https://xxxx-xxxx-xxxx.trycloudflare.com
echo  Open that HTTPS link on your mobile phone browser (Chrome/Safari).
echo ----------------------------------------------------------------------
echo.

.\cloudflared.exe tunnel --url http://localhost:5173
pause

