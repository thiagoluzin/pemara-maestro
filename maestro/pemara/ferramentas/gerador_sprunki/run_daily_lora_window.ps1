param(
    [string]$StartTime = "00:31",
    [string]$EndTime = "04:59",
    [string]$Python = "python",
    [int]$Steps = 900,
    [int]$Dim = 8,
    [int]$Alpha = 8,
    [int]$BatchSize = 2,
    [double]$LearningRate = 0.00002,
    [int]$EvalSamples = 4,
    [string]$EvalStrengths = "0.15,0.30,0.45"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "logs"
$Script = Join-Path $Root "daily_lora_cycle.py"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-RunLog {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path (Join-Path $LogDir "daily_lora_window.log") -Value "[$stamp] $Message"
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Pemara\gpu_window_guard.ps1" -Name "sprunki-daily-lora" -Kind "training"
if ($LASTEXITCODE -ne 0) {
    Write-RunLog "Bloqueado pela janela global de GPU. Permitido somente 00:31-04:59."
    exit 0
}

$now = Get-Date
$start = [datetime]::ParseExact($StartTime, "HH:mm", $null)
$end = [datetime]::ParseExact($EndTime, "HH:mm", $null)
$windowStart = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $start.Hour -Minute $start.Minute -Second 0
$windowEnd = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $end.Hour -Minute $end.Minute -Second 0

if ($windowEnd -le $windowStart) {
    $windowEnd = $windowEnd.AddDays(1)
}

if ($now -lt $windowStart) {
    Write-RunLog "Antes da janela ($StartTime-$EndTime). Saindo."
    exit 0
}

if ($now -ge $windowEnd) {
    Write-RunLog "Depois da janela ($StartTime-$EndTime). Saindo."
    exit 0
}

$deadline = $windowEnd.ToString("s")
Write-RunLog "Iniciando ciclo diario ate $deadline com steps=$Steps dim=$Dim alpha=$Alpha batch=$BatchSize lr=$LearningRate eval=$EvalSamples strengths=$EvalStrengths"

& $Python $Script `
    --deadline $deadline `
    --steps $Steps `
    --dim $Dim `
    --alpha $Alpha `
    --batch-size $BatchSize `
    --learning-rate $LearningRate `
    --eval-samples $EvalSamples `
    --eval-strengths $EvalStrengths `
    --python $Python
$code = $LASTEXITCODE

Write-RunLog "Ciclo diario finalizado com code=$code"
exit $code
