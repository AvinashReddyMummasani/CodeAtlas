# CodeAtlas – Backend startup script (Windows PowerShell)
Set-Location "$PSScriptRoot\backend"

Write-Host "Checking Python..." -ForegroundColor Cyan
python --version

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "Starting CodeAtlas backend on http://localhost:8000" -ForegroundColor Green
python main.py
