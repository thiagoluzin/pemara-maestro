[CmdletBinding()]
param(
    [int]$Port = 8188,
    [string]$RuntimeRoot = 'D:\PemaraRuntimes\ComfyUI-v0.40.0-pemara',
    [string]$Python = 'D:\PemaraRuntimes\comfyui-v0400-py311\Scripts\python.exe',
    [string]$ExpectedComfy = '0.41.0',
    [string]$ExpectedTorch = '2.14.0+cu130',
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath 'E:\Pemara\maestro\pemara\dados\comfy_lifecycle\maintenance.hold') {
    exit 0
}

$baseDir = 'E:\Pemara\maestro\pemara'
$logDir = Join-Path $baseDir 'dados\logs'
$logFile = Join-Path $logDir 'comfyui-v0360-watchdog.log'
$startScript = Join-Path $baseDir 'tools\start_comfy_runtime.ps1'
$expectedMain = [IO.Path]::GetFullPath((Join-Path $RuntimeRoot 'main.py'))
$null = New-Item -ItemType Directory -Path $logDir -Force

function Write-WatchdogLog {
    param([string]$Message)
    Add-Content -LiteralPath $logFile -Encoding utf8 -Value (
        '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    )
}

function Test-ExpectedRuntime {
    try {
        $stats = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 5
        $argv = @($stats.system.argv)
        $actualMain = if ($argv.Count) { [IO.Path]::GetFullPath([string]$argv[0]) } else { '' }
        return (
            $stats.system.comfyui_version -eq $ExpectedComfy -and
            $stats.system.pytorch_version -eq $ExpectedTorch -and
            $stats.devices[0].type -eq 'cuda' -and
            $actualMain.Equals($expectedMain, [StringComparison]::OrdinalIgnoreCase) -and
            -not ($argv -contains '0.0.0.0') -and
            -not ($argv -contains '::')
        )
    } catch {
        return $false
    }
}

try {
    if (Test-ExpectedRuntime) {
        Write-WatchdogLog "PASS runtime $ExpectedComfy / torch $ExpectedTorch em 127.0.0.1:$Port."
        exit 0
    }
    if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
        Write-WatchdogLog "BLOQUEADO porta $Port ocupada por runtime divergente; processo preservado para reinicio administrativo."
        exit 2
    }
    & $startScript -Port $Port -RuntimeRoot $RuntimeRoot -Python $Python `
        -ExpectedComfy $ExpectedComfy -ExpectedTorch $ExpectedTorch | Out-Null
    if (-not (Test-ExpectedRuntime)) {
        throw 'O launcher terminou sem estabelecer o contrato esperado.'
    }
    Write-WatchdogLog "RECUPERADO runtime $ExpectedComfy / torch $ExpectedTorch em 127.0.0.1:$Port."
    exit 0
} catch {
    Write-WatchdogLog "FALHA $($_.Exception.Message)"
    exit 1
}
