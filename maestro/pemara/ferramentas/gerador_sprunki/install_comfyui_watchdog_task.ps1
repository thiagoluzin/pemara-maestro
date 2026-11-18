param(
    [string]$TaskName = "Pemara ComfyUI Watchdog",
    [string]$LegacyTaskName = "PemaraComfyUI",
    [string]$ComfyPath = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI",
    [int]$Port = 8188,
    [string]$ListenHost = "127.0.0.1",
    [string]$Python = "python",
    [string]$ExtraArgs = "--cuda-device 0"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Watchdog = Join-Path $Root "watchdog_comfyui.ps1"

$taskRun = "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$Watchdog`" -Once -ComfyPath `"$ComfyPath`" -Port $Port -ListenHost $ListenHost -Python `"$Python`" -ExtraArgs `"$ExtraArgs`""

& schtasks.exe /Create /TN $TaskName /TR $taskRun /SC MINUTE /MO 1 /F | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao criar tarefa de watchdog do ComfyUI."
}

# A tarefa antiga inicia o mesmo main.py diretamente e pode disputar a porta
# com o watchdog durante um boot frio. O watchdog deve ser a unica autoridade.
if ($LegacyTaskName -and $LegacyTaskName -ne $TaskName) {
    $legacyTask = Get-ScheduledTask -TaskName $LegacyTaskName -ErrorAction SilentlyContinue
    if ($legacyTask) {
        Stop-ScheduledTask -TaskName $LegacyTaskName -ErrorAction SilentlyContinue
        Disable-ScheduledTask -TaskName $LegacyTaskName -ErrorAction Stop | Out-Null
        Write-Host "Tarefa legada desativada: $LegacyTaskName"
    }
}

Write-Host "Tarefa instalada: $TaskName"
Write-Host "Watchdog: $Watchdog"
Write-Host "Health: http://${ListenHost}:$Port/system_stats"
