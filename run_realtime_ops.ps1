# Drop-Off Detection: Real-Time Operations Launcher
# Run this script to start the entire ecosystem in real-time mode.

$ProjectDir = Get-Location
$API_PORT = 5000
$API_URL = "http://127.0.0.1:$API_PORT"

Write-Host "🚀 Launching Real-Time Operations..." -ForegroundColor Cyan

# 1. Start the Flask API Server
Write-Host "[1/4] Starting API Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python src/api/app.py" -WindowStyle Normal

# Wait for API to warm up
Write-Host "Waiting for API to initialize..."
Start-Sleep -Seconds 5

# 2. Start the Streamlit Dashboard
Write-Host "[2/4] Starting Streamlit Dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m streamlit run streamlit_dashboard.py" -WindowStyle Normal

# 3. Start the Automated Alerting Monitor
Write-Host "[3/4] Starting Alerting Engine..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python src/api/alerting.py" -WindowStyle Normal

# 4. Start the Live Traffic Generator
Write-Host "[4/4] Starting Live Traffic Generator..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python live_traffic_generator.py --interval 1.5 --burst 2" -WindowStyle Normal

Write-Host "✅ All systems are running!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "API Status: $API_URL/status"
Write-Host "Dashboard:  http://localhost:8501"
Write-Host "--------------------------------------------------"
Write-Host "Check the 'Real-Time Ops' tab in the dashboard."
