param(
    [switch]$SkipInstall,
    [switch]$UseFullRequirements,
    [switch]$RunDashboard,
    [switch]$SkipDashboard
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = (Get-Command python).Source
}

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

if (-not $SkipInstall) {
    $requirementsFile = if ($UseFullRequirements) { 'requirements.txt' } else { 'requirements-demo.txt' }
    Write-Host 'Installing dependencies...'
    Invoke-Step -Command { & $pythonExe -m pip install --upgrade pip setuptools wheel } -ErrorMessage 'Failed to prepare pip/setuptools/wheel.'
    Invoke-Step -Command { & $pythonExe -m pip install -r $requirementsFile } -ErrorMessage "Failed to install dependencies from $requirementsFile."
}

Write-Host 'Running database migration...'
Invoke-Step -Command { & $pythonExe mlops/deployment/db/migrate.py } -ErrorMessage 'Database migration failed.'

Write-Host 'Running core contract tests...'
Invoke-Step -Command { & $pythonExe -m pytest tests/contract/test_predict_contract.py tests/contract/test_crud_operations.py -q } -ErrorMessage 'Contract tests failed.'

Write-Host 'Starting API server in the background...'
if (-not $env:APP_ENV) { $env:APP_ENV = 'dev' }
if (-not $env:API_KEY) { $env:API_KEY = 'dev-local-key' }

$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$stdoutLog = Join-Path $logDir 'demo_api.out.log'
$stderrLog = Join-Path $logDir 'demo_api.err.log'
$pidFile = Join-Path $logDir 'demo_api.pid'

if (Test-Path $pidFile) {
    $previousPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($previousPid) {
        Stop-Process -Id $previousPid -Force -ErrorAction SilentlyContinue
    }
}

$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m src.api.app' -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
Set-Content -Path $pidFile -Value $apiProcess.Id

Write-Host 'Waiting for health endpoint...'
$healthUrl = 'http://127.0.0.1:5000/health'
$headers = @{ 'X-API-Key' = $env:API_KEY }
$ready = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Headers $headers -Method Get -TimeoutSec 5
        if ($response) {
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host 'API did not become ready. Check logs/demo_api.err.log.'
    exit 1
}

Write-Host 'API is ready.'
Write-Host 'Health endpoint:'
$response | ConvertTo-Json -Depth 6
Write-Host ''
Write-Host 'Demo process complete. API is still running in the background.'
Write-Host "PID saved to $pidFile"

$shouldRunDashboard = $RunDashboard -or (-not $SkipDashboard)

if ($shouldRunDashboard) {
    Write-Host 'Starting dashboard in the background...'
    $dashboardLogOut = Join-Path $logDir 'dashboard.out.log'
    $dashboardLogErr = Join-Path $logDir 'dashboard.err.log'
    $dashboardPidFile = Join-Path $logDir 'dashboard.pid'

    if (Test-Path $dashboardPidFile) {
        $previousDashboardPid = (Get-Content $dashboardPidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($previousDashboardPid) {
            Stop-Process -Id $previousDashboardPid -Force -ErrorAction SilentlyContinue
        }
    }

    $dashboardProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m streamlit run streamlit_dashboard.py --server.address 127.0.0.1 --server.port 8502' -PassThru -WindowStyle Hidden -RedirectStandardOutput $dashboardLogOut -RedirectStandardError $dashboardLogErr
    Set-Content -Path $dashboardPidFile -Value $dashboardProcess.Id

    $dashboardUrl = 'http://127.0.0.1:8502'
    $dashboardReady = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $dashboardUrl -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                $dashboardReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    if ($dashboardReady) {
        Write-Host 'Dashboard is ready at http://127.0.0.1:8502'
    } else {
        Write-Host 'Dashboard did not become ready. Check logs/dashboard.err.log.'
    }
}
