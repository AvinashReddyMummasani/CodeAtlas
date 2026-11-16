# CodeAtlas — One-line launcher: .\run.ps1
# Starts FastAPI backend and opens browser automatically

param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║      🗺️  CodeAtlas — AI Code Explorer     ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ✗ Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}
$pyVersion = python --version 2>&1
Write-Host "  ✓ $pyVersion" -ForegroundColor Green

# Check/install dependencies
Write-Host "  Checking dependencies..." -ForegroundColor Gray
$reqs = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqs) {
    python -m pip install -r $reqs -q --disable-pip-version-check 2>$null
    Write-Host "  ✓ Dependencies ready" -ForegroundColor Green
}

# Load .env if exists
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
    Write-Host "  ✓ Environment loaded from .env" -ForegroundColor Green
}

$url = "http://localhost:$Port"
Write-Host ""
Write-Host "  🚀 Starting CodeAtlas on $url" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Open browser after 2 seconds
if (-not $NoBrowser) {
    $browserJob = Start-Job {
        param($u)
        Start-Sleep 2.5
        Start-Process $u
    } -ArgumentList $url
}

# Start the backend
Set-Location $PSScriptRoot
python -m uvicorn backend.main:app --host 0.0.0.0 --port $Port --reload --reload-dir backend

# Cleanup
if ($browserJob) { Remove-Job $browserJob -Force -ErrorAction SilentlyContinue }
