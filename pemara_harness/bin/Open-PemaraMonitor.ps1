[CmdletBinding(PositionalBinding = $false)]
param(
  [ValidateRange(1, 65535)]
  [int] $Port = 3080,
  [string] $ProjectRoot,
  [string] $WorkspaceRoot,
  [ValidateRange(2, 60)]
  [int] $StartupTimeoutSec = 20,
  [switch] $NoBrowser,
  [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  $WorkspaceRoot = Split-Path -Parent $ProjectRoot
}
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$monitorEntry = Join-Path $ProjectRoot 'src\monitor.mjs'
$monitorUrl = "http://127.0.0.1:$Port"
$healthUrl = "$monitorUrl/api/health"
$nodeCommand = Get-Command node -ErrorAction Stop
$nodePath = $nodeCommand.Source

if (-not (Test-Path -LiteralPath $monitorEntry -PathType Leaf)) {
  throw "Monitor entrypoint not found: $monitorEntry"
}

$report = [ordered]@{
  url = $monitorUrl
  projectRoot = $ProjectRoot
  workspaceRoot = $WorkspaceRoot
  entrypoint = $monitorEntry
  node = $nodePath
  loopbackOnly = $true
  readOnly = $false
  taskSubmission = $true
  singleActiveTask = $true
  reusesExistingServer = $true
  serverWindow = 'hidden'
  browserMode = 'edge-app'
}

if ($DryRun) {
  $report | ConvertTo-Json -Depth 4
  exit 0
}

function Test-MonitorReady {
  try {
    $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 2
    return [bool] $response.ok
  }
  catch {
    return $false
  }
}

function Find-Edge {
  $command = Get-Command msedge.exe -ErrorAction SilentlyContinue
  if ($null -ne $command) { return $command.Source }

  $candidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\Application\msedge.exe')
  )
  foreach ($candidate in $candidates) {
    if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
      return $candidate
    }
  }
  return $null
}

$mutex = New-Object System.Threading.Mutex($false, "Local\PemaraHarness-VisualMonitor-$Port")
$mutexHeld = $false
try {
  try {
    $mutexHeld = $mutex.WaitOne([TimeSpan]::FromSeconds(5))
  }
  catch [System.Threading.AbandonedMutexException] {
    $mutexHeld = $true
  }

  if (-not $mutexHeld) {
    throw 'Outra abertura do monitor ainda esta em andamento.'
  }

  if (-not (Test-MonitorReady)) {
    $runtimeRoot = Join-Path $ProjectRoot '.runtime\monitor'
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    $attempt = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdoutPath = Join-Path $runtimeRoot "monitor-$attempt.out.log"
    $stderrPath = Join-Path $runtimeRoot "monitor-$attempt.err.log"
    $nodeArgs = @(
      $monitorEntry,
      '--port', [string] $Port,
      '--root', $ProjectRoot,
      '--workspace', $WorkspaceRoot
    )

    Start-Process -FilePath $nodePath `
      -ArgumentList $nodeArgs `
      -WorkingDirectory $ProjectRoot `
      -WindowStyle Hidden `
      -RedirectStandardOutput $stdoutPath `
      -RedirectStandardError $stderrPath | Out-Null

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
    while ((Get-Date) -lt $deadline -and -not (Test-MonitorReady)) {
      Start-Sleep -Milliseconds 250
    }
    if (-not (Test-MonitorReady)) {
      $detail = ''
      if (Test-Path -LiteralPath $stderrPath) {
        $detail = (Get-Content -LiteralPath $stderrPath -Tail 30 -ErrorAction SilentlyContinue) -join [Environment]::NewLine
      }
      throw "O monitor nao ficou pronto em ${StartupTimeoutSec}s. $detail"
    }
  }
}
finally {
  if ($mutexHeld) {
    try { $mutex.ReleaseMutex() } catch {}
  }
  $mutex.Dispose()
}

if ($NoBrowser) {
  $monitorUrl
  exit 0
}

$edgePath = Find-Edge
if ($null -ne $edgePath) {
  Start-Process -FilePath $edgePath -ArgumentList @("--app=$monitorUrl", '--start-maximized') | Out-Null
}
else {
  Start-Process $monitorUrl | Out-Null
}
