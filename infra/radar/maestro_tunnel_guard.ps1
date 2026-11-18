param()
$ErrorActionPreference = 'Stop'
$config = 'C:\Users\admin_remoto\.cloudflared\maestro-tunnel.yml'
$exe = 'C:\Users\admin_remoto\AppData\Local\Microsoft\WinGet\Links\cloudflared.exe'
$logs = 'E:\Pemara\logs\maestro_tunnel'
$mutex = [System.Threading.Mutex]::new($false, 'Local\PemaraMaestroTunnelGuard')
$owned = $false
try {
    try { $owned = $mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $owned = $true }
    if (-not $owned) { return }
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    $running = @(Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" | Where-Object {
        $_.CommandLine -and ($_.CommandLine.Replace('\','/').ToLowerInvariant().Contains($config.Replace('\','/').ToLowerInvariant()))
    })
    $origin = $false
    try { $origin = (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:9501/login' -TimeoutSec 5).StatusCode -eq 200 } catch {}
    $action = 'already_running'
    if ($running.Count -eq 0) {
        if (-not (Test-Path -LiteralPath $exe) -or -not (Test-Path -LiteralPath $config)) { throw 'Maestro tunnel executable or config missing.' }
        $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $process = Start-Process -FilePath $exe -ArgumentList ('tunnel --config "{0}" --no-autoupdate run' -f $config) -WindowStyle Hidden -RedirectStandardOutput "$logs\$stamp.stdout.log" -RedirectStandardError "$logs\$stamp.stderr.log" -PassThru
        $running = @($process)
        $action = 'started'
    }
    $ids = @($running | ForEach-Object { if ($_.ProcessId) { $_.ProcessId } else { $_.Id } })
    $status = [ordered]@{ timestamp = (Get-Date).ToUniversalTime().ToString('o'); action = $action; pids = $ids; origin_login_ok = $origin; config = $config; duplicate_detected = ($ids.Count -gt 1); recovery = 'Dedicated Windows task invokes this guard every minute and at admin_remoto logon, independent of Docker. Cloudflared reconnects transient network failures itself.' }
    $status | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$logs\status.json" -Encoding UTF8
    Write-Output ("Maestro tunnel: {0}; PID {1}; origin={2}" -f $action, ($ids -join ','), $origin)
} finally {
    if ($owned) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
