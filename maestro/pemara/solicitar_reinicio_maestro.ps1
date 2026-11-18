[CmdletBinding()]
param(
    [ValidateSet("studio", "frontend", "all")]
    [string]$Componente = "all",
    [ValidateRange(30, 180)]
    [int]$TimeoutSec = 150
)

$ErrorActionPreference = "Stop"
$Root = "E:\Pemara\maestro\pemara"
$FlagsDir = Join-Path $Root "dados\flags"
$LogDir = Join-Path $Root "dados\logs"
$LogFile = Join-Path $LogDir "maestro_operator_restart.log"
$StudioFlag = Join-Path $FlagsDir "studio_restart_requested.flag"
$FrontendFlag = Join-Path $FlagsDir "maestro_frontend_restart_requested.flag"
$RadarScriptFragment = "radar_monitor.py"

New-Item -ItemType Directory -Force -Path $FlagsDir, $LogDir | Out-Null

function Write-OperatorLog {
    param([string]$Message)

    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Output $line
}

function Test-Http {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Test-RadarSupervisor {
    $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match [regex]::Escape($RadarScriptFragment) } |
        Select-Object -First 1
    if ($null -ne $running) {
        return $true
    }

    # Um Radar elevado pode ocultar CommandLine de uma sessao nao elevada.
    # O pidfile do proprio Radar e a verificacao do processo Python preservam
    # a delegacao segura sem exigir que o operador abra outro terminal elevado.
    $RadarPidFile = "E:\Pemara\radar\pidfile.lock"
    if (-not (Test-Path -LiteralPath $RadarPidFile -PathType Leaf)) {
        return $false
    }
    $owner = [string](Get-Content -LiteralPath $RadarPidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $owner = $owner.Trim()
    if ($owner -notmatch "^\d+$") {
        return $false
    }
    $process = Get-Process -Id ([int]$owner) -ErrorAction SilentlyContinue
    return ($null -ne $process -and $process.ProcessName -in @("python", "pythonw"))
}

function Request-Restart {
    param([string]$FlagPath, [string]$Label)

    $request = @(
        "requested_at=$(Get-Date -Format o)",
        "component=$Label",
        "requested_by=maestro_operator_restart"
    ) -join [Environment]::NewLine
    [System.IO.File]::WriteAllText($FlagPath, $request + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Write-OperatorLog "Pedido de reinicio registrado para $Label."
}

try {
    if (-not (Test-RadarSupervisor)) {
        throw "O supervisor administrativo Radar nao esta em execucao. Use INICIAR_MAESTRO.bat e tente novamente."
    }

    $requested = @()
    if ($Componente -in @("studio", "all")) {
        Request-Restart -FlagPath $StudioFlag -Label "Studio"
        $requested += [pscustomobject]@{ Label = "Studio"; Flag = $StudioFlag; Url = "http://127.0.0.1:8029/api/status" }
    }
    if ($Componente -in @("frontend", "all")) {
        Request-Restart -FlagPath $FrontendFlag -Label "Maestro frontend"
        $requested += [pscustomobject]@{ Label = "Maestro frontend"; Flag = $FrontendFlag; Url = "http://127.0.0.1:9501/" }
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $pending = @($requested | Where-Object { Test-Path -LiteralPath $_.Flag -PathType Leaf })
        $unhealthy = @($requested | Where-Object { -not (Test-Http -Url $_.Url) })
        if (-not $pending -and -not $unhealthy) {
            Write-OperatorLog "Reinicio concluido: $($requested.Label -join ', ')."
            exit 0
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    $pendingLabels = @($requested | Where-Object { Test-Path -LiteralPath $_.Flag -PathType Leaf } | ForEach-Object Label)
    $unhealthyLabels = @($requested | Where-Object { -not (Test-Http -Url $_.Url) } | ForEach-Object Label)
    throw "Tempo esgotado. Pendentes: $($pendingLabels -join ', '). Indisponiveis: $($unhealthyLabels -join ', '). Consulte $LogFile."
} catch {
    Write-OperatorLog "FALHA: $($_.Exception.Message)"
    exit 1
}
