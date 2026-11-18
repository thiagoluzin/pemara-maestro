param(
    [string]$ComfyPath = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI",
    [int]$Port = 8188,
    [string]$ListenHost = "127.0.0.1",
    [string]$Python = "python",
    [string]$ExtraArgs = "--cuda-device 0",
    [switch]$Once,
    [int]$IntervalSeconds = 30,
    [int]$FailureThreshold = 3,
    [int]$BusyGpuMemoryMiB = 2048,
    [int]$BusyGpuUtilizationPercent = 5,
    [int]$StartupTimeoutSeconds = 180
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "logs"
$StartScript = Join-Path $Root "start_comfyui.ps1"
$LogFile = Join-Path $LogDir "comfyui.watchdog.log"
$StateFile = Join-Path $LogDir "comfyui.watchdog.state.json"
$PidFile = Join-Path $LogDir "comfyui.pid"
$HealthUrl = "http://${ListenHost}:$Port/system_stats"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$stamp] $Message"
}

function Get-PortListeners {
    @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Format-PortListeners {
    param($Listeners)
    $listenerList = @($Listeners)
    if ($listenerList.Count -eq 0) {
        return "nenhum listener"
    }

    return (($listenerList | ForEach-Object {
        "$($_.LocalAddress):$($_.LocalPort) pid=$($_.OwningProcess)"
    }) -join ", ")
}

function Test-PortLocalOnly {
    $listeners = @(Get-PortListeners)
    $bad = @($listeners | Where-Object { $_.LocalAddress -in @("0.0.0.0", "::") })
    $good = @($listeners | Where-Object { $_.LocalAddress -eq $ListenHost })

    return @{
        Ok = ($good.Count -gt 0 -and $bad.Count -eq 0)
        GoodCount = $good.Count
        BadCount = $bad.Count
        Listeners = $listeners
    }
}

function Test-Health {
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 8
        $portState = Test-PortLocalOnly
        $isHttpOk = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
        if (-not $portState.Ok) {
            return @{
                Ok = $false
                StatusCode = $response.StatusCode
                Error = "porta nao local-only: $(Format-PortListeners $portState.Listeners)"
            }
        }

        return @{
            Ok = $isHttpOk
            StatusCode = $response.StatusCode
            Error = $null
        }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            try { $statusCode = [int]$_.Exception.Response.StatusCode } catch {}
        }
        return @{
            Ok = $false
            StatusCode = $statusCode
            Error = $_.Exception.Message
        }
    }
}

function Get-WatchdogState {
    if (-not (Test-Path -LiteralPath $StateFile)) {
        return @{ ConsecutiveFailures = 0 }
    }

    try {
        $state = Get-Content -Raw -LiteralPath $StateFile | ConvertFrom-Json
        return @{ ConsecutiveFailures = [Math]::Max(0, [int]$state.ConsecutiveFailures) }
    } catch {
        return @{ ConsecutiveFailures = 0 }
    }
}

function Save-WatchdogState {
    param([int]$ConsecutiveFailures)
    $payload = [ordered]@{
        ConsecutiveFailures = [Math]::Max(0, $ConsecutiveFailures)
        UpdatedAt = (Get-Date).ToString("o")
    }
    $temporary = "$StateFile.tmp"
    $payload | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $StateFile -Force
}

function Get-GpuActivity {
    try {
        $line = & nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if (-not $line) {
            return @{ Known = $false; Busy = $false; MemoryMiB = 0; UtilizationPercent = 0 }
        }
        $parts = @($line -split ',' | ForEach-Object { $_.Trim() })
        $memory = [int]$parts[0]
        $utilization = [int]$parts[1]
        return @{
            Known = $true
            Busy = ($memory -ge $BusyGpuMemoryMiB -or $utilization -ge $BusyGpuUtilizationPercent)
            MemoryMiB = $memory
            UtilizationPercent = $utilization
        }
    } catch {
        return @{ Known = $false; Busy = $false; MemoryMiB = 0; UtilizationPercent = 0 }
    }
}

function Get-TrackedComfyProcess {
    if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) {
        return $null
    }

    $owner = [string](Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    $owner = $owner.Trim()
    if ($owner -notmatch "^\d+$") {
        return $null
    }

    $process = Get-Process -Id ([int]$owner) -ErrorAction SilentlyContinue
    if ($null -eq $process -or $process.ProcessName -notmatch "^python(w)?$") {
        return $null
    }
    return $process
}

function Invoke-Check {
    $health = Test-Health
    if ($health.Ok) {
        $previous = Get-WatchdogState
        if ($previous.ConsecutiveFailures -gt 0) {
            Write-Log "Health recuperado sem restart apos $($previous.ConsecutiveFailures) falha(s)."
        }
        Save-WatchdogState -ConsecutiveFailures 0
        Write-Log "OK local=$HealthUrl"
        return 0
    }

    $state = Get-WatchdogState
    $failures = [int]$state.ConsecutiveFailures + 1
    Save-WatchdogState -ConsecutiveFailures $failures
    $portState = Test-PortLocalOnly
    $gpu = Get-GpuActivity
    $trackedComfy = Get-TrackedComfyProcess

    # A Windows Proactor failure can remove only the HTTP listener while the
    # Comfy worker is still sampling on the GPU. Never kill that live render.
    # Once compute utilization becomes idle, the next watchdog pass may repair
    # the service normally.
    if ($null -ne $trackedComfy -and $gpu.Known -and $gpu.UtilizationPercent -ge $BusyGpuUtilizationPercent) {
        Write-Log "Health falhou ($($health.StatusCode)) $($health.Error), mas ComfyUI pid=$($trackedComfy.Id) ainda computa na GPU (VRAM=$($gpu.MemoryMiB)MiB uso=$($gpu.UtilizationPercent)%). Restart adiado; falha $failures/$FailureThreshold."
        return 0
    }

    if ($portState.GoodCount -gt 0 -and $gpu.Busy) {
        Write-Log "Health falhou ($($health.StatusCode)) $($health.Error), mas ComfyUI escuta em $ListenHost`:$Port e GPU esta ativa (VRAM=$($gpu.MemoryMiB)MiB uso=$($gpu.UtilizationPercent)%). Restart adiado; falha $failures/$FailureThreshold."
        return 0
    }

    if ($portState.GoodCount -gt 0 -and $failures -lt $FailureThreshold) {
        $gpuText = if ($gpu.Known) { "VRAM=$($gpu.MemoryMiB)MiB uso=$($gpu.UtilizationPercent)%" } else { "GPU desconhecida" }
        Write-Log "Health falhou ($($health.StatusCode)) $($health.Error), listener ainda ativo ($gpuText). Restart adiado; falha $failures/$FailureThreshold."
        return 0
    }

    Write-Log "Health falhou ($($health.StatusCode)) $($health.Error). Listener=$(Format-PortListeners $portState.Listeners); falhas=$failures/$FailureThreshold; GPUbusy=$($gpu.Busy). Reinicio autorizado."
    $launcherOutLog = Join-Path $LogDir "comfyui.launcher.out.log"
    $launcherErrLog = Join-Path $LogDir "comfyui.launcher.err.log"
    $launcherArgs = @(
        "-WindowStyle", "Hidden",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$StartScript`"",
        "-ComfyPath", "`"$ComfyPath`"",
        "-Port", "$Port",
        "-ListenHost", "`"$ListenHost`"",
        "-Python", "`"$Python`"",
        "-ExtraArgs", "`"$ExtraArgs`""
    )
    try {
        $launcher = Start-Process `
            -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
            -ArgumentList $launcherArgs `
            -WindowStyle Hidden `
            -RedirectStandardOutput $launcherOutLog `
            -RedirectStandardError $launcherErrLog `
            -PassThru `
            -ErrorAction Stop
        Write-Log "Launcher iniciado em background pid=$($launcher.Id) port=$Port."
    } catch {
        Write-Log "Falha ao iniciar launcher: $($_.Exception.Message)"
        return 1
    }

    $launcherReported = $false
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    do {
        $health = Test-Health
        if ($health.Ok) {
            Save-WatchdogState -ConsecutiveFailures 0
            Write-Log "OK apos restart local=$HealthUrl"
            return 0
        }

        if ($launcher.HasExited -and -not $launcherReported) {
            $launcherReported = $true
            $restartOutput = @()
            foreach ($launcherLog in @($launcherOutLog, $launcherErrLog)) {
                if (Test-Path -LiteralPath $launcherLog) {
                    $restartOutput += @(Get-Content -LiteralPath $launcherLog -ErrorAction SilentlyContinue)
                }
            }
            if ($restartOutput.Count -gt 0) {
                $restartText = (($restartOutput | ForEach-Object { "$_".Trim() }) -join " | ")
                Write-Log "Launcher reportou: $restartText"
            }
            Write-Log "Launcher finalizado com exit=$($launcher.ExitCode)."
            if ($launcher.ExitCode -ne 0) {
                return 1
            }
        }

        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    Write-Log "Ainda indisponivel apos $StartupTimeoutSeconds segundos: $($health.Error)"
    return 1
}

do {
    $code = Invoke-Check
    if ($Once) {
        exit $code
    }
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)
