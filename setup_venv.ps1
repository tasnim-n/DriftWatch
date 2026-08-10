# DriftWatch PowerShell Setup Script
Write-Host "Setting up DriftWatch environment..." -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Virtual Environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating Virtual Environment and installing dependencies..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Environment setup complete!" -ForegroundColor Green
Write-Host "To run DriftWatch: .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000" -ForegroundColor Cyan
