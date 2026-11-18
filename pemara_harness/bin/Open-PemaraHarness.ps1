[CmdletBinding(PositionalBinding = $false)]
param(
  [string] $Workspace = 'E:\Pemara',
  [string] $Task,
  [string] $TaskFile,
  [string] $AttachmentsManifest,
  [ValidateSet('local-qwen', 'deepseek-api')]
  [string] $ProviderId = 'local-qwen',
  [switch] $DryRun,
  [switch] $Once,
  [string] $QwenLauncher = 'E:\Pemara\local_ai_qwen\scripts\Start-Qwen38-Yarn524K.ps1',
  [string] $QwenEndpoint = 'http://127.0.0.1:11436/v1/models',
  [string] $ExpectedModel = 'qwen3.8-27b-uncensored-yarn-524k',
  [string] $QwenApiBase = 'http://127.0.0.1:11436/v1',
  [string] $MediaPython = 'E:\Pemara\local_ai_qwen\runtime\media-python\Scripts\python.exe',
  [string] $MediaBridge = 'E:\Pemara\local_ai_qwen\media\media_bridge.py',
  [string] $WhisperModel = 'E:\Pemara\local_ai_qwen\runtime\media-models\faster-whisper-large-v3-turbo',
  [string] $ComfyQueueEndpoint = 'http://127.0.0.1:8188/queue',
  [string] $ComfyFreeEndpoint = 'http://127.0.0.1:8188/free',
  [string] $NvidiaSmiPath = 'nvidia-smi',
  [ValidateRange(0, 131072)]
  [int] $MinimumFreeGpuMiB = 12000,
  [ValidateRange(1, 10)]
  [int] $IdleGpuSampleCount = 5,
  [ValidateRange(0, 100)]
  [int] $MaximumIdleGpuUtilizationPercent = 5,
  [ValidateRange(1, 10)]
  [int] $IdleGpuSampleIntervalSec = 1,
  [ValidateRange(5, 120)]
  [int] $ComfyReleaseTimeoutSec = 30,
  [ValidateRange(5, 600)]
  [int] $QwenStartupTimeoutSec = 150,
  [ValidateRange(1, 60)]
  [int] $RetryIntervalSec = 10
)

$ErrorActionPreference = 'Stop'

trap {
  if ($DryRun -or $Once) {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
  }
  Write-Host ''
  Write-Host "Falha ao abrir o Pemara Harness: $($_.Exception.Message)" -ForegroundColor Red
  [void](Read-Host 'Pressione Enter para fechar')
  exit 1
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$engineLauncher = Join-Path $PSScriptRoot 'start-pemara-dsh.ps1'
$mediaPrepare = Join-Path $projectRoot 'scripts\prepare-media-context.mjs'
$mediaProcessor = Join-Path $projectRoot 'scripts\process-media-attachment.py'
$workspaceRoot = (Resolve-Path -LiteralPath $Workspace).Path
$workspaceItem = Get-Item -LiteralPath $workspaceRoot
$windowsRoot = $env:SystemRoot
if ([string]::IsNullOrWhiteSpace($windowsRoot)) { $windowsRoot = 'C:\Windows' }
$powerShell = Join-Path $windowsRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$usesLocalQwen = $ProviderId -eq 'local-qwen'

if (-not $workspaceItem.PSIsContainer) {
  throw "Workspace is not a directory: $workspaceRoot"
}
if (-not (Test-Path -LiteralPath $engineLauncher -PathType Leaf)) {
  throw "Engine launcher not found: $engineLauncher"
}
if (-not (Test-Path -LiteralPath $QwenLauncher -PathType Leaf)) {
  throw "Qwen launcher not found: $QwenLauncher"
}
if (-not (Test-Path -LiteralPath $powerShell -PathType Leaf)) {
  throw "Windows PowerShell not found: $powerShell"
}
if (-not $usesLocalQwen -and [string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
  throw 'DeepSeek API selecionada, mas DEEPSEEK_API_KEY não está configurada para o Harness. Configure a variável de ambiente e reinicie o monitor.'
}

$monitorRuntime = [IO.Path]::GetFullPath((Join-Path $projectRoot '.runtime\monitor'))
function Resolve-MonitorArtifact([string] $Path, [string] $Label) {
  $resolved = (Resolve-Path -LiteralPath $Path).Path
  $prefix = $monitorRuntime.TrimEnd('\') + '\'
  if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label precisa ficar no runtime isolado do monitor."
  }
  return $resolved
}
if (-not [string]::IsNullOrWhiteSpace($TaskFile)) {
  if (-not [string]::IsNullOrWhiteSpace($Task)) { throw 'Use Task ou TaskFile, nunca os dois.' }
  $TaskFile = Resolve-MonitorArtifact $TaskFile 'TaskFile'
  $Task = (Get-Content -LiteralPath $TaskFile -Raw).Trim()
}
if (-not [string]::IsNullOrWhiteSpace($AttachmentsManifest)) {
  if ([string]::IsNullOrWhiteSpace($TaskFile)) { throw 'AttachmentsManifest exige TaskFile.' }
  $AttachmentsManifest = Resolve-MonitorArtifact $AttachmentsManifest 'AttachmentsManifest'
  if ((Split-Path -Parent $AttachmentsManifest) -ne (Split-Path -Parent $TaskFile)) {
    throw 'TaskFile e AttachmentsManifest precisam pertencer ao mesmo job.'
  }
}

function Get-QwenStatus {
  try {
    $response = Invoke-RestMethod -Uri $QwenEndpoint -Method Get -TimeoutSec 2
    $modelIds = @($response.data | ForEach-Object { [string] $_.id } | Where-Object { $_ })
    return [pscustomobject]@{
      ready = $modelIds -contains $ExpectedModel
      reachable = $true
      models = $modelIds
      error = $null
    }
  }
  catch {
    return [pscustomobject]@{
      ready = $false
      reachable = $false
      models = @()
      error = $_.Exception.Message
    }
  }
}

function Get-GpuSnapshot {
  if ($MinimumFreeGpuMiB -eq 0) {
    return [pscustomobject]@{
      available = $true
      freeGpuMiB = $null
      utilizationPercent = 0
    }
  }
  try {
    $raw = & $NvidiaSmiPath '--query-gpu=memory.free,utilization.gpu' '--format=csv,noheader,nounits' 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($raw -join ''))) {
      throw 'nvidia-smi did not return a GPU row.'
    }
    $line = ($raw | Select-Object -First 1).ToString()
    $parts = $line.Split(',')
    if ($parts.Count -lt 2) { throw "Unexpected nvidia-smi row: $line" }
    return [pscustomobject]@{
      available = $true
      freeGpuMiB = [int]($parts[0].Trim())
      utilizationPercent = [int]($parts[1].Trim())
    }
  }
  catch {
    return [pscustomobject]@{
      available = $false
      freeGpuMiB = $null
      utilizationPercent = $null
    }
  }
}

function Get-ComfyQueueStatus {
  try {
    $queue = Invoke-RestMethod -Uri $ComfyQueueEndpoint -Method Get -TimeoutSec 2
    return [pscustomobject]@{
      reachable = $true
      running = @($queue.queue_running).Count
      pending = @($queue.queue_pending).Count
    }
  }
  catch {
    return [pscustomobject]@{
      reachable = $false
      running = 0
      pending = 0
    }
  }
}

function Get-QwenAdmission {
  $queue = Get-ComfyQueueStatus
  $gpu = Get-GpuSnapshot
  $freeGpuMiB = $gpu.freeGpuMiB

  if ($queue.running -gt 0 -or $queue.pending -gt 0) {
    return [pscustomobject]@{
      allowed = $false
      reason = "ComfyUI tem $($queue.running) trabalho(s) rodando e $($queue.pending) pendente(s)."
      freeGpuMiB = $freeGpuMiB
      gpuUtilizationPercent = $gpu.utilizationPercent
      queueReachable = $queue.reachable
      queueRunning = $queue.running
      queuePending = $queue.pending
    }
  }

  if ($MinimumFreeGpuMiB -gt 0 -and -not $gpu.available) {
    return [pscustomobject]@{
      allowed = $false
      reason = 'Nao foi possivel medir a VRAM livre com nvidia-smi.'
      freeGpuMiB = $null
      gpuUtilizationPercent = $null
      queueReachable = $queue.reachable
      queueRunning = $queue.running
      queuePending = $queue.pending
    }
  }

  if ($MinimumFreeGpuMiB -gt 0 -and $freeGpuMiB -lt $MinimumFreeGpuMiB) {
    return [pscustomobject]@{
      allowed = $false
      reason = "VRAM livre: ${freeGpuMiB} MiB; minimo seguro: ${MinimumFreeGpuMiB} MiB."
      freeGpuMiB = $freeGpuMiB
      gpuUtilizationPercent = $gpu.utilizationPercent
      queueReachable = $queue.reachable
      queueRunning = $queue.running
      queuePending = $queue.pending
    }
  }

  $reason = 'Fila ComfyUI vazia e VRAM admitida.'
  if (-not $queue.reachable) {
    $reason = 'VRAM admitida; endpoint da fila ComfyUI indisponivel.'
  }
  return [pscustomobject]@{
    allowed = $true
    reason = $reason
    freeGpuMiB = $freeGpuMiB
    gpuUtilizationPercent = $gpu.utilizationPercent
    queueReachable = $queue.reachable
    queueRunning = $queue.running
    queuePending = $queue.pending
  }
}

function Release-IdleComfyCache {
  $releaseMutex = New-Object System.Threading.Mutex($false, 'Local\PemaraHarness-ComfyUI-IdleCacheRelease')
  $mutexHeld = $false
  try {
    try {
      $mutexHeld = $releaseMutex.WaitOne(0)
    }
    catch [System.Threading.AbandonedMutexException] {
      $mutexHeld = $true
    }

    if (-not $mutexHeld) {
      return [pscustomobject]@{
        attempted = $false
        released = $false
        reason = 'Outra janela esta verificando o cache ocioso do ComfyUI.'
        freeGpuMiB = $null
      }
    }

    $queueBefore = Get-ComfyQueueStatus
    if (-not $queueBefore.reachable -or $queueBefore.running -gt 0 -or $queueBefore.pending -gt 0) {
      return [pscustomobject]@{
        attempted = $false
        released = $false
        reason = 'A fila ComfyUI nao esta comprovadamente vazia.'
        freeGpuMiB = $null
      }
    }

    $lastGpu = $null
    for ($sampleIndex = 1; $sampleIndex -le $IdleGpuSampleCount; $sampleIndex++) {
      $lastGpu = Get-GpuSnapshot
      if (-not $lastGpu.available) {
        return [pscustomobject]@{
          attempted = $false
          released = $false
          reason = 'Nao foi possivel comprovar que a GPU esta ociosa.'
          freeGpuMiB = $null
        }
      }
      if ($lastGpu.utilizationPercent -gt $MaximumIdleGpuUtilizationPercent) {
        return [pscustomobject]@{
          attempted = $false
          released = $false
          reason = "GPU ainda ativa: $($lastGpu.utilizationPercent)% de uso."
          freeGpuMiB = $lastGpu.freeGpuMiB
        }
      }
      if ($sampleIndex -lt $IdleGpuSampleCount) {
        Start-Sleep -Seconds $IdleGpuSampleIntervalSec
      }
    }

    if ($lastGpu.freeGpuMiB -ge $MinimumFreeGpuMiB) {
      return [pscustomobject]@{
        attempted = $false
        released = $true
        reason = 'A VRAM ficou livre durante a verificacao ociosa.'
        freeGpuMiB = $lastGpu.freeGpuMiB
      }
    }

    $queueAfter = Get-ComfyQueueStatus
    if (-not $queueAfter.reachable -or $queueAfter.running -gt 0 -or $queueAfter.pending -gt 0) {
      return [pscustomobject]@{
        attempted = $false
        released = $false
        reason = 'A fila ComfyUI mudou durante a verificacao; cache preservado.'
        freeGpuMiB = $lastGpu.freeGpuMiB
      }
    }

    Write-Host 'Liberando somente o cache ocioso do ComfyUI; nenhum trabalho ou processo sera encerrado.' -ForegroundColor Cyan
    $body = @{
      unload_models = $true
      free_memory = $true
    } | ConvertTo-Json -Compress
    Invoke-RestMethod -Uri $ComfyFreeEndpoint -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5 | Out-Null

    $deadline = (Get-Date).AddSeconds($ComfyReleaseTimeoutSec)
    while ((Get-Date) -lt $deadline) {
      $releasedGpu = Get-GpuSnapshot
      if ($releasedGpu.available -and $releasedGpu.freeGpuMiB -ge $MinimumFreeGpuMiB) {
        return [pscustomobject]@{
          attempted = $true
          released = $true
          reason = "Cache ComfyUI liberado; VRAM livre: $($releasedGpu.freeGpuMiB) MiB."
          freeGpuMiB = $releasedGpu.freeGpuMiB
        }
      }
      Start-Sleep -Seconds 1
    }

    $finalGpu = Get-GpuSnapshot
    return [pscustomobject]@{
      attempted = $true
      released = $false
      reason = 'O ComfyUI recebeu o pedido, mas a VRAM minima ainda nao ficou livre.'
      freeGpuMiB = $finalGpu.freeGpuMiB
    }
  }
  catch {
    return [pscustomobject]@{
      attempted = $true
      released = $false
      reason = "Falha ao liberar o cache ocioso do ComfyUI: $($_.Exception.Message)"
      freeGpuMiB = $null
    }
  }
  finally {
    if ($mutexHeld) {
      try { $releaseMutex.ReleaseMutex() } catch {}
    }
    $releaseMutex.Dispose()
  }
}

function Start-QwenAutomatically {
  $startMutex = New-Object System.Threading.Mutex($false, 'Local\PemaraHarness-Qwen38-Yarn524K-Autostart')
  $mutexHeld = $false
  try {
    try {
      $mutexHeld = $startMutex.WaitOne(0)
    }
    catch [System.Threading.AbandonedMutexException] {
      $mutexHeld = $true
    }

    if (-not $mutexHeld) {
      $sharedDeadline = (Get-Date).AddSeconds($QwenStartupTimeoutSec)
      while ((Get-Date) -lt $sharedDeadline) {
        $sharedStatus = Get-QwenStatus
        if ($sharedStatus.ready) {
          return [pscustomobject]@{
            ready = $true
            retryable = $false
            processId = $null
            detail = 'Modelo iniciado por outra janela do Pemara Harness.'
            stdoutPath = $null
            stderrPath = $null
          }
        }
        Start-Sleep -Seconds 1
      }
      return [pscustomobject]@{
        ready = $false
        retryable = $true
        processId = $null
        detail = 'Outra janela ainda possui o lock de inicializacao do Qwen.'
        stdoutPath = $null
        stderrPath = $null
      }
    }

    $statusAfterLock = Get-QwenStatus
    if ($statusAfterLock.ready) {
      return [pscustomobject]@{
        ready = $true
        retryable = $false
        processId = $null
        detail = 'Modelo ja estava pronto apos adquirir o lock.'
        stdoutPath = $null
        stderrPath = $null
      }
    }

    $admissionAfterLock = Get-QwenAdmission
    if (-not $admissionAfterLock.allowed) {
      return [pscustomobject]@{
        ready = $false
        retryable = $true
        processId = $null
        detail = $admissionAfterLock.reason
        stdoutPath = $null
        stderrPath = $null
      }
    }

  $launcherRuntime = Join-Path $projectRoot '.runtime\launcher'
  New-Item -ItemType Directory -Path $launcherRuntime -Force | Out-Null
  $attemptId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([Guid]::NewGuid().ToString('N').Substring(0, 8))
  $stdoutPath = Join-Path $launcherRuntime "qwen-autostart-$attemptId.out.log"
  $stderrPath = Join-Path $launcherRuntime "qwen-autostart-$attemptId.err.log"
  $qwenArgs = @(
    '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
    '-File', $QwenLauncher
  )

  $process = Start-Process -FilePath $powerShell `
    -ArgumentList $qwenArgs `
    -WorkingDirectory (Split-Path -Parent $QwenLauncher) `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -PassThru

  $deadline = (Get-Date).AddSeconds($QwenStartupTimeoutSec)
  while ((Get-Date) -lt $deadline) {
    $status = Get-QwenStatus
    if ($status.ready) {
      return [pscustomobject]@{
        ready = $true
        retryable = $false
        processId = $process.Id
        detail = $null
        stdoutPath = $stdoutPath
        stderrPath = $stderrPath
      }
    }
    # O processo filho e o servidor do modelo têm ciclos de vida independentes:
    # ele pode terminar com um código não-zero depois de disparar o llama-server.
    # A única confirmação confiável é o endpoint responder com o modelo esperado.
    # Portanto, mesmo após a saída do filho, aguardamos o prazo inteiro.
    Start-Sleep -Seconds 1
  }

  $finalStatus = Get-QwenStatus
  if ($finalStatus.ready) {
    return [pscustomobject]@{
      ready = $true
      retryable = $false
      processId = $process.Id
      detail = $null
      stdoutPath = $stdoutPath
      stderrPath = $stderrPath
    }
  }

  $detailLines = @()
  if (Test-Path -LiteralPath $stderrPath) {
    $detailLines += @(Get-Content -LiteralPath $stderrPath -Tail 40 -ErrorAction SilentlyContinue)
  }
  if (Test-Path -LiteralPath $stdoutPath) {
    $detailLines += @(Get-Content -LiteralPath $stdoutPath -Tail 40 -ErrorAction SilentlyContinue)
  }
  $detail = ($detailLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join [Environment]::NewLine
  if ([string]::IsNullOrWhiteSpace($detail)) {
    $detail = "O Qwen nao ficou pronto em ${QwenStartupTimeoutSec}s."
  }

  return [pscustomobject]@{
    ready = $false
    retryable = $detail -match 'VRAM livre insuficiente'
    processId = $process.Id
    detail = $detail
    stdoutPath = $stdoutPath
    stderrPath = $stderrPath
  }
  }
  finally {
    if ($mutexHeld) {
      try { $startMutex.ReleaseMutex() } catch {}
    }
    $startMutex.Dispose()
  }
}

if ($usesLocalQwen) {
  $initialStatus = Get-QwenStatus
  $initialAdmission = Get-QwenAdmission
}
else {
  # A rota remota não consulta fila/VRAM nem tenta iniciar o modelo local.
  $initialStatus = [pscustomobject]@{ ready = $false; reachable = $false; models = @() }
  $initialAdmission = [pscustomobject]@{
    allowed = $true; reason = 'Rota remota: GPU local não consultada.'
    freeGpuMiB = $null; gpuUtilizationPercent = $null; queueReachable = $false
    queueRunning = 0; queuePending = 0
  }
}
$report = [ordered]@{
  launcher = $engineLauncher
  workspace = $workspaceRoot
  profile = 'pemara'
  provider = $ProviderId
  task = $Task
  attachmentsManifest = $AttachmentsManifest
  qwen = [ordered]@{
    endpoint = $QwenEndpoint
    expectedModel = $ExpectedModel
    ready = [bool] $initialStatus.ready
    reachable = [bool] $initialStatus.reachable
    models = @($initialStatus.models)
  }
  safety = [ordered]@{
    autoStartsModel = [bool] $usesLocalQwen
    startsInSeparatePowerShell = $true
    forceGpuEviction = $false
    minimumFreeGpuMiB = $MinimumFreeGpuMiB
    waitsForComfyQueue = $true
    releasesIdleComfyCache = $true
    idleGpuSampleCount = $IdleGpuSampleCount
    maximumIdleGpuUtilizationPercent = $MaximumIdleGpuUtilizationPercent
    admissionAllowed = [bool] $initialAdmission.allowed
    admissionReason = $initialAdmission.reason
    freeGpuMiB = $initialAdmission.freeGpuMiB
    gpuUtilizationPercent = $initialAdmission.gpuUtilizationPercent
    comfyQueueReachable = [bool] $initialAdmission.queueReachable
    comfyQueueRunning = $initialAdmission.queueRunning
    comfyQueuePending = $initialAdmission.queuePending
    safeStartCommand = "& '$QwenLauncher'"
  }
}

if ($DryRun) {
  $report | ConvertTo-Json -Depth 5
  exit 0
}

try { $Host.UI.RawUI.WindowTitle = "Pemara Harness - $ProviderId" } catch {}
$exitAfterTask = $Once -or -not [string]::IsNullOrWhiteSpace($Task)

Write-Host ''
Write-Host 'PEMARA HARNESS' -ForegroundColor Cyan
Write-Host "Workspace : $workspaceRoot"
Write-Host 'Perfil    : pemara'
Write-Host "Rota      : $ProviderId"
Write-Host "Modelo    : $(if ($usesLocalQwen) { $ExpectedModel } else { 'deepseek-chat' })"
Write-Host 'Comandos  : :status  :ajuda  :sair'

$lastAdmissionMessage = $null
$nextAdmissionNotice = [DateTime]::MinValue
$nextComfyReleaseAttempt = [DateTime]::MinValue
while ($true) {
  if ($usesLocalQwen) {
    $status = Get-QwenStatus
    if (-not $status.ready) {
    Write-Host ''
    if ($status.reachable) {
      $visibleModels = if ($status.models.Count -gt 0) { $status.models -join ', ' } else { '(nenhum)' }
      Write-Host 'Qwen respondeu, mas o modelo esperado nao esta carregado.' -ForegroundColor Yellow
      Write-Host "Modelos encontrados: $visibleModels"
      Write-Host 'A porta existente nao sera encerrada ou substituida pelo Harness.'

      if ($Once) { exit 4 }
      $occupiedChoice = Read-Host 'Enter = verificar novamente | :sair = fechar'
      if ($occupiedChoice.Trim().ToLowerInvariant() -eq ':sair') { exit 0 }
      continue
    }

    $admission = Get-QwenAdmission
    if (-not $admission.allowed) {
      $now = Get-Date
      $canReleaseIdleComfyCache = (
        $MinimumFreeGpuMiB -gt 0 -and
        $admission.queueReachable -and
        $admission.queueRunning -eq 0 -and
        $admission.queuePending -eq 0 -and
        $null -ne $admission.freeGpuMiB -and
        $admission.freeGpuMiB -lt $MinimumFreeGpuMiB -and
        $now -ge $nextComfyReleaseAttempt
      )
      if ($canReleaseIdleComfyCache) {
        $cacheRelease = Release-IdleComfyCache
        $nextComfyReleaseAttempt = $now.AddSeconds([Math]::Max(30, $RetryIntervalSec))
        if ($cacheRelease.released) {
          Write-Host $cacheRelease.reason -ForegroundColor Green
          $lastAdmissionMessage = $null
          continue
        }
        if ($cacheRelease.attempted) {
          Write-Host $cacheRelease.reason -ForegroundColor Yellow
        }
      }
      if ($admission.reason -ne $lastAdmissionMessage -or $now -ge $nextAdmissionNotice) {
        Write-Host 'Qwen local esta offline; inicializacao aguardando condicao segura.' -ForegroundColor Yellow
        Write-Host $admission.reason
        Write-Host "Nova verificacao automatica em ${RetryIntervalSec}s. Ctrl+C cancela."
        $lastAdmissionMessage = $admission.reason
        $nextAdmissionNotice = $now.AddSeconds(30)
      }
      if ($Once) { exit 3 }
      Start-Sleep -Seconds $RetryIntervalSec
      continue
    }

    if (-not $admission.queueReachable) {
      Write-Host 'Aviso: a fila ComfyUI nao respondeu; a VRAM livre passou no gate.' -ForegroundColor Yellow
    }
    Write-Host 'Qwen local esta offline. Iniciando Qwen automaticamente em outro PowerShell...' -ForegroundColor Cyan
    Write-Host 'Nenhum processo GPU sera encerrado e o launcher nao usa -Force.'
    $startResult = Start-QwenAutomatically
    if (-not $startResult.ready) {
      if ($startResult.retryable) {
        Write-Host 'A condicao mudou durante a partida; o Harness vai aguardar e tentar novamente.' -ForegroundColor Yellow
        Write-Host $startResult.detail
        if ($Once) { exit 3 }
        Start-Sleep -Seconds $RetryIntervalSec
        continue
      }
      throw "Falha ao iniciar o Qwen automaticamente.`n$($startResult.detail)`nLogs: $($startResult.stdoutPath) | $($startResult.stderrPath)"
    }
    Write-Host "Qwen iniciado pelo launcher filho (PID $($startResult.processId))." -ForegroundColor Green
    continue
    }

    Write-Host ''
    Write-Host 'Qwen pronto.' -ForegroundColor Green
  }
  else {
    Write-Host ''
    Write-Host 'DeepSeek API pronta. Nenhuma GPU local sera iniciada.' -ForegroundColor Green
  }
  if (-not [string]::IsNullOrWhiteSpace($Task)) {
    $currentTask = $Task.Trim()
    $Task = $null
  }
  else {
    $currentTask = (Read-Host 'Descreva a tarefa').Trim()
  }

  switch ($currentTask.ToLowerInvariant()) {
    ':sair' { exit 0 }
    ':status' { continue }
    ':ajuda' {
      Write-Host 'Digite uma tarefa normal para executar na rota selecionada.'
      Write-Host ':status verifica novamente; :sair fecha esta janela.'
      continue
    }
    '' { continue }
  }

  Write-Host ''
  Write-Host 'Executando tarefa...' -ForegroundColor Cyan
  $mediaContextPath = $null
  if (-not [string]::IsNullOrWhiteSpace($AttachmentsManifest)) {
    if (-not $usesLocalQwen) {
      throw 'DeepSeek API neste corte aceita somente texto. Use Qwen local para foto, áudio ou vídeo.'
    }
    foreach ($requiredMediaPath in @($mediaPrepare, $mediaProcessor, $MediaPython, $MediaBridge, $WhisperModel)) {
      if (-not (Test-Path -LiteralPath $requiredMediaPath)) { throw "Componente de mídia ausente: $requiredMediaPath" }
    }
    $mediaContextPath = Join-Path (Split-Path -Parent $AttachmentsManifest) 'media-context.json'
    Write-Host 'Lendo foto, áudio e vídeo localmente...' -ForegroundColor Cyan
    & node $mediaPrepare '--manifest' $AttachmentsManifest '--task-file' $TaskFile '--output' $mediaContextPath '--python' $MediaPython '--processor' $mediaProcessor '--bridge' $MediaBridge '--whisper-model' $WhisperModel '--qwen-url' $QwenApiBase '--qwen-model' $ExpectedModel
    if ($LASTEXITCODE -ne 0) { throw "Falha ao preparar os anexos (codigo $LASTEXITCODE)." }
    Write-Host 'Anexos interpretados e vinculados à tarefa.' -ForegroundColor Green
    $AttachmentsManifest = $null
  }
  $childArgs = @(
    '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
    '-File', $engineLauncher,
    '-Workspace', $workspaceRoot,
    '-ProviderId', $ProviderId
  )
  if ($null -ne $mediaContextPath) { $childArgs += @('-MediaContextPath', $mediaContextPath) }
  if (-not [string]::IsNullOrWhiteSpace($TaskFile)) {
    $childArgs += @('-TaskFile', $TaskFile)
  }
  else {
    $childArgs += $currentTask
  }
  & $powerShell @childArgs
  $taskExitCode = $LASTEXITCODE

  if ($taskExitCode -eq 0) {
    Write-Host 'Tarefa encerrada pelo runtime com codigo 0.' -ForegroundColor Green
  }
  else {
    Write-Host "Runtime encerrado com codigo $taskExitCode. O ledger foi preservado." -ForegroundColor Yellow
  }

  if ($exitAfterTask) { exit $taskExitCode }
  [void](Read-Host 'Pressione Enter para iniciar outra tarefa')
}
