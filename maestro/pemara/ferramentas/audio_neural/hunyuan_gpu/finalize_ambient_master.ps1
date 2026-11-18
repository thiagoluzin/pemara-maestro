$ErrorActionPreference = 'Stop'

$projectRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s'
$queuePath = Join-Path $projectRoot 'take_queue.json'
$audioRoot = Join-Path $projectRoot 'audio\hunyuan_foley_20260814'
$rawRoot = Join-Path $audioRoot 'remaining_gpu_raw'
$deliveryRoot = Join-Path $audioRoot 'deliveries'
$masterRoot = Join-Path $projectRoot 'deliveries'
$masterPath = Join-Path $masterRoot 'mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd.mp4'
$masterQcPath = Join-Path $masterRoot 'mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd_ffprobe.json'
$masterLoudnessPath = Join-Path $masterRoot 'mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd_loudness.txt'

New-Item -ItemType Directory -Force -Path $deliveryRoot, $masterRoot | Out-Null
$queue = Get-Content -LiteralPath $queuePath -Raw | ConvertFrom-Json

$audioFiles = [System.Collections.Generic.List[string]]::new()
$reviewVideos = [System.Collections.Generic.List[string]]::new()

$pilotAudio = Join-Path $audioRoot 'take01_pilot\take01_hunyuan_xxl_ambient_pilot_review.wav'
$pilotReview = Join-Path $audioRoot 'take01_pilot\take01_hunyuan_xxl_ambient_pilot_review_fhd.mp4'
if (-not (Test-Path -LiteralPath $pilotAudio) -or -not (Test-Path -LiteralPath $pilotReview)) {
    throw 'Approved Take 01 Hunyuan pilot is missing.'
}
$audioFiles.Add($pilotAudio)
$reviewVideos.Add($pilotReview)

for ($takeNumber = 2; $takeNumber -le 8; $takeNumber++) {
    $rawIndex = $takeNumber - 2
    $rawAudio = Join-Path $rawRoot ('{0:D4}.wav' -f $rawIndex)
    $deliveryAudio = Join-Path $deliveryRoot ('take_{0:D2}_hunyuan_xxl_ambient_gpu_48k_stereo.wav' -f $takeNumber)
    $reviewVideo = Join-Path $deliveryRoot ('take_{0:D2}_hunyuan_xxl_ambient_gpu_review_fhd.mp4' -f $takeNumber)
    $sourceVideo = [string]$queue.takes[$takeNumber - 1].video.output_active

    if (-not (Test-Path -LiteralPath $rawAudio)) {
        throw "Raw Hunyuan audio missing for Take ${takeNumber}: $rawAudio"
    }
    if (-not (Test-Path -LiteralPath $sourceVideo)) {
        throw "Approved FHD video missing for Take ${takeNumber}: $sourceVideo"
    }

    & ffmpeg -hide_banner -loglevel error -y -i $rawAudio `
      -af 'loudnorm=I=-16:LRA=11:TP=-2,apad=pad_dur=8,atrim=0:8' `
      -ac 2 -ar 48000 -c:a pcm_s24le $deliveryAudio
    if ($LASTEXITCODE -ne 0) { throw "Audio delivery failed for Take $takeNumber." }

    & ffmpeg -hide_banner -loglevel error -y -i $sourceVideo -i $deliveryAudio `
      -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 320k -ar 48000 -t 8 -movflags +faststart $reviewVideo
    if ($LASTEXITCODE -ne 0) { throw "FHD review mux failed for Take $takeNumber." }

    $audioFiles.Add($deliveryAudio)
    $reviewVideos.Add($reviewVideo)
}

$ffmpegArgs = [System.Collections.Generic.List[string]]::new()
for ($i = 0; $i -lt 8; $i++) {
    $sourceVideo = [string]$queue.takes[$i].video.output_active
    $ffmpegArgs.Add('-i')
    $ffmpegArgs.Add($sourceVideo)
    $ffmpegArgs.Add('-i')
    $ffmpegArgs.Add($audioFiles[$i])
}

$filterParts = [System.Collections.Generic.List[string]]::new()
for ($i = 0; $i -lt 8; $i++) {
    $videoInput = $i * 2
    $audioInput = $videoInput + 1
    $filterParts.Add("[$videoInput`:v]trim=duration=7.5,setpts=PTS-STARTPTS[v$i]")
    $filterParts.Add("[$audioInput`:a]atrim=duration=7.5,asetpts=PTS-STARTPTS[a$i]")
}
$concatInputs = (0..7 | ForEach-Object { "[v$_][a$_]" }) -join ''
$filterParts.Add("${concatInputs}concat=n=8:v=1:a=1[vout][aout]")
$filterGraph = $filterParts -join ';'

$ffmpegArgs.Add('-filter_complex')
$ffmpegArgs.Add($filterGraph)
$ffmpegArgs.Add('-map')
$ffmpegArgs.Add('[vout]')
$ffmpegArgs.Add('-map')
$ffmpegArgs.Add('[aout]')
$ffmpegArgs.Add('-c:v')
$ffmpegArgs.Add('h264_nvenc')
$ffmpegArgs.Add('-preset')
$ffmpegArgs.Add('p6')
$ffmpegArgs.Add('-tune')
$ffmpegArgs.Add('hq')
$ffmpegArgs.Add('-rc')
$ffmpegArgs.Add('vbr')
$ffmpegArgs.Add('-cq')
$ffmpegArgs.Add('16')
$ffmpegArgs.Add('-b:v')
$ffmpegArgs.Add('0')
$ffmpegArgs.Add('-maxrate')
$ffmpegArgs.Add('35M')
$ffmpegArgs.Add('-bufsize')
$ffmpegArgs.Add('70M')
$ffmpegArgs.Add('-pix_fmt')
$ffmpegArgs.Add('yuv420p')
$ffmpegArgs.Add('-c:a')
$ffmpegArgs.Add('aac')
$ffmpegArgs.Add('-b:a')
$ffmpegArgs.Add('320k')
$ffmpegArgs.Add('-ar')
$ffmpegArgs.Add('48000')
$ffmpegArgs.Add('-t')
$ffmpegArgs.Add('60')
$ffmpegArgs.Add('-movflags')
$ffmpegArgs.Add('+faststart')
$ffmpegArgs.Add('-y')
$ffmpegArgs.Add($masterPath)

& ffmpeg -hide_banner -loglevel warning @ffmpegArgs
if ($LASTEXITCODE -ne 0) { throw 'Final 60-second ambient master assembly failed.' }

& ffprobe -v error -show_format -show_streams -of json $masterPath | Set-Content -LiteralPath $masterQcPath -Encoding utf8
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& ffmpeg -hide_banner -nostats -i $masterPath -filter_complex 'ebur128=peak=true' -f null NUL 2>&1 | Set-Content -LiteralPath $masterLoudnessPath -Encoding utf8
$loudnessExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorAction
if ($loudnessExitCode -ne 0) { throw 'Final loudness analysis failed.' }

$deliveries = for ($takeNumber = 1; $takeNumber -le 8; $takeNumber++) {
    [pscustomobject]@{
        take = ('{0:D2}' -f $takeNumber)
        engine = 'Tencent HunyuanVideo-Foley XXL'
        device = 'cuda:0 NVIDIA GeForce RTX 5090'
        offload = $false
        audio = $audioFiles[$takeNumber - 1]
        review_video = $reviewVideos[$takeNumber - 1]
        duration_seconds = 8.0
        sample_rate_hz = 48000
        channels = 2
        status = if ($takeNumber -eq 1) { 'owner_approved_pilot' } else { 'generated_pending_human_listening' }
    }
}
$deliveries | Export-Csv -LiteralPath (Join-Path $deliveryRoot 'hunyuan_xxl_gpu_audio_manifest.csv') -NoTypeInformation -Encoding utf8

Write-Output $masterPath
