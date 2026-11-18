$ErrorActionPreference = 'Stop'

$modelRoot = 'G:\Pemara_AI_Models\HunyuanVideo-Foley'
$projectRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s'
$videoRoot = Join-Path $projectRoot 'audio\hunyuan_foley_20260814\inputs'
$outputRoot = Join-Path $projectRoot 'audio\hunyuan_foley_20260814\remaining_gpu_raw'
$queuePath = Join-Path $projectRoot 'take_queue.json'
$csvSource = Join-Path $PSScriptRoot 'remaining_takes.csv'
$csvRuntime = Join-Path $videoRoot 'remaining_takes.csv'
$runLog = Join-Path $outputRoot 'generation.log'
$negative = 'music, soundtrack, melody, rhythm, drums, vocals, speech, dialogue, announcer, chant, synthesizer, chiptune, retro game sound, arcade bleeps, cartoon, laser, gunfire, weak impact, weightless impact'

New-Item -ItemType Directory -Force -Path $videoRoot, $outputRoot | Out-Null
Copy-Item -LiteralPath $csvSource -Destination $csvRuntime -Force

$queue = Get-Content -LiteralPath $queuePath -Raw | ConvertFrom-Json
foreach ($take in $queue.takes | Where-Object { [int]$_.id -ge 2 }) {
    $takeNumber = [int]$take.id
    $source = [string]$take.video.output_active
    $destination = Join-Path $videoRoot ('take{0:D2}_hunyuan_input_512x288_24fps.mp4' -f $takeNumber)
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Approved FHD source missing for Take $($take.id): $source"
    }
    & ffmpeg -hide_banner -loglevel error -y -i $source -an -vf 'scale=512:288:flags=lanczos,fps=24' -t 8 -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p $destination
    if ($LASTEXITCODE -ne 0) {
        throw "FFmpeg proxy preparation failed for Take $($take.id)."
    }
}

$startedAt = Get-Date
"[$($startedAt.ToString('o'))] Starting HunyuanVideo-Foley XXL batch on cuda:0; offload disabled." | Set-Content -LiteralPath $runLog -Encoding utf8

& docker run --rm --gpus all `
  --env HF_HUB_OFFLINE=1 `
  --env TRANSFORMERS_OFFLINE=1 `
  --mount "type=bind,source=$modelRoot,target=/models,readonly" `
  --mount "type=bind,source=$videoRoot,target=/input,readonly" `
  --mount "type=bind,source=$outputRoot,target=/output" `
  pemara/hunyuanvideo-foley:cuda128 `
  --model_path /models `
  --model_size xxl `
  --device cuda `
  --gpu_id 0 `
  --csv_path /input/remaining_takes.csv `
  --neg_prompt $negative `
  --output_dir /output `
  --audio_length 8 `
  --num_inference_steps 50 2>&1 | Tee-Object -FilePath $runLog -Append

if ($LASTEXITCODE -ne 0) {
    throw "HunyuanVideo-Foley batch failed with exit code $LASTEXITCODE."
}

$finishedAt = Get-Date
"[$($finishedAt.ToString('o'))] Batch completed in $([math]::Round(($finishedAt - $startedAt).TotalSeconds, 1)) seconds." | Add-Content -LiteralPath $runLog -Encoding utf8
