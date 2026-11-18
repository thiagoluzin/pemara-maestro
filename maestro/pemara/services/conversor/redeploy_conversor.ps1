$ErrorActionPreference = "Continue"

$Root = "E:\Pemara\maestro\pemara"
$ServiceDir = Join-Path $Root "services\conversor"
$LogDir = Join-Path $Root "dados\logs"
$OutLog = Join-Path $LogDir "svc_conversor.out.log"
$ErrLog = Join-Path $LogDir "svc_conversor.err.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$conn = Get-NetTCPConnection -LocalPort 8003 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

$python = "C:\Program Files\Python311\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

$env:PYTHONPATH = $Root
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"

Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8003", "--app-dir", $ServiceDir, "--log-level", "warning") `
    -WorkingDirectory $ServiceDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog
