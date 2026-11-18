param(
    [Parameter(Mandatory=$true)][string]$LyricsFile,
    [Parameter(Mandatory=$true)][string]$Style,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$AbcFile,
    [string]$ArLora,
    [string]$NarLora,
    [long]$Seed = 42,
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$runtime = 'D:\PemaraRuntimes\audio-cpp-v0.8.1\bin'
$exe = Get-ChildItem -LiteralPath $runtime -Recurse -File -Filter 'audiocpp_cli.exe' | Select-Object -First 1
if (!$exe) { throw 'O executável audio.cpp ainda não está instalado.' }
$model = 'D:\PemaraModels\workflows_20260920\audio_cpp\Yue2-3B-GGUF'
foreach ($name in @('yue2-3b-q8_0.gguf','yue2-vae-f16.gguf','sidecars/yue2-model-config.json','sidecars/yue2-generation-config.json','sidecars/yue2-qwen.tiktoken','sidecars/yue2-vae-config.json')) {
    if (!(Test-Path -LiteralPath (Join-Path $model $name))) { throw "Modelo incompleto: $name" }
}
$lyrics = Get-Content -LiteralPath $LyricsFile -Raw -Encoding UTF8
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Escolha uma pasta de saída nova para preservar os resultados existentes.' }
$cliArgs = @('--task','gen','--family','yue2','--model',$model,'--backend','cuda','--threads','8',
    '--lyrics',$lyrics,'--request-option',"style=$Style",'--request-option','cot=full',
    '--seed',"$Seed",'--out',(Join-Path $OutputDirectory 'candidate.wav'),'--out-dir',$OutputDirectory,'--log')
foreach ($option in @(@('abc_file',$AbcFile,'--request-option'),@('yue2.ar_lora',$ArLora,'--session-option'),@('yue2.nar_lora',$NarLora,'--session-option'))) {
    if ($option[1]) {
        $resolved = (Resolve-Path -LiteralPath $option[1]).Path
        $cliArgs += @($option[2],"$($option[0])=$resolved")
    }
}
if ($PlanOnly) {
    [pscustomobject]@{Executable=$exe.FullName; Model=$model; Output=$OutputDirectory; Mode='full'; AR=[bool]$ArLora; NAR=[bool]$NarLora}
    return
}
# This launcher is for an explicit local user invocation. Codex uses MCP for ComfyUI.
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$env:PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin;$env:PATH"
& $exe.FullName @cliArgs
if ($LASTEXITCODE -ne 0) { throw "audio.cpp encerrou com código $LASTEXITCODE" }
