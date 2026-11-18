param(
    [string]$TaskName = "Pemara Sprunki FLUX Weekly Compare",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Root "bootstrap_flux_experiments.ps1"
$taskRun = "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -Python `"$Python`" -RunCompare"

& schtasks.exe /Create /TN $TaskName /TR $taskRun /SC WEEKLY /D SUN /ST 01:30 /F | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao criar tarefa semanal de comparacao FLUX."
}

Write-Host "Tarefa instalada: $TaskName"
Write-Host "Horario: domingos as 01:30"
Write-Host "Runner: $Runner"
