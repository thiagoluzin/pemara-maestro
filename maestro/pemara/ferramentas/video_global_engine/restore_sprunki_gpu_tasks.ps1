$ErrorActionPreference = "Continue"

$tasks = @(
  "Pemara Sprunki LoRA Daily Training",
  "Pemara Sprunki FLUX Weekly Compare",
  "Pemara Sprunki LoRA Krea Weekly Experiment",
  "RitmosIntroTreinoStart1300UntilStop"
)

foreach ($name in $tasks) {
  $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if ($task) {
    try {
      Enable-ScheduledTask -TaskName $name | Out-Null
      Write-Host "Reativada: $name"
    } catch {
      Write-Host "Falha via Enable-ScheduledTask em ${name}: $($_.Exception.Message)"
      & schtasks.exe /Change /TN $name /ENABLE | Write-Host
    }
  } else {
    Write-Host "Nao encontrada: $name"
  }
}

Get-ScheduledTask -TaskName $tasks -ErrorAction SilentlyContinue | Select-Object TaskName,State
