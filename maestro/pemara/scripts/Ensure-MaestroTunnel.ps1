$ErrorActionPreference = 'Stop'

$tunnelId = '940443cd-a1cc-472c-85c7-6f2c572179d8'
$binary = 'C:\Users\admin_remoto\AppData\Local\Microsoft\WinGet\Links\cloudflared.exe'
$config = 'C:\Users\admin_remoto\.cloudflared\maestro-tunnel.yml'
$logDirectory = 'E:\Pemara\logs\cloudflared'

if (-not (Test-Path -LiteralPath $binary)) {
    throw "cloudflared nao encontrado: $binary"
}
if (-not (Test-Path -LiteralPath $config)) {
    throw "Configuracao do tunel Maestro ausente: $config"
}

$alreadyConnected = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -ieq 'cloudflared.exe' -and
        $_.CommandLine -match [regex]::Escape('maestro-tunnel.yml')
    } |
    Select-Object -First 1
if ($alreadyConnected) {
    exit 0
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Start-Process -FilePath $binary \
    -ArgumentList @('--config', $config, 'tunnel', 'run') \
    -WindowStyle Hidden \
    -RedirectStandardOutput (Join-Path $logDirectory 'maestro-tunnel.stdout.log') \
    -RedirectStandardError (Join-Path $logDirectory 'maestro-tunnel.stderr.log')
