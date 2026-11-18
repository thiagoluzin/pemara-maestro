param(
    [string]$Take = "06",
    [string[]]$Variants = @("wan_a14b_q4_smoke_512"),
    [int]$MaxWaitMinutes = 180,
    [int]$PollSeconds = 60
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "outputs\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "motion_smoke_when_gpu_free_$Stamp.log"
$LockFile = Join-Path $LogDir "motion_smoke_when_gpu_free.lock"

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    $line | Tee-Object -FilePath $LogFile -Append | Out-Null
}

function Get-BusyTrainingProcess {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -match "flux_train_network\.py|train_network\.py|train_card_lora\.py|run_card_lora_training\.ps1|accelerate.*launch|sd-scripts"
        } |
        Select-Object ProcessId, ParentProcessId, Name, CommandLine
}

function Test-ComfyQueueBusy {
    try {
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:8188/queue" -TimeoutSec 8
        return (($queue.queue_running.Count + $queue.queue_pending.Count) -gt 0)
    }
    catch {
        Write-Log "Comfy queue check falhou: $($_.Exception.Message)"
        return $true
    }
}

if (Test-Path -LiteralPath $LockFile) {
    $existing = Get-Content -LiteralPath $LockFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($existing -match "^\d+$") {
        $process = Get-Process -Id ([int]$existing) -ErrorAction SilentlyContinue
        if ($process) {
            Write-Log "Ja existe smoke aguardando GPU no PID $existing. Saindo."
            exit 0
        }
    }
}

[string]$PID | Set-Content -LiteralPath $LockFile -Encoding ascii
try {
    Write-Log "Aguardando GPU livre para take $Take; variants=$($Variants -join ','); max_wait=${MaxWaitMinutes}min"
    $deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
    while ((Get-Date) -lt $deadline) {
        $busyProcesses = @(Get-BusyTrainingProcess)
        $comfyBusy = Test-ComfyQueueBusy
        if ($busyProcesses.Count -eq 0 -and -not $comfyBusy) {
            Write-Log "GPU aparenta livre: nenhum treino conhecido e fila Comfy vazia."
            break
        }

        $busyList = ($busyProcesses | ForEach-Object { "$($_.ProcessId):$($_.Name)" }) -join ", "
        if (-not $busyList) { $busyList = "nenhum treino conhecido" }
        Write-Log "Aguardando. Treinos: $busyList; comfy_busy=$comfyBusy"
        Start-Sleep -Seconds $PollSeconds
    }

    if ((Get-Date) -ge $deadline) {
        Write-Log "Timeout aguardando GPU livre. Smoke nao iniciado."
        exit 2
    }

    $env:MAESTRO_STUDIO_URL = "http://127.0.0.1:8029"
    $runner = Join-Path $Root "run_motion_escalation.py"
    $args = @($runner, "--take", $Take, "--variants") + $Variants
    Write-Log "Iniciando: python $($args -join ' ')"
    & python @args 2>&1 | Tee-Object -FilePath $LogFile -Append
    $code = $LASTEXITCODE
    Write-Log "Smoke finalizado com exit_code=$code"
    exit $code
}
finally {
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
}

