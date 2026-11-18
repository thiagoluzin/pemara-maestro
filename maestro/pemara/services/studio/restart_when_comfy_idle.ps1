param(
    [ValidateRange(1, 720)]
    [int]$MaxWaitMinutes = 720,
    [ValidateRange(2, 12)]
    [int]$StableIdleChecks = 3,
    [ValidateRange(5, 60)]
    [int]$PollSeconds = 10
)

$ErrorActionPreference = "Stop"
$BaseDir = "E:\Pemara\maestro\pemara"
$LogDir = Join-Path $BaseDir "dados\logs"
$LogFile = Join-Path $LogDir "studio_restart_when_comfy_idle.log"
$RestartScript = Join-Path $BaseDir "solicitar_reinicio_maestro.ps1"
$QueueUrl = "http://127.0.0.1:8188/queue"
$JobsPath = Join-Path $BaseDir "dados\studio\generative_jobs.json"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-WatcherLog {
    param([string]$Message)
    "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message |
        Add-Content -LiteralPath $LogFile -Encoding UTF8
}

function Get-ActiveStudioJobs {
    if (-not (Test-Path -LiteralPath $JobsPath -PathType Leaf)) {
        throw "Historico de jobs nao encontrado: $JobsPath"
    }
    $payload = Get-Content -LiteralPath $JobsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $payload.jobs) {
        return @()
    }
    return @(
        $payload.jobs.PSObject.Properties.Value |
            Where-Object { [string]$_.status -in @("queued", "running", "canceling") }
    )
}

$mutex = New-Object System.Threading.Mutex($false, "Local\PemaraMaestroStudioIdleRestart")
if (-not $mutex.WaitOne(0)) {
    Write-WatcherLog "Outro observador de reinicio seguro ja esta ativo; encerrando duplicata."
    exit 0
}

try {
    if (-not (Test-Path -LiteralPath $RestartScript -PathType Leaf)) {
        throw "Solicitador de reinicio nao encontrado: $RestartScript"
    }
    $deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
    $idleChecks = 0
    Write-WatcherLog "Aguardando ComfyUI ficar ocioso para recarregar somente o Studio."

    while ((Get-Date) -lt $deadline) {
        try {
            $queue = Invoke-RestMethod -Uri $QueueUrl -TimeoutSec 5
            $running = @($queue.queue_running).Count
            $pending = @($queue.queue_pending).Count
            $activeJobs = @(Get-ActiveStudioJobs)
            if ($running -eq 0 -and $pending -eq 0 -and $activeJobs.Count -eq 0) {
                $idleChecks++
                Write-WatcherLog "ComfyUI e jobs do Studio ociosos ($idleChecks/$StableIdleChecks)."
                if ($idleChecks -ge $StableIdleChecks) {
                    & $RestartScript -Componente studio -TimeoutSec 180 | ForEach-Object {
                        Write-WatcherLog $_
                    }
                    if ($LASTEXITCODE -ne 0) {
                        throw "O Radar nao concluiu o reinicio do Studio."
                    }
                    Write-WatcherLog "Studio recarregado com seguranca apos a fila ficar ociosa."
                    exit 0
                }
            } else {
                if ($idleChecks -gt 0) {
                    Write-WatcherLog "Nova atividade detectada; estabilidade reiniciada."
                }
                $idleChecks = 0
            }
        } catch {
            $idleChecks = 0
            Write-WatcherLog "Leitura da fila falhou; nenhuma acao tomada: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds $PollSeconds
    }
    Write-WatcherLog "Tempo maximo atingido; Studio preservado sem reinicio forcado."
    exit 2
} catch {
    Write-WatcherLog "FALHA: $($_.Exception.Message)"
    exit 1
} finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
