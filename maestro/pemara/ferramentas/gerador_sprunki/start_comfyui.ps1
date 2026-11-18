param(
    [string]$ComfyPath = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI",
    [int]$Port = 8188,
    [string]$ListenHost = "127.0.0.1",
    [string]$Python = "python",
    [string]$ExtraArgs = "--cuda-device 0",
    [int]$StartupTimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Main = Join-Path $ComfyPath "main.py"
$LogDir = Join-Path $Root "logs"
$OutLog = Join-Path $LogDir "comfyui.out.log"
$ErrLog = Join-Path $LogDir "comfyui.err.log"
$PidFile = Join-Path $LogDir "comfyui.pid"
$HealthUrl = "http://${ListenHost}:$Port/system_stats"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path (Join-Path $LogDir "comfyui.watchdog.log") -Value "[$stamp] $Message"
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
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
            return $false
        }

        $port = Test-PortLocalOnly
        if (-not $port.Ok) {
            Write-Log "ComfyUI respondeu, mas a porta nao esta local-only: $(Format-PortListeners $port.Listeners)"
            return $false
        }

        return $true
    } catch {
        return $false
    }
}

function Test-RunningApiMatchesProject {
    try {
        $api = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 8
        $argv = @($api.system.argv)
        $mainArg = ($argv | Select-Object -First 1)
        return ($mainArg -and ([IO.Path]::GetFullPath($mainArg) -eq [IO.Path]::GetFullPath($Main)))
    } catch {
        return $false
    }
}

function Stop-ExistingComfy {
    $targets = @()

    $matchingProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match "python" -and
            $_.CommandLine -like "*$ComfyPath*" -and
            $_.CommandLine -like "*main.py*"
        }

    foreach ($proc in $matchingProcesses) {
        $targets += [int]$proc.ProcessId
    }

    $listeners = @(Get-PortListeners)
    $apiMatches = Test-RunningApiMatchesProject
    if ($apiMatches) {
        foreach ($listener in $listeners) {
            if ($listener.OwningProcess) {
                $targets += [int]$listener.OwningProcess
            }
        }
    }

    $targets = @($targets | Sort-Object -Unique)
    foreach ($targetPid in $targets) {
        try {
            Write-Log "Encerrando ComfyUI existente PID $targetPid."
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
        } catch {
            Write-Log "Falha ao encerrar PID ${targetPid}: $($_.Exception.Message)"
        }
    }

    if ($targets.Count -gt 0) {
        Start-Sleep -Seconds 5
    }
}

if (-not (Test-Path -LiteralPath $Main)) {
    Write-Log "Falha: main.py nao encontrado em $Main"
    exit 1
}

if (Test-Health) {
    Write-Log "ComfyUI ja esta saudavel em $HealthUrl"
    exit 0
}

Stop-ExistingComfy

$remainingListeners = @(Get-PortListeners)
if ($remainingListeners.Count -gt 0) {
    Write-Log "Porta $Port ainda ocupada; nao vou iniciar segunda instancia. Listeners: $(Format-PortListeners $remainingListeners)"
    exit 1
}

Write-Log "Iniciando ComfyUI em $ComfyPath em ${ListenHost}:$Port"
$args = @($Main, "--listen", $ListenHost, "--port", [string]$Port)
if ($ExtraArgs) {
    $args += ($ExtraArgs -split " ")
}

$process = Start-Process `
    -FilePath $Python `
    -ArgumentList $args `
    -WorkingDirectory $ComfyPath `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $PidFile -Value $process.Id
Write-Log "Processo iniciado com PID $($process.Id)"

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-Health) {
        Write-Log "ComfyUI ficou saudavel em $HealthUrl"
        exit 0
    }

    if ($process.HasExited) {
        Write-Log "Falha: processo ComfyUI saiu com code $($process.ExitCode). Veja $ErrLog"
        exit 1
    }

    Start-Sleep -Seconds 5
}

Write-Log "Falha: ComfyUI nao respondeu em $StartupTimeoutSeconds segundos. Veja $ErrLog"
exit 1
