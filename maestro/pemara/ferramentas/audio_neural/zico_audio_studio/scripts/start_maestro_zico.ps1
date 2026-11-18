$ErrorActionPreference='Stop'
$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python=Join-Path $Root '.venv\Scripts\python.exe'
if(!(Test-Path -LiteralPath $Python)){throw 'Ambiente ZICO ausente.'}
$listener=Get-NetTCPConnection -LocalPort 8790 -State Listen -ErrorAction SilentlyContinue
if(!$listener){
  Start-Process -FilePath $Python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8790','--app-dir',$Root) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput "$Root\outputs\server.out.log" -RedirectStandardError "$Root\outputs\server.err.log"
}
Write-Host 'Painel ZICO: http://127.0.0.1:8790/api/zico'
