param(
    [string]$TaskName = "Pemara Sprunki LoRA Krea Weekly Experiment",
    [string]$Python = "python",
    [int]$Steps = 1200
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Root "run_krea_lora_experiment.ps1"
$taskRun = "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -Python `"$Python`" -Steps $Steps"

& schtasks.exe /Create /TN $TaskName /TR $taskRun /SC WEEKLY /D SUN /ST 03:00 /F | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao criar tarefa semanal de experimento Krea."
}

Write-Host "Tarefa instalada: $TaskName"
Write-Host "Horario: domingos as 03:00"
Write-Host "Runner: $Runner"
