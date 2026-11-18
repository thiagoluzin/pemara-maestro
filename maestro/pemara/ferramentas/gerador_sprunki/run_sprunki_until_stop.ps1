param(
    [string]$Python = "python",
    [int]$SleepSecondsAfterFailure = 120,
    [int]$EvalSamples = 4,
    [string]$EvalStrengths = "0.15,0.30,0.45",
    [string]$RunPrefix = "sprunki_until_stop"
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root "daily_lora_cycle.py"
$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir "sprunki_until_stop.log"
$PriorityFlag = Join-Path $Root "SPRUNKI_TRAINING_PRIORITY.flag"
$StopFlag = Join-Path $Root "STOP_SPRUNKI_TRAINING.flag"
$PidFile = Join-Path $LogDir "sprunki_until_stop.pid"
$GpuGuard = "E:\Pemara\gpu_window_guard.ps1"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File $GpuGuard -Name "sprunki-until-stop" -Kind "training" -Quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Treino Sprunki bloqueado pela pausa global. Codigo=$LASTEXITCODE"
    exit $LASTEXITCODE
}
Set-Content -LiteralPath $PidFile -Value $PID -Encoding UTF8
Remove-Item -LiteralPath $StopFlag -Force -ErrorAction SilentlyContinue
Set-Content -LiteralPath $PriorityFlag -Value "Sprunki training priority active since $(Get-Date -Format s). Remove STOP flag or run stop_sprunki_training.ps1 to end." -Encoding UTF8

function Write-RunLog {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogFile -Value "[$stamp] $Message" -Encoding UTF8
}

function Get-Preset {
    param([int]$Index)
    $presets = @(
        @{ Steps = 900;  Dim = 8;  Alpha = 8;  LearningRate = "0.00002"; Label = "stable_900_d8" },
        @{ Steps = 1200; Dim = 8;  Alpha = 8;  LearningRate = "0.00002"; Label = "stronger_1200_d8" },
        @{ Steps = 1200; Dim = 16; Alpha = 16; LearningRate = "0.00002"; Label = "capacity_1200_d16" },
        @{ Steps = 1500; Dim = 16; Alpha = 16; LearningRate = "0.000015"; Label = "refine_1500_d16_lr15" }
    )
    return $presets[$Index % $presets.Count]
}

Write-RunLog "Inicio modo ate parar. pid=$PID eval=$EvalSamples strengths=$EvalStrengths"

$cycle = 0
while (-not (Test-Path -LiteralPath $StopFlag)) {
    $preset = Get-Preset -Index $cycle
    $label = $preset.Label
    $prefix = "${RunPrefix}_${label}"

    Write-RunLog "Ciclo $cycle preset=$label steps=$($preset.Steps) dim=$($preset.Dim) alpha=$($preset.Alpha) lr=$($preset.LearningRate)"
    try {
        nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits | ForEach-Object {
            Write-RunLog "GPU antes: $_"
        }
    } catch {
        Write-RunLog "GPU antes indisponivel: $($_.Exception.Message)"
    }

    & $Python $Script `
        --steps $preset.Steps `
        --dim $preset.Dim `
        --alpha $preset.Alpha `
        --learning-rate $preset.LearningRate `
        --batch-size 2 `
        --eval-samples $EvalSamples `
        --eval-strengths $EvalStrengths `
        --run-prefix $prefix `
        --python $Python

    $code = $LASTEXITCODE
    Write-RunLog "Ciclo $cycle finalizado code=$code"

    try {
        nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits | ForEach-Object {
            Write-RunLog "GPU depois: $_"
        }
    } catch {
        Write-RunLog "GPU depois indisponivel: $($_.Exception.Message)"
    }

    if ($code -ne 0) {
        Write-RunLog "Falha/timeout code=$code; aguardando $SleepSecondsAfterFailure segundos antes de tentar novamente."
        Start-Sleep -Seconds $SleepSecondsAfterFailure
    }

    $cycle += 1
}

Write-RunLog "Stop flag detectada. Encerrando modo ate parar."
Remove-Item -LiteralPath $PriorityFlag -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
exit 0
