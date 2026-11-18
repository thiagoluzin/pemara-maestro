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

try {
    Write-RestartLog "Reinicio administrativo solicitado na porta $Port."
    $ownerPids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($ownerPid in $ownerPids) {
        if ($ownerPid) {
            Write-RestartLog "Parando PID $ownerPid."
            Stop-Process -Id $ownerPid -Force
        }
    }

    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
    }
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
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
    $env:STUDIO_AUTO_RESUME_TAKES = "0"
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
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 5
            if ($null -ne $response.status) {
                $healthy = $true
                break
            }
        } catch {
            # A proxima tentativa registra somente o resultado final.
        }
    }
    if (-not $healthy) {
        throw "Studio iniciou, mas nao ficou saudavel em 20 segundos."
    }
    Write-RestartLog "Studio saudavel em 127.0.0.1:$Port."
    exit 0
} catch {
    Write-RestartLog "FALHA: $($_.Exception.Message)"
    exit 1
}

