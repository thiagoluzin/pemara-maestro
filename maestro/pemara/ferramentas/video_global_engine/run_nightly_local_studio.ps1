param(
  [string]$Start = "00:31",
  [string]$Stop = "04:55",
  [string]$ProjectDir = "E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\intro_ritmos_revolta",
  [string]$IntroToolDir = "E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo",
  [string]$StudioUrl = "http://127.0.0.1:8029",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$LogDir = Join-Path $ProjectDir "logs"
$QcRoot = Join-Path $ProjectDir "qc"
$LockFile = Join-Path $ProjectDir "nightly_local_studio.lock"
$LogFile = Join-Path $LogDir ("nightly_local_studio_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$Runner = Join-Path $IntroToolDir "run_intro_take_queue.py"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $QcRoot | Out-Null

function Write-RunLog {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
  Write-Output $line
}

function Get-MinutesOfDay {
  param([datetime]$Date = (Get-Date))
  return ($Date.Hour * 60) + $Date.Minute
}

function Convert-HhMmToMinutes {
  param([string]$Text)
  $parts = $Text.Split(":")
  return ([int]$parts[0] * 60) + [int]$parts[1]
}

function Test-InWindow {
  $now = Get-MinutesOfDay
  $startMin = Convert-HhMmToMinutes $Start
  $stopMin = Convert-HhMmToMinutes $Stop
  if ($startMin -le $stopMin) {
    return ($now -ge $startMin -and $now -le $stopMin)
  }
  return ($now -ge $startMin -or $now -le $stopMin)
}

function Assert-InWindow {
  if (-not (Test-InWindow)) {
    throw "Fora da janela noturna ($Start-$Stop). Agora: $(Get-Date -Format HH:mm)."
  }
}

function Get-MinutesUntilStop {
  $now = Get-MinutesOfDay
  $stopMin = Convert-HhMmToMinutes $Stop
  if ($now -le $stopMin) { return $stopMin - $now }
  return (24 * 60 - $now) + $stopMin
}

function Wait-ComfyIdle {
  param([int]$MaxMinutes = 45)
  $deadline = (Get-Date).AddMinutes($MaxMinutes)
  while ((Get-Date) -lt $deadline) {
    Assert-InWindow
    try {
      $queue = Invoke-RestMethod -Uri "http://127.0.0.1:8188/queue" -TimeoutSec 10
      $running = @($queue.queue_running).Count
      $pending = @($queue.queue_pending).Count
      Write-RunLog "Comfy queue: running=$running pending=$pending"
      if ($running -eq 0 -and $pending -eq 0) {
        return
      }
    } catch {
      Write-RunLog "Comfy queue indisponivel: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 60
  }
  throw "Comfy nao ficou ocioso dentro de $MaxMinutes minutos."
}

function ConvertTo-CommandLineArg {
  param([string]$Value)
  if ($null -eq $Value) { return '""' }
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '"', '\"') + '"'
}

function Run-Variant {
  param(
    [string]$Name,
    [string[]]$Takes,
    [double]$LoraStrength,
    [int]$Steps
  )

  Assert-InWindow
  if ((Get-MinutesUntilStop) -lt 35) {
    Write-RunLog "Pulando ${Name}: tempo restante menor que 35 minutos."
    return
  }

  Wait-ComfyIdle -MaxMinutes 20

  $args = @(
    $Runner,
    "--takes"
  ) + $Takes + @(
    "--assemble",
    "--lora-strength", ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:0.###}", $LoraStrength)),
    "--steps", "$Steps",
    "--guidance", "7",
    "--fps", "30"
  )

  Write-RunLog "Iniciando variante ${Name}: takes=$($Takes -join ',') lora=$LoraStrength steps=$Steps"
  if ($DryRun) {
    Write-RunLog "DRY-RUN python $($args -join ' ')"
    return
  }

  Push-Location $IntroToolDir
  try {
    $stdout = Join-Path $LogDir ("{0}_{1}_stdout.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"), $Name)
    $stderr = Join-Path $LogDir ("{0}_{1}_stderr.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"), $Name)
    $argLine = ($args | ForEach-Object { ConvertTo-CommandLineArg $_ }) -join " "
    $proc = Start-Process -FilePath "python" -ArgumentList $argLine -WorkingDirectory $IntroToolDir -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr

    if (Test-Path -LiteralPath $stdout) {
      Get-Content -LiteralPath $stdout -ErrorAction SilentlyContinue | ForEach-Object { Write-RunLog $_ }
    }
    if (Test-Path -LiteralPath $stderr) {
      Get-Content -LiteralPath $stderr -ErrorAction SilentlyContinue | ForEach-Object { Write-RunLog $_ }
    }
    if ($proc.ExitCode -ne 0) {
      throw "Runner retornou codigo $($proc.ExitCode) na variante $Name. stdout=$stdout stderr=$stderr"
    }
  } finally {
    Pop-Location
  }
}

function Write-NightlySummary {
  $latest = Get-ChildItem -LiteralPath (Join-Path $ProjectDir "output") -File -Filter "intro_preview_*.mp4" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 4

  $summary = [ordered]@{
    created_at = (Get-Date).ToString("s")
    window = "$Start-$Stop"
    log = $LogFile
    latest_outputs = @($latest | ForEach-Object {
      [ordered]@{
        file = $_.FullName
        size_mb = [math]::Round($_.Length / 1MB, 2)
        last_write = $_.LastWriteTime.ToString("s")
      }
    })
    next_action = "Comparar contra golden VEO 3.1 e testar LoRA pronta de camera/motion em take unico."
  }

  $out = Join-Path $LogDir "nightly_local_studio_latest_summary.json"
  ($summary | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $out -Encoding UTF8
  Write-RunLog "Resumo atualizado: $out"
}

if (Test-Path -LiteralPath $LockFile) {
  $owner = Get-Content -LiteralPath $LockFile -ErrorAction SilentlyContinue
  throw "Lock ativo: $LockFile ($owner)"
}

Set-Content -LiteralPath $LockFile -Value ("pid={0}; started={1}" -f $PID, (Get-Date).ToString("s")) -Encoding UTF8

try {
  Write-RunLog "==== Inicio rotina noturna Estudio Local ===="
  Assert-InWindow
  Write-RunLog "Janela valida: $Start-$Stop"
  Write-RunLog "GPU antes: $(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader)"

  # O objetivo nao e renderizar 60s toda noite. E descobrir stack local que se aproxima do VEO.
  try {
    Run-Variant -Name "motion_baseline_lora012_takes_02_04" -Takes @("02", "04") -LoraStrength 0.12 -Steps 36
  } catch {
    Write-RunLog "VARIANTE_FALHOU motion_baseline_lora012_takes_02_04: $($_.Exception.Message)"
  }
  try {
    Run-Variant -Name "motion_stronger_lora016_takes_02_04" -Takes @("02", "04") -LoraStrength 0.16 -Steps 40
  } catch {
    Write-RunLog "VARIANTE_FALHOU motion_stronger_lora016_takes_02_04: $($_.Exception.Message)"
  }

  Write-NightlySummary
  Write-RunLog "GPU depois: $(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader)"
  Write-RunLog "==== Fim rotina noturna Estudio Local ===="
} catch {
  Write-RunLog "ERRO: $($_.Exception.Message)"
  throw
} finally {
  Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
}
