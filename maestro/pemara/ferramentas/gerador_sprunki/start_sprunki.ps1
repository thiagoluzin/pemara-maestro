param(
    [int]$Port = 5005,
    [string]$Python = "python",
    [int]$StartupTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $Root "app.py"
$LogDir = Join-Path $Root "logs"
$OutLog = Join-Path $LogDir "sprunki.out.log"
$ErrLog = Join-Path $LogDir "sprunki.err.log"
$PidFile = Join-Path $LogDir "sprunki.pid"
$HealthUrl = "http://127.0.0.1:$Port/api/health"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path (Join-Path $LogDir "sprunki.watchdog.log") -Value "[$stamp] $Message"
}

function Test-Health {
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    } catch {
        return $false
    }
}

if (Test-Health) {
    Write-Log "Sprunki ja esta saudavel em $HealthUrl"
    exit 0
}

$existing = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match "python" -and
        $_.CommandLine -like "*$App*"
    } |
    Select-Object -First 1

if ($existing) {
    Write-Log "Processo Sprunki existe mas health falhou. Encerrando PID $($existing.ProcessId)."
    Stop-Process -Id $existing.ProcessId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Log "Iniciando Sprunki em $Root na porta $Port"
$env:SPRUNKI_PORT = [string]$Port
$env:SPRUNKI_HOST = "127.0.0.1"

$process = Start-Process `
    -FilePath $Python `
    -ArgumentList @($App) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $PidFile -Value $process.Id
Write-Log "Processo iniciado com PID $($process.Id)"

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-Health) {
        Write-Log "Sprunki ficou saudavel em $HealthUrl"
        exit 0
    }
    Start-Sleep -Seconds 2
}

Write-Log "Falha: Sprunki nao respondeu em $StartupTimeoutSeconds segundos. Veja $ErrLog"
exit 1
