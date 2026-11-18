param(
    [string]$ProjectRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_transicoes_h3',
    [string]$CsvSource = (Join-Path $PSScriptRoot 'transition_bridges.csv'),
    [string]$BatchFolder = 'hunyuan_foley_bridges_20260814'
)

$ErrorActionPreference = 'Stop'

$modelRoot = 'G:\Pemara_AI_Models\HunyuanVideo-Foley'
$editorialRoot = Join-Path $projectRoot 'editorial_2s'
$audioRoot = Join-Path $projectRoot ('audio\' + $BatchFolder)
$inputRoot = Join-Path $audioRoot 'inputs'
$outputRoot = Join-Path $audioRoot 'raw_gpu'
$csvRuntime = Join-Path $inputRoot 'transition_bridges.csv'
$runLog = Join-Path $outputRoot 'generation.log'
$negative = 'music, soundtrack, melody, rhythm, drums, vocals, speech, dialogue, announcer, chant, synthesizer, chiptune, retro game sound, arcade bleeps, cartoon, laser, gunfire, weak impact, weightless impact, clipping'

New-Item -ItemType Directory -Force -Path $inputRoot, $outputRoot | Out-Null
if (-not (Test-Path -LiteralPath $CsvSource)) {
    throw "Transition prompt CSV missing: $CsvSource"
}
Copy-Item -LiteralPath $csvSource -Destination $csvRuntime -Force

$bridgeIds = @('B01_02', 'B02_03', 'B03_04', 'B04_05', 'B05_06', 'B06_07', 'B07_08')
foreach ($bridgeId in $bridgeIds) {
    $source = Join-Path $editorialRoot ($bridgeId + '_editorial_2s_720p24.mp4')
    $destination = Join-Path $inputRoot ($bridgeId + '_512x288_24fps.mp4')
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Editorial bridge missing: $source"
    }

    & ffmpeg -hide_banner -loglevel error -y -hwaccel cuda -i $source `
      -an -vf 'scale=512:288:flags=lanczos,fps=24' -frames:v 48 `
      -c:v h264_nvenc -preset p6 -tune hq -cq 18 -b:v 0 -pix_fmt yuv420p $destination
    if ($LASTEXITCODE -ne 0) {
        throw "GPU proxy preparation failed for $bridgeId."
    }
}

$startedAt = Get-Date
"[$($startedAt.ToString('o'))] Starting seven transition bridges on HunyuanVideo-Foley XXL cuda:0; offload disabled." | Set-Content -LiteralPath $runLog -Encoding utf8

$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& docker run --rm --gpus all `
  --env HF_HUB_OFFLINE=1 `
  --env TRANSFORMERS_OFFLINE=1 `
  --mount "type=bind,source=$modelRoot,target=/models,readonly" `
  --mount "type=bind,source=$inputRoot,target=/input,readonly" `
  --mount "type=bind,source=$outputRoot,target=/output" `
  pemara/hunyuanvideo-foley:cuda128 `
  --model_path /models `
  --model_size xxl `
  --device cuda `
  --gpu_id 0 `
  --csv_path /input/transition_bridges.csv `
  --neg_prompt $negative `
  --output_dir /output `
  --audio_length 2 `
  --num_inference_steps 50 2>&1 | Tee-Object -FilePath $runLog -Append
$dockerExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorAction

if ($dockerExitCode -ne 0) {
    throw "HunyuanVideo-Foley bridge batch failed with exit code $dockerExitCode."
}

$finishedAt = Get-Date
"[$($finishedAt.ToString('o'))] Bridge batch completed in $([math]::Round(($finishedAt - $startedAt).TotalSeconds, 1)) seconds." | Add-Content -LiteralPath $runLog -Encoding utf8
Write-Output $outputRoot
