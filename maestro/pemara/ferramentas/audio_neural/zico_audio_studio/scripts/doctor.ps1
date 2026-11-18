$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host 'ZICO Audio Studio - Diagnóstico' -ForegroundColor Cyan
foreach($c in @('git','ffmpeg','ffprobe','nvidia-smi','uv')) {
 if(Get-Command $c -ErrorAction SilentlyContinue){Write-Host "[OK] $c" -ForegroundColor Green}else{Write-Host "[FALTA] $c" -ForegroundColor Red}
}
if(Get-Command nvidia-smi -ErrorAction SilentlyContinue){nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader}
$Py=Join-Path $Root '.venv\Scripts\python.exe'
if(Test-Path $Py){& $Py -c "import fastapi,uvicorn; print('[OK] API Python')"}else{Write-Host '[FALTA] ambiente principal' -ForegroundColor Red}
Get-ChildItem (Join-Path $Root 'engines') -Directory -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "[ENGINE] $($_.Name)" }
