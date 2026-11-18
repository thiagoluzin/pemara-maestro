$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Py=Join-Path $Root '.venv\Scripts\python.exe'
if (!(Test-Path $Py)) { Write-Host 'Execute INSTALAR_ZICO.bat primeiro.'; pause; exit 1 }
Start-Process 'http://127.0.0.1:8790/docs'
& $Py -m uvicorn app.main:app --host 127.0.0.1 --port 8790 --app-dir $Root
