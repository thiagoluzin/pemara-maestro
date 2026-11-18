param(
    [switch]$Once
)

$ErrorActionPreference = "Continue"
$BaseDir = "E:\Pemara"
$LojaDir = Join-Path $BaseDir "loja"
$MaestroDir = Join-Path $BaseDir "maestro"
$MaestroRoot = Join-Path $MaestroDir "pemara"
$RadarDir = Join-Path $BaseDir "radar"
$LogDir = Join-Path $BaseDir "logs"
$MaestroLogDir = Join-Path $MaestroRoot "dados\logs"
$LogFile = Join-Path $LogDir "pemara_boot_watchdog.log"

New-Item -ItemType Directory -Force -Path $LogDir, $MaestroLogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Output $line
}

function Resolve-Exe {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

$Python = Resolve-Exe @("C:\Program Files\Python311\python.exe", "python.exe")
$Docker = Resolve-Exe @("docker.exe", "C:\Program Files\Docker\Docker\resources\bin\docker.exe")

function Test-Http {
    param([string]$Url, [int]$TimeoutSec = 5)
    try {
        $res = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        return ($res.StatusCode -ge 200 -and $res.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Test-Docker {
    param([int]$TimeoutSec = 15)

    if (-not $Docker) { return $false }

    $process = $null
    try {
        $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = $Docker
        $startInfo.Arguments = "info"
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $process = [System.Diagnostics.Process]::new()
        $process.StartInfo = $startInfo

        if (-not $process.Start()) {
            Write-Log "ERRO: nao foi possivel iniciar docker info."
            return $false
        }

        if (-not $process.WaitForExit($TimeoutSec * 1000)) {
            $process.Kill()
            $process.WaitForExit()
            Write-Log "AVISO: docker info excedeu ${TimeoutSec}s; tratando o daemon como offline."
            return $false
        }

        return ($process.ExitCode -eq 0)
    } catch {
        Write-Log "AVISO: falha ao verificar Docker: $($_.Exception.Message)"
        return $false
    } finally {
        if ($process) { $process.Dispose() }
    }
}

function Ensure-Docker {
    if (Test-Docker) {
        Write-Log "Docker daemon OK."
        return $true
    }

    $desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktop) {
        Write-Log "Docker daemon offline. Iniciando Docker Desktop."
        Start-Process -FilePath $desktop -WindowStyle Hidden
    } else {
        Write-Log "ERRO: Docker Desktop nao encontrado."
        return $false
    }

    for ($i = 1; $i -le 36; $i++) {
        Start-Sleep -Seconds 5
        if (Test-Docker) {
            Write-Log "Docker daemon OK apos espera ($i/36)."
            return $true
        }
    }

    Write-Log "ERRO: Docker daemon nao respondeu apos espera."
    return $false
}

function Invoke-ComposeUp {
    param([string]$ProjectDir, [string]$Label)
    if (-not (Test-Path (Join-Path $ProjectDir "docker-compose.yml"))) {
        Write-Log "AVISO: compose nao encontrado para $Label em $ProjectDir."
        return $false
    }
    Write-Log "Garantindo $Label via docker compose up -d."
    $out = & $Docker compose -f (Join-Path $ProjectDir "docker-compose.yml") up -d 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERRO: compose $Label falhou: $out"
        return $false
    }
    return $true
}

function Test-PortOpen {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        return [bool]$conn
    } catch {
        return $false
    }
}

function Start-MaestroFrontend {
    if (Test-Http "http://127.0.0.1:9501/" 5) {
        Write-Log "Maestro frontend OK em 9501."
        return $true
    }

    if (-not $Python) {
        Write-Log "ERRO: Python nao encontrado para iniciar MASTER.py."
        return $false
    }

    $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "MASTER\.py" } |
        Select-Object -First 1
    if ($running) {
        Write-Log "MASTER.py estava rodando no PID $($running.ProcessId), mas 9501 nao respondeu. Aguardando antes de relancar."
        Start-Sleep -Seconds 8
        if (Test-Http "http://127.0.0.1:9501/" 5) { return $true }
    }

    $env:PYTHONPATH = $MaestroRoot
    $env:PYTHONUNBUFFERED = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:MAESTRO_FRONTEND_PORT = "9501"
    $env:MAESTRO_STUDIO_PORT = "8029"

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdout = Join-Path $MaestroLogDir "master_watchdog_$stamp.out.log"
    $stderr = Join-Path $MaestroLogDir "master_watchdog_$stamp.err.log"
    Write-Log "Iniciando MASTER.py na porta 9501."
    $proc = Start-Process -FilePath $Python -ArgumentList "MASTER.py" -WorkingDirectory $MaestroRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    for ($i = 1; $i -le 24; $i++) {
        Start-Sleep -Seconds 5
        if (Test-Http "http://127.0.0.1:9501/" 5) {
            Write-Log "Maestro frontend restaurado em 9501. PID $($proc.Id)."
            return $true
        }
        if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
            Write-Log "ERRO: MASTER.py encerrou antes de abrir 9501. Logs: $stdout / $stderr"
            return $false
        }
    }

    Write-Log "ERRO: MASTER.py nao abriu 9501 dentro da janela. Logs: $stdout / $stderr"
    return $false
}

function Ensure-RadarMonitor {
    $radarPy = Join-Path $RadarDir "radar_monitor.py"
    if (-not (Test-Path $radarPy) -or -not $Python) { return }

    $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "radar_monitor\.py" } |
        Select-Object -First 1
    if ($running) {
        Write-Log "Radar Monitor OK. PID $($running.ProcessId)."
        return
    }

    $pidfile = Join-Path $RadarDir "pidfile.lock"
    if (Test-Path $pidfile) {
        $owner = Get-Content -LiteralPath $pidfile -ErrorAction SilentlyContinue | Select-Object -First 1
        $ownerProcess = $null
        if ($owner -match "^\d+$") {
            $ownerProcess = Get-Process -Id ([int]$owner) -ErrorAction SilentlyContinue
        }
        if (-not $ownerProcess) {
            Write-Log "Removendo pidfile orfao do Radar: $owner."
            Remove-Item -LiteralPath $pidfile -Force -ErrorAction SilentlyContinue
        }
    }

    $stdout = Join-Path $LogDir "radar_monitor_watchdog.out.log"
    $stderr = Join-Path $LogDir "radar_monitor_watchdog.err.log"
    Write-Log "Iniciando Radar Monitor em background."
    Start-Process -FilePath $Python -ArgumentList $radarPy -WorkingDirectory $RadarDir -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
}

Write-Log "Rodada do Pemara Boot Watchdog iniciada."

# Maestro uses the native Windows tunnel. Run this before Docker checks,
# which may block while the unrelated container engine is unavailable.
& (Join-Path $RadarDir "maestro_tunnel_guard.ps1")

if (Ensure-Docker) {
    Invoke-ComposeUp -ProjectDir $LojaDir -Label "Loja" | Out-Null
    # Legacy maestro-cloudflared container is disabled; do not revive it.
}

Start-MaestroFrontend | Out-Null
Ensure-RadarMonitor

$lojaOk = Test-Http "http://127.0.0.1:5000/" 5
$maestroOk = Test-Http "http://127.0.0.1:9501/" 5
$publicLojaOk = Test-Http "https://pemaratech.com.br/" 12
$publicMaestroOk = Test-Http "https://maestro.pemaratech.com.br/" 12
Write-Log "Resumo: loja_local=$lojaOk maestro_local=$maestroOk loja_publica=$publicLojaOk maestro_publico=$publicMaestroOk"

if ($Once) { exit 0 }
