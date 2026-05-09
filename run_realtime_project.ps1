param(
    [switch]$SkipInstall,
    [switch]$SkipPipeline,
    [double]$TrafficIntervalSeconds = 2.0,
    [int]$TrafficBurst = 1
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Invoke-Step {
    param(
        [scriptblock]$Command,
        [string]$ErrorMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

Write-Host ''
Write-Host '=============================================' -ForegroundColor Cyan
Write-Host 'DROP-OFF REALTIME RUNNER' -ForegroundColor Cyan
Write-Host '=============================================' -ForegroundColor Cyan

if (-not $SkipInstall) {
    Write-Host 'Installing dependencies from requirements.txt...'
    Invoke-Step -Command { python -m pip install --upgrade pip setuptools wheel } -ErrorMessage 'Failed to prepare pip/setuptools/wheel.'
    Invoke-Step -Command { python -m pip install -r requirements.txt } -ErrorMessage 'Failed to install dependencies from requirements.txt.'
}

if (-not $SkipPipeline) {
    $modelPath = Join-Path $repoRoot 'models\final_model.pkl'
    if (-not (Test-Path $modelPath)) {
        Write-Host 'Model artifact missing. Running full pipeline...'
        Invoke-Step -Command { python run_pipeline.py } -ErrorMessage 'Pipeline run failed.'
    }
}

Write-Host 'Running database migration...'
Invoke-Step -Command { python mlops/deployment/db/migrate.py } -ErrorMessage 'Database migration failed.'

if (-not $env:APP_ENV) { $env:APP_ENV = 'dev' }
if (-not $env:API_KEY) { $env:API_KEY = 'dev-local-key' }
if (-not $env:DROPOFF_API_URL) { $env:DROPOFF_API_URL = 'http://127.0.0.1:5000' }

$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

function Stop-FromPidFile {
    param([string]$PidFile)

    if (Test-Path $PidFile) {
        $oldPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($oldPid) {
            Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        }
    }
}

$apiPidFile = Join-Path $logDir 'realtime_api.pid'
$dashPidFile = Join-Path $logDir 'realtime_dashboard.pid'
$trafficPidFile = Join-Path $logDir 'realtime_traffic.pid'

Stop-FromPidFile -PidFile $apiPidFile
Stop-FromPidFile -PidFile $dashPidFile
Stop-FromPidFile -PidFile $trafficPidFile

# Ensure required ports are free even if older processes were started outside PID files.
Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

$apiOut = Join-Path $logDir 'realtime_api.out.log'
$apiErr = Join-Path $logDir 'realtime_api.err.log'
$dashOut = Join-Path $logDir 'realtime_dashboard.out.log'
$dashErr = Join-Path $logDir 'realtime_dashboard.err.log'
$trafficOut = Join-Path $logDir 'realtime_traffic.out.log'
$trafficErr = Join-Path $logDir 'realtime_traffic.err.log'

Write-Host 'Starting API service...'
$apiProcess = Start-Process -FilePath 'python' -ArgumentList '-m src.api.app' -PassThru -WindowStyle Hidden -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr
Set-Content -Path $apiPidFile -Value $apiProcess.Id

Write-Host 'Waiting for API health...'
$healthUrl = 'http://127.0.0.1:5000/health'
$headers = @{ 'X-API-Key' = $env:API_KEY }
$ready = $false
for ($attempt = 1; $attempt -le 40; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Headers $headers -Method Get -TimeoutSec 4
        if ($response) {
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 1500
    }
}

if (-not $ready) {
    Write-Host 'API did not become ready. Check logs/realtime_api.err.log' -ForegroundColor Red
    exit 1
}

Write-Host 'Starting live traffic generator...'
$trafficArgs = @(
    '-u',
    'live_traffic_generator.py',
    '--api-url', $env:DROPOFF_API_URL,
    '--api-key', $env:API_KEY,
    '--interval', "$TrafficIntervalSeconds",
    '--burst', "$TrafficBurst"
)
$trafficProcess = Start-Process -FilePath 'python' -ArgumentList $trafficArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $trafficOut -RedirectStandardError $trafficErr
Set-Content -Path $trafficPidFile -Value $trafficProcess.Id

Write-Host 'Starting Streamlit dashboard...'
$dashArgs = @(
    '-m', 'streamlit', 'run', 'streamlit_dashboard.py',
    '--server.port', '8502',
    '--client.showErrorDetails=false',
    '--logger.level=error'
)
$dashProcess = Start-Process -FilePath 'python' -ArgumentList $dashArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $dashOut -RedirectStandardError $dashErr
Set-Content -Path $dashPidFile -Value $dashProcess.Id

Write-Host ''
Write-Host 'Realtime system is running.' -ForegroundColor Green
Write-Host 'Dashboard: http://localhost:8502' -ForegroundColor Yellow
Write-Host 'API:       http://127.0.0.1:5000' -ForegroundColor Yellow
Write-Host ''
Write-Host 'PID files:' -ForegroundColor Cyan
Write-Host "  API:       $apiPidFile"
Write-Host "  Dashboard: $dashPidFile"
Write-Host "  Traffic:   $trafficPidFile"
Write-Host ''
Write-Host 'To stop realtime services:' -ForegroundColor Cyan
Write-Host "  Get-Content '$apiPidFile' | ForEach-Object { Stop-Process -Id `$_ -Force }"
Write-Host "  Get-Content '$dashPidFile' | ForEach-Object { Stop-Process -Id `$_ -Force }"
Write-Host "  Get-Content '$trafficPidFile' | ForEach-Object { Stop-Process -Id `$_ -Force }"
