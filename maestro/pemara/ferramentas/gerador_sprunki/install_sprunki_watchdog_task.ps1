param(
    [string]$TaskName = "Pemara Sprunki Watchdog",
    [int]$Port = 5005,
    [string]$Python = "python",
    [string]$PublicUrl = "https://sprunki.pemaratech.com.br/",
    [switch]$RunAsSystem
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Watchdog = Join-Path $Root "watchdog_sprunki.ps1"

$arguments = "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$Watchdog`" -Once -Port $Port -Python `"$Python`" -PublicUrl `"$PublicUrl`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $Root
$triggerPrimary = if ($RunAsSystem) {
    New-ScheduledTaskTrigger -AtStartup
} else {
    New-ScheduledTaskTrigger -AtLogOn
}
$triggerMinute = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = if ($RunAsSystem) {
    New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
} else {
    New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
}

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerPrimary, $triggerMinute) -Settings $settings -Principal $principal -Description "Mantem o Portal Sprunki online localmente e confere o acesso publico protegido." -Force | Out-Null
} catch {
    if ($RunAsSystem) {
        throw "A instalacao 24/7 como SYSTEM requer execucao elevada: $($_.Exception.Message)"
    }
    Write-Warning "Register-ScheduledTask falhou: $($_.Exception.Message)"
    Write-Warning "Tentando fallback com schtasks.exe no usuario atual."

    $taskRun = "powershell.exe $arguments"
    & schtasks.exe /Create /TN $TaskName /TR $taskRun /SC MINUTE /MO 1 /F | Out-Host

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar tarefa tambem via schtasks.exe. Execute este script em um PowerShell com permissao para criar tarefas."
    }
}

Write-Host "Tarefa instalada: $TaskName"
Write-Host "Watchdog: $Watchdog"
Write-Host "Health: http://127.0.0.1:$Port/api/health"
Write-Host "Publico protegido: $PublicUrl"
Write-Host "Execucao: $(if ($RunAsSystem) { 'SYSTEM 24/7' } else { 'usuario atual' })"
