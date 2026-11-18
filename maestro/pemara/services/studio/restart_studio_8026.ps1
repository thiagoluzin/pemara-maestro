param(
    [int]$Port = 8027
)

$ErrorActionPreference = "Continue"
$BaseDir = "E:\Pemara\maestro\pemara"
$StudioDir = Join-Path $BaseDir "services\studio"
$LogDir = Join-Path $BaseDir "dados\logs"
$LogFile = Join-Path $LogDir "restart_studio_current.log"
$Watchdog = Join-Path $StudioDir "watchdog_studio_generative.ps1"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Output $line
}

Write-Log "Restart solicitado para Studio na porta $Port."

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$ownerPids = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($ownerPid in $ownerPids) {
    if (-not $ownerPid) { continue }
    try {
        Write-Log "Parando PID $ownerPid dono da porta $Port."
        Stop-Process -Id $ownerPid -Force -ErrorAction Stop
    } catch {
        Write-Log "Falha ao parar PID ${ownerPid}: $($_.Exception.Message)"
    }
}

Start-Sleep -Seconds 3

$still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Log "Porta $Port ainda ocupada. Abortando start para nao duplicar servico."
    exit 2
}

Write-Log "Porta $Port livre. Subindo watchdog do Studio."
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File $Watchdog -Port $Port -Once
Start-Sleep -Seconds 3

try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/generative/status" -TimeoutSec 12
    $hasAudio = $null -ne $res.providers
    Write-Log "Status final ok=$($res.ok) comfy=$($res.comfy_online) audio_providers=$hasAudio."
} catch {
    Write-Log "Falha ao validar Studio: $($_.Exception.Message)"
    exit 3
}
