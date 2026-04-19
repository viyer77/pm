# Start script for Windows PowerShell

Write-Host "Building Docker image..."
docker compose build

Write-Host "Starting container..."
docker compose up -d

Write-Host "Waiting for service to be ready..."
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✓ Service started successfully!"
Write-Host "Frontend: http://localhost:8000"
Write-Host "API Test: curl http://localhost:8000/api/test"
Write-Host "Health: curl http://localhost:8000/health"
Write-Host ""
Write-Host "To stop: .\scripts\stop.ps1"
