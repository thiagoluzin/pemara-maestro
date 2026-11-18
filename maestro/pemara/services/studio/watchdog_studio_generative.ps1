param(
    [int]$Port = 8029,
    [int]$HyperFramesPort = 8032,
    [string]$Python = "python",
    [string]$StudioDir = "E:\Pemara\maestro\pemara\services\studio",
    [switch]$Once
)

$ErrorActionPreference = "Continue"
$BaseDir = "E:\Pemara\maestro\pemara"
$LogDir = Join-Path $BaseDir "dados\logs"
$LogFile = Join-Path $LogDir "studio_generative_watchdog.log"
$RestartRequest = Join-Path $BaseDir "dados\flags\studio_restart_requested.flag"
$HyperFramesDir = Join-Path $BaseDir "ferramentas\video_global_engine\engines\hyperframes"
$HyperFramesCli = Join-Path $HyperFramesDir "node_modules\.bin\hyperframes.cmd"
$HyperFramesProject = Join-Path $HyperFramesDir "projects\maestro-pilot"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $RestartRequest -Parent) | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Output $line
}

function Test-StudioGenerative {
    try {
        $url = "http://127.0.0.1:$Port/api/generative/status"
        $res = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
        return ($res.StatusCode -ge 200 -and $res.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function Test-PortOpen {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1500, $false)
        if ($ok) { $client.EndConnect($iar) }
        $client.Close()
        return $ok
    } catch {
        return $false
    }
}

function Test-HyperFrames {
    try {
        $url = "http://127.0.0.1:$HyperFramesPort/"
        $res = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
        return ($res.StatusCode -ge 200 -and $res.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Test-HyperFramesPortOpen {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect("127.0.0.1", $HyperFramesPort, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1500, $false)
        if ($ok) { $client.EndConnect($iar) }
        $client.Close()
        return $ok
    } catch {
        return $false
    }
}

function Start-HyperFrames {
    if (Test-HyperFramesPortOpen) {
        Write-Log "Porta $HyperFramesPort ocupada sem resposta do HyperFrames. Processo desconhecido preservado."
        return
    }
    if (-not (Test-Path -LiteralPath $HyperFramesCli -PathType Leaf) -or
        -not (Test-Path -LiteralPath $HyperFramesProject -PathType Container)) {
        Write-Log "ERRO: HyperFrames ou projeto maestro-pilot nao encontrado."
        return
    }

    $logOut = Join-Path $LogDir "hyperframes_$HyperFramesPort.out.log"
    $logErr = Join-Path $LogDir "hyperframes_$HyperFramesPort.err.log"
    $args = @(
        "preview", $HyperFramesProject,
        "--port", "$HyperFramesPort",
        "--no-open",
        "--no-browser-gpu"
    )
    Write-Log "Iniciando HyperFrames em 127.0.0.1:$HyperFramesPort."
    Start-Process -FilePath $HyperFramesCli -ArgumentList $args -WorkingDirectory $HyperFramesDir -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr | Out-Null
    Start-Sleep -Seconds 8
    if (Test-HyperFrames) {
        Write-Log "HyperFrames saudavel em $HyperFramesPort."
    } else {
        Write-Log "HyperFrames foi iniciado, mas ainda nao respondeu em $HyperFramesPort."
    }
}

function Start-StudioGenerative {
    if (Test-PortOpen) {
        Write-Log "Porta $Port esta ocupada, mas /api/generative/status nao respondeu. Nao vou derrubar processo desconhecido."
        return
    }

    $env:PYTHONPATH = $BaseDir
    $env:PYTHONUNBUFFERED = "1"
    $env:PYTHONIOENCODING = "utf-8"
    # Perfil legado dependia do Wan, removido por ordem do proprietario.
    $env:STUDIO_ALLOW_PEMARA_ESTUDIO_40ANOS = "0"
    $logOut = Join-Path $LogDir "studio_generative_$Port.out.log"
    $logErr = Join-Path $LogDir "studio_generative_$Port.err.log"
    $args = @(
        "-m", "uvicorn", "main:app",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--app-dir", $StudioDir,
        "--log-level", "warning"
    )

    Write-Log "Iniciando Studio Generative em 127.0.0.1:$Port..."
    Start-Process -FilePath $Python -ArgumentList $args -WorkingDirectory $StudioDir -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr
    Start-Sleep -Seconds 10
    if (Test-StudioGenerative) {
        Write-Log "Studio Generative saudavel em $Port."
    } else {
        Write-Log "Studio Generative foi iniciado, mas ainda nao respondeu em $Port."
    }
}

do {
    if (Test-Path -LiteralPath $RestartRequest -PathType Leaf) {
        # Este watchdog roda com token limitado e nao consegue encerrar o
        # Studio administrativo. A flag pertence ao Radar elevado, que so a
        # remove depois de confirmar o novo PID saudavel.
        Write-Log "Pedido de reinicio aguardando o supervisor administrativo Radar."
    }
    if (Test-StudioGenerative) {
        Write-Log "OK: Studio Generative respondendo em $Port."
    } else {
        Write-Log "Falha: Studio Generative offline em $Port."
        Start-StudioGenerative
    }
    if (Test-HyperFrames) {
        Write-Log "OK: HyperFrames respondendo em $HyperFramesPort."
    } else {
        Write-Log "Falha: HyperFrames offline em $HyperFramesPort."
        Start-HyperFrames
    }
    if ($Once) { break }
    Start-Sleep -Seconds 60
} while ($true)
