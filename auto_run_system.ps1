# Auto-run system setup - Step by step

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "SILENT USER DROP-OFF DETECTION" -ForegroundColor Cyan
Write-Host "Auto-Run System Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

$projectPath = $PSScriptRoot
Set-Location $projectPath

# ==========================================
# STEP 1: Clean up any existing processes
# ==========================================
Write-Host "`n[STEP 1] Cleaning up existing processes..." -ForegroundColor Yellow

$processes_5000 = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
$processes_8502 = Get-NetTCPConnection -LocalPort 8502 -ErrorAction SilentlyContinue

if ($processes_5000) {
    Write-Host "  -> Stopping Flask API (port 5000)..." -ForegroundColor Gray
    $processes_5000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

if ($processes_8502) {
    Write-Host "  -> Stopping Streamlit Dashboard (port 8502)..." -ForegroundColor Gray
    $processes_8502 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Write-Host "[OK] Cleanup complete" -ForegroundColor Green

# ==========================================
# STEP 2: Start Flask API
# ==========================================
Write-Host "`n[STEP 2] Starting Flask API Server..." -ForegroundColor Yellow
Start-Job -Name "FlaskAPI" -ScriptBlock {
    Set-Location $projectPath
    python -m src.api.app
} | Out-Null

Write-Host "  -> Waiting for Flask to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Check if API is responsive
$apiCheck = $false
for ($i = 1; $i -le 5; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $apiCheck = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($apiCheck) {
    Write-Host "[OK] Flask API running on http://127.0.0.1:5000" -ForegroundColor Green
} else {
    Write-Host "[INFO] Flask API may still be initializing..." -ForegroundColor Yellow
}

# ==========================================
# STEP 3: Start Streamlit Dashboard
# ==========================================
Write-Host "`n[STEP 3] Starting Streamlit Dashboard..." -ForegroundColor Yellow
Start-Job -Name "StreamlitDash" -ScriptBlock {
    Set-Location $projectPath
    python -m streamlit run streamlit_dashboard.py --server.port 8502 --client.showErrorDetails=false --logger.level=error
} | Out-Null

Write-Host "  -> Waiting for Dashboard to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

Write-Host "[OK] Streamlit Dashboard starting on http://localhost:8502" -ForegroundColor Green

# ==========================================
# STEP 4: Display System Status
# ==========================================
Write-Host "`n[STEP 4] System Status Check..." -ForegroundColor Yellow

$jobs = Get-Job | Where-Object {$_.Name -eq "FlaskAPI" -or $_.Name -eq "StreamlitDash"}
Write-Host ""
$jobs | ForEach-Object {
    $status = if ($_.State -eq "Running") { "[RUNNING]" } else { "[STOPPED]" }
    Write-Host "  $($_.Name): $status" -ForegroundColor Green
}

# ==========================================
# STEP 5: Display Access Information
# ==========================================
Write-Host "`n[STEP 5] Access Information..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Dashboard URL: http://localhost:8502" -ForegroundColor Cyan
Write-Host "API URL:       http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Available Pages:" -ForegroundColor Cyan
Write-Host "  1. Dashboard - System overview and metrics" -ForegroundColor Gray
Write-Host "  2. Make Prediction - Single user predictions" -ForegroundColor Gray
Write-Host "  3. Model Metrics - Detailed performance analysis" -ForegroundColor Gray
Write-Host "  4. Advanced Analytics - Feature importance and decision boundaries" -ForegroundColor Gray
Write-Host "  5. API Monitor - Real-time API metrics" -ForegroundColor Gray
Write-Host "  6. Batch Predictions - CSV upload and processing" -ForegroundColor Gray
Write-Host "  7. About - Project information and tech stack" -ForegroundColor Gray

# ==========================================
# STEP 6: Final Instructions
# ==========================================
Write-Host "`n[STEP 6] Ready to Use!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open http://localhost:8502 in your browser" -ForegroundColor Gray
Write-Host "  2. Navigate through the dashboard pages" -ForegroundColor Gray
Write-Host "  3. Try making predictions on sample users" -ForegroundColor Gray
Write-Host "  4. View API metrics and performance data" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop the services:" -ForegroundColor Yellow
Write-Host "  Get-Job | Stop-Job" -ForegroundColor Gray
Write-Host "  Get-Job | Remove-Job" -ForegroundColor Gray
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "System is ready!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
