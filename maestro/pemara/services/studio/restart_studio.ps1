param(
    [int]$Port = 8029,
    [string]$Python = "C:\Program Files\Python311\python.exe"
)

$ErrorActionPreference = "Stop"
$BaseDir = "E:\Pemara\maestro\pemara"
$StudioDir = Join-Path $BaseDir "services\studio"
$LogDir = Join-Path $BaseDir "dados\logs"
$RestartLog = Join-Path $LogDir "restart_studio_admin.log"
$StdoutLog = Join-Path $LogDir "studio_generative_$Port.out.log"
$StderrLog = Join-Path $LogDir "studio_generative_$Port.err.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-RestartLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $RestartLog -Value $line -Encoding UTF8
}

function Get-StudioPortOwners {
    param([int]$TargetPort)
    # Some Windows TCP providers return a null State for a live listening
    # socket. Filtering with -State Listen hides it and leaves the old server
    # running. A listener has no remote endpoint; established client sockets
    # must never become restart targets.
    @(Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue |
        Where-Object {
            $_.OwningProcess -gt 0 -and $_.RemotePort -eq 0 -and
            $_.RemoteAddress -in @("0.0.0.0", "::", "127.0.0.1")
        } | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Test-StudioListenerOwner {
    param([int]$LauncherId, [int]$TargetPort)
    # On Windows a venv launcher starts the interpreter as a direct child.
    foreach ($listenerId in (Get-StudioPortOwners -TargetPort $TargetPort)) {
        if ($listenerId -eq $LauncherId) { return $true }
        $listener = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerId" -ErrorAction SilentlyContinue
        if ($listener.ParentProcessId -eq $LauncherId -and $listener.Name -eq 'python.exe') {
            return $true
        }
    }
    return $false
}

try {
    Write-RestartLog "Reinicio administrativo solicitado na porta $Port."
    $MediaPython = $Python
    $RuntimeConfig = Join-Path $BaseDir "sistema\studio-web-runtime.json"
    if (!$PSBoundParameters.ContainsKey('Python') -and (Test-Path -LiteralPath $RuntimeConfig -PathType Leaf)) {
        $config = Get-Content -LiteralPath $RuntimeConfig -Raw | ConvertFrom-Json
        $Python = $config.python
        if (!$Python -or ![IO.Path]::IsPathRooted($Python) -or !(Test-Path -LiteralPath $Python -PathType Leaf)) {
            throw "Python configurado do Studio indisponivel."
        }
        $env:PEMARA_STUDIO_MEDIA_PYTHON = $MediaPython
    }
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $ownerPids = @(Get-StudioPortOwners -TargetPort $Port)
    foreach ($ownerPid in $ownerPids) {
        if ($ownerPid) {
            Write-RestartLog "Parando PID $ownerPid."
            Stop-Process -Id $ownerPid -Force
        }
    }

    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-StudioPortOwners -TargetPort $Port) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
    }
    if (Get-StudioPortOwners -TargetPort $Port) {
        throw "Porta $Port continuou ocupada apos 15 segundos."
    }
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Python nao encontrado: $Python"
    }

    $env:PYTHONPATH = $BaseDir
    $env:PYTHONUNBUFFERED = "1"
    $env:PYTHONIOENCODING = "utf-8"
    # Politica vigente do proprietario: MiniMax H3 e o motor de video ativo.
    # Variaveis legadas de Wan ficam explicitamente desligadas apos sua remocao.
    $env:STUDIO_ENABLE_UNAUTHORIZED_VIDEO_ENGINES = "0"
    $env:STUDIO_ENABLE_WAN_RESERVE = "0"
    $env:STUDIO_ALLOW_PEMARA_ESTUDIO_40ANOS = "0"
    $env:STUDIO_AUTO_RESUME_TAKES = "1"
    $arguments = @(
        "-m", "uvicorn", "main:app",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--app-dir", $StudioDir,
        "--log-level", "warning"
    )
    $process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $StudioDir `
        -WindowStyle Hidden -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -PassThru
    Write-RestartLog "Novo Studio iniciado no PID $($process.Id)."

    $healthy = $false
    $readyDeadline = (Get-Date).AddSeconds(50)
    while ((Get-Date) -lt $readyDeadline) {
        Start-Sleep -Seconds 1
        $process.Refresh()
        if ($process.HasExited) {
            throw "O novo Studio encerrou antes da verificacao de saude. Consulte $StderrLog."
        }
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 5
            if ($null -ne $response.status -and (Test-StudioListenerOwner -LauncherId $process.Id -TargetPort $Port)) {
                $healthy = $true
                break
            }
        } catch {
            # A proxima tentativa registra somente o resultado final.
        }
    }
    if (-not $healthy) {
        throw "Studio iniciou, mas nao ficou saudavel dentro do prazo."
    }
    Write-RestartLog "Studio saudavel em 127.0.0.1:$Port."
    exit 0
} catch {
    Write-RestartLog "FALHA: $($_.Exception.Message)"
    exit 1
}
