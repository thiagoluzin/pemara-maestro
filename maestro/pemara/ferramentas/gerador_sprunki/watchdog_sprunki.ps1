param(
    [int]$Port = 5005,
    [string]$PublicUrl = "",
    [string]$Python = "python",
    [switch]$Once,
    [int]$IntervalSeconds = 30
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "logs"
$StartScript = Join-Path $Root "start_sprunki.ps1"
$LogFile = Join-Path $LogDir "sprunki.watchdog.log"
$LocalHealth = "http://127.0.0.1:$Port/api/health"
$RestartRequest = Join-Path $LogDir "sprunki_restart_requested.flag"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$stamp] $Message"
}

function Test-Url {
    param([string]$Url, [int]$TimeoutSec = 8)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return @{
            Ok = ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
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

function Invoke-Check {
    if (Test-Path -LiteralPath $RestartRequest -PathType Leaf) {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($listener) {
            $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
            $expectedApp = Join-Path $Root "app.py"
            if (-not $process -or $process.Name -notmatch "^python(w)?\.exe$" -or $process.CommandLine -notlike "*$expectedApp*") {
                Write-Log "Reinicio recusado: PID $($listener.OwningProcess) na porta $Port nao corresponde ao app Sprunki esperado."
                return 3
            }
            Write-Log "Reinicio solicitado. Encerrando apenas o Sprunki PID $($listener.OwningProcess)."
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction Stop
            $deadline = (Get-Date).AddSeconds(15)
            do {
                Start-Sleep -Milliseconds 250
                $stillListening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            } while ($stillListening -and (Get-Date) -lt $deadline)
            if ($stillListening) {
                Write-Log "Reinicio falhou: a porta $Port permaneceu ocupada."
                return 3
            }
        }
        Remove-Item -LiteralPath $RestartRequest -Force -ErrorAction Stop
        Write-Log "Pedido de reinicio consumido com seguranca."
    }

    $local = Test-Url -Url $LocalHealth -TimeoutSec 5
    if (-not $local.Ok) {
        Write-Log "Health local falhou ($($local.StatusCode)) $($local.Error). Tentando subir/reiniciar."
        & "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File $StartScript -Port $Port -Python $Python | Out-Null
        $local = Test-Url -Url $LocalHealth -TimeoutSec 5
        if (-not $local.Ok) {
            Write-Log "Ainda indisponivel localmente apos restart: $($local.Error)"
            return 1
        }
    }

    if ($PublicUrl) {
        $public = Test-Url -Url $PublicUrl -TimeoutSec 10
        if (-not $public.Ok) {
            Write-Log "Public URL falhou ($($public.StatusCode)) $($public.Error). Backend local esta ok; verificar cloudflared/DNS/proxy."
            return 2
        }
    }

    Write-Log "OK local=$LocalHealth public=$PublicUrl"
    return 0
}

do {
    $code = Invoke-Check
    if ($Once) {
        exit $code
    }
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)
