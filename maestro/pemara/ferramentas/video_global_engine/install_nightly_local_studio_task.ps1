param(
  [string]$TaskName = "Pemara Video Studio Local Nightly",
  [string]$Script = "E:\Pemara\maestro\pemara\ferramentas\video_global_engine\run_nightly_local_studio.ps1",
  [string]$StartTime = "00:31",
  [switch]$DisableSprunkiGpuTasks,
  [switch]$RunNowDryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Script)) {
  throw "Script not found: $Script"
}

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""

$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 4 -Minutes 30)

$principal = New-ScheduledTaskPrincipal `
  -UserId $env:USERNAME `
  -LogonType Interactive `
  -RunLevel Highest

$registered = $false
try {
  Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Rotina noturna do Estudio Pemara local: testes por takes contra benchmark VEO 3.1, com lock, janela e logs." `
    -Force | Out-Null
  $registered = $true
  Write-Host "Task instalada via Register-ScheduledTask: $TaskName ($StartTime)"
} catch {
  Write-Host "Register-ScheduledTask falhou: $($_.Exception.Message)"
  Write-Host "Tentando fallback com schtasks.exe..."
  $taskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Script`""
  & schtasks.exe /Create /TN $TaskName /TR $taskRun /SC DAILY /ST $StartTime /F | Write-Host
  if ($LASTEXITCODE -ne 0) {
    throw "Falha ao criar task tambem via schtasks.exe. Codigo: $LASTEXITCODE"
  }
  $registered = $true
  Write-Host "Task instalada via schtasks.exe: $TaskName ($StartTime)"
}

if ($DisableSprunkiGpuTasks) {
  $conflicts = @(
    "Pemara Sprunki LoRA Daily Training",
    "Pemara Sprunki FLUX Weekly Compare",
    "Pemara Sprunki LoRA Krea Weekly Experiment",
    "RitmosIntroTreinoStart1300UntilStop"
  )

  foreach ($name in $conflicts) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
      try {
        Disable-ScheduledTask -TaskName $name | Out-Null
        Write-Host "Task GPU conflitante pausada: $name"
      } catch {
        Write-Host "Nao consegui pausar $name via Disable-ScheduledTask: $($_.Exception.Message)"
        & schtasks.exe /Change /TN $name /DISABLE | Write-Host
      }
    }
  }
}

if ($RunNowDryRun) {
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Script -DryRun
}

if ($registered) {
  Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Select-Object TaskName,State
  Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue | Select-Object LastRunTime,LastTaskResult,NextRunTime
}
