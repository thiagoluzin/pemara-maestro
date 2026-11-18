param(
    [int]$Port = 9501
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "dados\logs"
$ResetLog = Join-Path $LogDir "maestro_frontend_reset.log"
$DashboardRestartFlag = Join-Path $Root "dados\flags\dashboard_restart_requested.flag"
$ReloadDashboard = Test-Path -LiteralPath $DashboardRestartFlag -PathType Leaf
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-ResetLog {
    param([string]$Message)
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" |
        Add-Content -LiteralPath $ResetLog -Encoding UTF8
}

function Test-MaestroFrontend {
    param([int]$FrontendPort)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort/" -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Test-DashboardSensors {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8007/snapshot" -TimeoutSec 5
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Protect-MaestroSecretFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }

    $ownerSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $Path "/inheritance:r" "/grant:r" `
        "*$ownerSid`:(F)" "*S-1-5-18:(F)" "*S-1-5-32-544:(F)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel restringir as permissoes de $Path."
    }
    Write-ResetLog "Permissoes restritas para arquivo sensivel: $Path"
}

function Protect-MaestroPrivateDirectory {
    param([string]$Path)
    New-Item -ItemType Directory -Force -Path $Path | Out-Null

    $ownerSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $Path "/inheritance:r" "/grant:r" `
        "*$ownerSid`:(OI)(CI)(F)" "*S-1-5-18:(OI)(CI)(F)" `
        "*S-1-5-32-544:(OI)(CI)(F)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel restringir as permissoes do diretorio $Path."
    }
    Write-ResetLog "Permissoes privadas aplicadas ao diretorio: $Path"
}

Write-ResetLog "Reinicio solicitado para o stack Maestro com frontend/proxy na porta $Port."

# Ollama no Windows herda este valor quando o usuario entra novamente. O MASTER
# tambem o recebe abaixo para que o listener atual volte somente em loopback.
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11435", "User")

# Por padrao, recarrega somente o frontend/proxy. Uma flag explicita inclui o
# Dashboard; os motores, o Studio, o Sprunki e o Ollama continuam atendendo.
$managedPorts = @($Port)
if ($ReloadDashboard) {
    $managedPorts += 8007
    Write-ResetLog "Flag do Dashboard detectada; a telemetria da porta 8007 tambem sera recarregada."
}
$ownerPids = @()
foreach ($managedPort in $managedPorts) {
    $ownerPids += @(Get-NetTCPConnection -LocalPort $managedPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
}
$ownerPids = @($ownerPids | Select-Object -Unique)

foreach ($ownerPid in $ownerPids) {
    $ownedPorts = @(Get-NetTCPConnection -State Listen -OwningProcess $ownerPid -ErrorAction SilentlyContinue |
        Where-Object { $managedPorts -contains $_.LocalPort } |
        Select-Object -ExpandProperty LocalPort -Unique)
    Write-ResetLog "Encerrando processo gerenciado PID $ownerPid nas portas $($ownedPorts -join ',')."
    Stop-Process -Id $ownerPid -Force -ErrorAction Stop
}

$deadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $deadline) {
    $remaining = @(foreach ($managedPort in $managedPorts) {
        Get-NetTCPConnection -LocalPort $managedPort -State Listen -ErrorAction SilentlyContinue
    })
    if (-not $remaining) { break }
    Start-Sleep -Milliseconds 500
}
$remaining = @(foreach ($managedPort in $managedPorts) {
    Get-NetTCPConnection -LocalPort $managedPort -State Listen -ErrorAction SilentlyContinue
})
if ($remaining) {
    throw "As portas gerenciadas nao foram liberadas: $((@($remaining.LocalPort | Select-Object -Unique) -join ','))."
}

# O reset roda elevado pelo Radar. Alem de corrigir instalacoes antigas, isto
# impede que uma permissao herdada volte a expor credenciais ou sessoes locais.
$cloudflaredDir = Join-Path (Split-Path -Parent $Root) ".cloudflared"
$secretFiles = @(
    (Join-Path $Root ".env"),
    (Join-Path $Root ".env.backup_20260704_nvidia"),
    (Join-Path $Root "dados\auth_sessions.json")
)
$secretFiles += @(Get-ChildItem -LiteralPath $cloudflaredDir -Filter "*.json" -File -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName)
$secretFiles | Select-Object -Unique | ForEach-Object {
    Protect-MaestroSecretFile -Path $_
}
Protect-MaestroPrivateDirectory -Path (Join-Path $Root "dados\studio")

$python = (Get-Command python -ErrorAction Stop).Source
$sprunkiWatchdogInstaller = Join-Path $Root "ferramentas\gerador_sprunki\install_sprunki_watchdog_task.ps1"
if (Test-Path -LiteralPath $sprunkiWatchdogInstaller -PathType Leaf) {
    & $sprunkiWatchdogInstaller -Port 5005 -Python $python `
        -PublicUrl "https://sprunki.pemaratech.com.br/" -RunAsSystem | ForEach-Object {
            Write-ResetLog "Sprunki watchdog: $_"
        }
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar o watchdog 24/7 do Sprunki."
    }
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdout = Join-Path $LogDir "master_frontend_$stamp.out.log"
$stderr = Join-Path $LogDir "master_frontend_$stamp.err.log"

$env:PYTHONPATH = $Root
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:MAESTRO_FRONTEND_PORT = "$Port"
$env:MAESTRO_FRONTEND_ONLY = "1"
$env:MAESTRO_STUDIO_PORT = "8029"
$env:SPRUNKI_HOST = "127.0.0.1"
$env:OLLAMA_HOST = "127.0.0.1:11435"

$process = Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList "MASTER.py" `
    -WorkingDirectory $Root -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Write-ResetLog "Novo MASTER iniciado. PID $($process.Id)."

for ($attempt = 1; $attempt -le 40; $attempt++) {
    Start-Sleep -Seconds 1
    $frontendReady = Test-MaestroFrontend -FrontendPort $Port
    $dashboardReady = -not $ReloadDashboard -or (Test-DashboardSensors)
    if ($frontendReady -and $dashboardReady) {
        if ($ReloadDashboard -and (Test-Path -LiteralPath $DashboardRestartFlag -PathType Leaf)) {
            Remove-Item -LiteralPath $DashboardRestartFlag -Force
            Write-ResetLog "Dashboard recarregado e flag consumida."
        }
        Write-ResetLog "Frontend/proxy saudavel na porta $Port."
        exit 0
    }
    if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
        throw "MASTER encerrou antes de abrir a porta $Port. Consulte $stderr."
    }
}

throw "MASTER nao abriu a porta $Port dentro de 40 segundos. Consulte $stderr."
