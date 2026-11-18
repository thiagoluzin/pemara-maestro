param(
    [string]$BridgeProject = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_transicoes_progressao_v2',
    [string]$OutputFileName = 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd24.mp4'
)

$ErrorActionPreference = 'Stop'

$takeProject = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s'
$bridgeProject = $BridgeProject
$queuePath = Join-Path $takeProject 'take_queue.json'
$bridgeQueuePath = Join-Path $bridgeProject 'take_queue.json'
$bridgeAudioRoot = Join-Path $bridgeProject 'audio\hunyuan_foley_bridges_progressao_approved\deliveries'
$bridgeFhdRoot = Join-Path $bridgeProject 'editorial_2s_fhd_approved'
$deliveryRoot = Join-Path $takeProject 'deliveries'
$masterPath = Join-Path $deliveryRoot $OutputFileName
$probePath = [IO.Path]::ChangeExtension($masterPath, '.ffprobe.json')
$loudnessPath = [IO.Path]::ChangeExtension($masterPath, '.loudness.txt')

New-Item -ItemType Directory -Force -Path $bridgeFhdRoot, $deliveryRoot | Out-Null
$queue = Get-Content -Raw -LiteralPath $queuePath | ConvertFrom-Json
$bridgeQueue = Get-Content -Raw -LiteralPath $bridgeQueuePath | ConvertFrom-Json

$bridgeIds = @('B01_02', 'B02_03', 'B03_04', 'B04_05', 'B05_06', 'B06_07', 'B07_08')
foreach ($bridgeId in $bridgeIds) {
    $bridgeTake = $bridgeQueue.takes | Where-Object { [string]$_.id -eq $bridgeId } | Select-Object -First 1
    if ($null -eq $bridgeTake) { throw "Bridge not found in queue: $bridgeId" }
    $source = [string]$bridgeTake.video.output_active
    $destination = Join-Path $bridgeFhdRoot ($bridgeId + '_editorial_2s_1920x1080_24fps.mp4')
    if (-not (Test-Path -LiteralPath $source)) { throw "Bridge video missing: $source" }

    & ffmpeg -hide_banner -loglevel error -y -hwaccel cuda -i $source `
      -vf 'setpts=PTS*48/124,fps=24,trim=end_frame=48,setpts=N/(24*TB),format=yuv420p' -frames:v 48 `
      -c:v h264_nvenc -preset p6 -tune hq -rc vbr -cq 16 -b:v 0 -an $destination
    if ($LASTEXITCODE -ne 0) { throw "GPU FHD upscale failed for $bridgeId." }
}

$takeAudioRoot = Join-Path $takeProject 'audio\hunyuan_foley_20260814'
$takeAudio = @{
    '01' = Join-Path $takeAudioRoot 'take01_pilot\take01_hunyuan_xxl_ambient_pilot_review.wav'
    '02' = Join-Path $takeAudioRoot 'deliveries\take_02_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
    '03' = Join-Path $takeAudioRoot 'deliveries\take_03_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
    '04' = Join-Path $takeAudioRoot 'deliveries\take_04_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
    '05' = Join-Path $takeAudioRoot 'deliveries\take_05_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
    '06' = Join-Path $takeAudioRoot 'deliveries\take_06_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
    '07' = Join-Path $takeAudioRoot 'deliveries\take_07_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
    '08' = Join-Path $takeAudioRoot 'deliveries\take_08_hunyuan_xxl_ambient_gpu_48k_stereo.wav'
}
$ownerVoice = @{
    '07' = Join-Path $takeProject 'audio\production\take_07_voice_owner_supplied.wav'
    '08' = Join-Path $takeProject 'audio\production\take_08_voice_owner_supplied.wav'
}

$segments = [System.Collections.Generic.List[object]]::new()
function Add-TakeSegment([string]$id, [double]$start, [double]$duration) {
    $take = $queue.takes | Where-Object { [string]$_.id -eq $id } | Select-Object -First 1
    if ($null -eq $take) { throw "Take not found in queue: $id" }
    $segments.Add([pscustomobject]@{
        kind = 'take'; id = $id; video = [string]$take.video.output_active; audio = $takeAudio[$id]
        voice = if ($ownerVoice.ContainsKey($id)) { $ownerVoice[$id] } else { '' }
        start = $start; duration = $duration
    })
}
function Add-BridgeSegment([string]$id) {
    $segments.Add([pscustomobject]@{
        kind = 'bridge'; id = $id
        video = Join-Path $bridgeFhdRoot ($id + '_editorial_2s_1920x1080_24fps.mp4')
        audio = Join-Path $bridgeAudioRoot ($id + '_hunyuan_xxl_heavy_48k_stereo.wav')
        voice = ''; start = 0.0; duration = 2.0
    })
}

Add-TakeSegment '01' 0.0 6.0
Add-BridgeSegment 'B01_02'
for ($takeNumber = 2; $takeNumber -le 7; $takeNumber++) {
    $id = '{0:D2}' -f $takeNumber
    Add-TakeSegment $id 1.0 5.5
    Add-BridgeSegment ('B{0:D2}_{1:D2}' -f $takeNumber, ($takeNumber + 1))
}
Add-TakeSegment '08' 1.0 7.0

$ffmpegArgs = [System.Collections.Generic.List[string]]::new()
$filterParts = [System.Collections.Generic.List[string]]::new()
$concatInputs = [System.Text.StringBuilder]::new()
$inputIndex = 0

for ($segmentIndex = 0; $segmentIndex -lt $segments.Count; $segmentIndex++) {
    $segment = $segments[$segmentIndex]
    foreach ($path in @($segment.video, $segment.audio)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Assembly input missing: $path" }
        $ffmpegArgs.Add('-i'); $ffmpegArgs.Add($path)
    }
    $videoIndex = $inputIndex
    $audioIndex = $inputIndex + 1
    $inputIndex += 2
    $voiceIndex = -1
    if (-not [string]::IsNullOrWhiteSpace($segment.voice)) {
        if (-not (Test-Path -LiteralPath $segment.voice)) { throw "Owner voice missing: $($segment.voice)" }
        $ffmpegArgs.Add('-i'); $ffmpegArgs.Add($segment.voice)
        $voiceIndex = $inputIndex
        $inputIndex += 1
    }

    $start = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.###}', [double]$segment.start)
    $duration = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.###}', [double]$segment.duration)
    $filterParts.Add("[$videoIndex`:v]trim=start=$start`:duration=$duration,setpts=PTS-STARTPTS,fps=24,format=yuv420p[v$segmentIndex]")
    $filterParts.Add("[$audioIndex`:a]atrim=start=$start`:duration=$duration,asetpts=PTS-STARTPTS,aresample=48000:async=1:first_pts=0,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=pad_dur=$duration,atrim=duration=$duration[amb$segmentIndex]")

    if ($voiceIndex -ge 0) {
        $filterParts.Add("[$voiceIndex`:a]atrim=start=$start`:duration=$duration,asetpts=PTS-STARTPTS,aresample=48000:async=1:first_pts=0,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=pad_dur=$duration,atrim=duration=$duration[voicebase$segmentIndex]")
        $filterParts.Add("[voicebase$segmentIndex]asplit=2[voicesc$segmentIndex][voicemix$segmentIndex]")
        $filterParts.Add("[amb$segmentIndex][voicesc$segmentIndex]sidechaincompress=threshold=0.015:ratio=8:attack=5:release=250[duck$segmentIndex]")
        $filterParts.Add("[duck$segmentIndex][voicemix$segmentIndex]amix=inputs=2:duration=longest:normalize=0:weights='0.82 1.18',alimiter=limit=0.89:level=false[a$segmentIndex]")
    } else {
        $filterParts.Add("[amb$segmentIndex]anull[a$segmentIndex]")
    }
    [void]$concatInputs.Append("[v$segmentIndex][a$segmentIndex]")
}

$filterParts.Add("$($concatInputs.ToString())concat=n=$($segments.Count):v=1:a=1[vcat][acat]")
$filterParts.Add('[acat]alimiter=limit=0.89:level=false[aout]')
$filterGraph = $filterParts -join ';'

$ffmpegArgs.Add('-filter_complex'); $ffmpegArgs.Add($filterGraph)
$ffmpegArgs.Add('-map'); $ffmpegArgs.Add('[vcat]')
$ffmpegArgs.Add('-map'); $ffmpegArgs.Add('[aout]')
$ffmpegArgs.Add('-c:v'); $ffmpegArgs.Add('h264_nvenc')
$ffmpegArgs.Add('-preset'); $ffmpegArgs.Add('p6')
$ffmpegArgs.Add('-tune'); $ffmpegArgs.Add('hq')
$ffmpegArgs.Add('-rc'); $ffmpegArgs.Add('vbr')
$ffmpegArgs.Add('-cq'); $ffmpegArgs.Add('16')
$ffmpegArgs.Add('-b:v'); $ffmpegArgs.Add('0')
$ffmpegArgs.Add('-maxrate'); $ffmpegArgs.Add('35M')
$ffmpegArgs.Add('-bufsize'); $ffmpegArgs.Add('70M')
$ffmpegArgs.Add('-pix_fmt'); $ffmpegArgs.Add('yuv420p')
$ffmpegArgs.Add('-c:a'); $ffmpegArgs.Add('aac')
$ffmpegArgs.Add('-b:a'); $ffmpegArgs.Add('320k')
$ffmpegArgs.Add('-ar'); $ffmpegArgs.Add('48000')
$ffmpegArgs.Add('-t'); $ffmpegArgs.Add('60')
$ffmpegArgs.Add('-movflags'); $ffmpegArgs.Add('+faststart')
$ffmpegArgs.Add('-y'); $ffmpegArgs.Add($masterPath)

& ffmpeg -hide_banner -loglevel warning @ffmpegArgs
if ($LASTEXITCODE -ne 0) { throw 'Corrected 60-second master assembly failed.' }

& ffprobe -v error -show_format -show_streams -of json $masterPath | Set-Content -LiteralPath $probePath -Encoding utf8
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& ffmpeg -hide_banner -nostats -i $masterPath -filter_complex 'ebur128=peak=true' -f null NUL 2>&1 | Set-Content -LiteralPath $loudnessPath -Encoding utf8
$analysisExit = $LASTEXITCODE
$ErrorActionPreference = $previousErrorAction
if ($analysisExit -ne 0) { throw 'Master loudness analysis failed.' }

Write-Output $masterPath
