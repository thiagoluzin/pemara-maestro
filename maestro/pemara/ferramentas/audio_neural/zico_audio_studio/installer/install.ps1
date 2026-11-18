$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Install = Join-Path $env:LOCALAPPDATA 'ZICOAudioStudio'
Write-Host "`nZICO AUDIO STUDIO 1.0 - RTX Studio Installer`n" -ForegroundColor Cyan

function Need($cmd) { return -not (Get-Command $cmd -ErrorAction SilentlyContinue) }
if (Need 'winget') { throw 'Winget ausente. Atualize o App Installer pela Microsoft Store.' }
if (Need 'git') { winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements }
if (Need 'ffmpeg') { winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements }
if (Need 'uv') { powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex" }
$env:Path += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Microsoft\WinGet\Links"

New-Item -ItemType Directory -Force -Path $Install | Out-Null
Copy-Item "$Root\*" $Install -Recurse -Force
Set-Location $Install
uv venv .venv --python 3.11
& "$Install\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "`nPerfil de instalação:" -ForegroundColor Yellow
Write-Host '1 - Essencial (API + mix/master + Chatterbox PT-BR)'
Write-Host '2 - Estúdio completo (inclui Qwen3-TTS, Fish, MMAudio e ACE-Step)'
Write-Host '3 - Núcleo apenas (motores depois)'
$choice = Read-Host 'Escolha 1, 2 ou 3'
if ($choice -eq '1' -or $choice -eq '2') { & "$Install\installer\install-engine.ps1" chatterbox }
if ($choice -eq '2') {
  foreach ($e in @('qwen3','fish','mmaudio','acestep')) {
    try { & "$Install\installer\install-engine.ps1" $e }
    catch { Add-Content "$Install\install-errors.log" "[$(Get-Date -Format o)] $e : $($_.Exception.Message)"; Write-Host "Falha em $e; detalhes em install-errors.log. O restante continuará." -ForegroundColor Yellow }
  }
}
$desktop=[Environment]::GetFolderPath('Desktop')
$ws=New-Object -ComObject WScript.Shell
$sc=$ws.CreateShortcut((Join-Path $desktop 'ZICO Audio Studio.lnk'))
$sc.TargetPath=Join-Path $Install 'INICIAR_ZICO.bat'; $sc.WorkingDirectory=$Install; $sc.Save()
Write-Host "`nInstalado em $Install" -ForegroundColor Green
Write-Host 'Use o atalho ZICO Audio Studio. Modelos são baixados no primeiro uso.'
