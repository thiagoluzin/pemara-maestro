param([Parameter(Mandatory=$true)][ValidateSet('chatterbox','qwen3','fish','mmaudio','acestep')]$Engine)
$ErrorActionPreference='Stop'
$Base=Join-Path $env:LOCALAPPDATA 'ZICOAudioStudio'
$EnvDir=Join-Path $Base "engines\$Engine\.venv"
New-Item -ItemType Directory -Force -Path (Split-Path $EnvDir) | Out-Null
Write-Host "Instalando engine $Engine em ambiente isolado..." -ForegroundColor Cyan
uv venv $EnvDir --python 3.11
$Py=Join-Path $EnvDir 'Scripts\python.exe'
switch ($Engine) {
 'chatterbox' { & $Py -m pip install chatterbox-tts }
 'qwen3' { & $Py -m pip install qwen-tts }
 'fish' { if (!(Test-Path "$Base\engines\fish\repo")) { git clone --depth 1 https://github.com/fishaudio/fish-speech.git "$Base\engines\fish\repo" }; & $Py -m pip install -e "$Base\engines\fish\repo" }
 'mmaudio' { if (!(Test-Path "$Base\engines\mmaudio\repo")) { git clone --depth 1 https://github.com/hkchengrex/MMAudio.git "$Base\engines\mmaudio\repo" }; & $Py -m pip install -e "$Base\engines\mmaudio\repo" }
 'acestep' { if (!(Test-Path "$Base\engines\acestep\repo")) { git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git "$Base\engines\acestep\repo" }; & $Py -m pip install -e "$Base\engines\acestep\repo" }
}
Write-Host "$Engine instalado." -ForegroundColor Green
