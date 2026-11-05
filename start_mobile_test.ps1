# AuraVitals Mobile Testing via Cloudflare Tunnel
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "         AuraVitals - Mobile Camera Testing via Cloudflare            " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Launching FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python run.py"

Write-Host "[2/3] Launching Vite Frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location frontend; npm run dev"

Write-Host "`nWaiting 4 seconds for local servers to start..." -ForegroundColor DarkGray
Start-Sleep -Seconds 4

Write-Host ""
Write-Host "[3/3] Starting Cloudflare HTTPS Tunnel to http://localhost:5173 ..." -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host " Look below for the line containing: " -ForegroundColor White
Write-Host "   https://xxxx.trycloudflare.com " -ForegroundColor Green -BackgroundColor Black
Write-Host " Open that HTTPS link on your phone browser (Chrome on Android / Safari on iOS)!" -ForegroundColor White
Write-Host "----------------------------------------------------------------------`n" -ForegroundColor Cyan

& .\cloudflared.exe tunnel --url http://localhost:5173

