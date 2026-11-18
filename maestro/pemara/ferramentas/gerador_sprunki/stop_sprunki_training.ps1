$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "logs"
$StopFlag = Join-Path $Root "STOP_SPRUNKI_TRAINING.flag"
$PriorityFlag = Join-Path $Root "SPRUNKI_TRAINING_PRIORITY.flag"
$PidFile = Join-Path $LogDir "sprunki_until_stop.pid"
$CycleLock = Join-Path $LogDir "daily_lora_cycle.lock"
$LogFile = Join-Path $LogDir "sprunki_until_stop.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Content -LiteralPath $StopFlag -Value "Stop requested at $(Get-Date -Format s)" -Encoding UTF8
Remove-Item -LiteralPath $PriorityFlag -Force -ErrorAction SilentlyContinue

function Write-StopLog {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogFile -Value "[$stamp] $Message" -Encoding UTF8
}

Write-StopLog "Stop solicitado."

if (Test-Path -LiteralPath $CycleLock) {
    try {
        $lock = Get-Content -Raw -LiteralPath $CycleLock | ConvertFrom-Json
        $cyclePid = [int]$lock.pid
        if ($cyclePid -gt 0) {
            Write-StopLog "Encerrando ciclo diario PID $cyclePid."
            taskkill /PID $cyclePid /T /F | Out-Null
        }
    } catch {
        Write-StopLog "Falha lendo lock: $($_.Exception.Message)"
    }
}

if (Test-Path -LiteralPath $PidFile) {
    try {
        $runnerPid = [int](Get-Content -LiteralPath $PidFile | Select-Object -First 1)
        if ($runnerPid -gt 0) {
            Write-StopLog "Encerrando runner PID $runnerPid."
            taskkill /PID $runnerPid /T /F | Out-Null
        }
    } catch {
        Write-StopLog "Falha encerrando runner: $($_.Exception.Message)"
    }
}

Write-Output "Stop Sprunki solicitado. Logs: $LogFile"
