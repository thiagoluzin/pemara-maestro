$ErrorActionPreference = 'Stop'

$projectRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s'
$queuePath = Join-Path $projectRoot 'take_queue.json'
$sourceMaster = Join-Path $projectRoot 'deliveries\mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd.mp4'
$finalMaster = Join-Path $projectRoot 'deliveries\mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd60_rife46.mp4'
$qcPath = Join-Path $projectRoot 'deliveries\mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd60_rife46_ffprobe.json'
$workRoot = Join-Path $projectRoot 'qc\rife60_20260814_ambient_master'
$rifeRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\tools\bin\rife-ncnn-vulkan-20221029-windows\rife-ncnn-vulkan-20221029-windows'
$rifeExe = Join-Path $rifeRoot 'rife-ncnn-vulkan.exe'
$rifeModel = Join-Path $rifeRoot 'rife-v4.6'
$concatList = Join-Path $workRoot 'segments_60fps.txt'

foreach ($required in @($queuePath, $sourceMaster, $rifeExe, $rifeModel)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required input missing: $required" }
}

New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
$queue = Get-Content -LiteralPath $queuePath -Raw | ConvertFrom-Json
$segmentPaths = [System.Collections.Generic.List[string]]::new()

for ($takeNumber = 1; $takeNumber -le 8; $takeNumber++) {
    $takeId = '{0:D2}' -f $takeNumber
    $takeRoot = Join-Path $workRoot "take_$takeId"
    $sourceFrames = Join-Path $takeRoot '01_source_24fps'
    $rifeFrames = Join-Path $takeRoot '02_rife46_60fps'
    $segment = Join-Path $takeRoot "take_${takeId}_fhd60_nvenc.mp4"
    $sourceVideo = [string]$queue.takes[$takeNumber - 1].video.output_active

    if (-not (Test-Path -LiteralPath $sourceVideo)) { throw "Approved source missing for Take ${takeNumber}: $sourceVideo" }
    New-Item -ItemType Directory -Force -Path $sourceFrames, $rifeFrames | Out-Null

    $sourceCount = @(Get-ChildItem -LiteralPath $sourceFrames -Filter '*.png' -File -ErrorAction SilentlyContinue).Count
    if ($sourceCount -ne 180) {
        & ffmpeg -hide_banner -loglevel error -y -i $sourceVideo -an -vf 'fps=24' -frames:v 180 (Join-Path $sourceFrames '%08d.png')
        if ($LASTEXITCODE -ne 0) { throw "Frame extraction failed for Take $takeNumber." }
        $sourceCount = @(Get-ChildItem -LiteralPath $sourceFrames -Filter '*.png' -File).Count
        if ($sourceCount -ne 180) { throw "Take $takeNumber extraction produced $sourceCount frames, expected 180." }
    }

    $rifeCount = @(Get-ChildItem -LiteralPath $rifeFrames -Filter '*.png' -File -ErrorAction SilentlyContinue).Count
    if ($rifeCount -ne 450) {
        & $rifeExe -i $sourceFrames -o $rifeFrames -m $rifeModel -n 450 -g 0 -j '2:4:2' -f '%08d.png'
        if ($LASTEXITCODE -ne 0) { throw "RIFE GPU interpolation failed for Take $takeNumber." }
        $rifeCount = @(Get-ChildItem -LiteralPath $rifeFrames -Filter '*.png' -File).Count
        if ($rifeCount -ne 450) { throw "Take $takeNumber RIFE produced $rifeCount frames, expected 450." }
    }

    & ffmpeg -hide_banner -loglevel error -y -framerate 60 -start_number 1 -i (Join-Path $rifeFrames '%08d.png') `
      -an -c:v h264_nvenc -preset p6 -tune hq -rc vbr -cq 16 -b:v 0 -maxrate 35M -bufsize 70M `
      -pix_fmt yuv420p -frames:v 450 -movflags +faststart $segment
    if ($LASTEXITCODE -ne 0) { throw "NVENC segment encoding failed for Take $takeNumber." }
    $segmentPaths.Add($segment)
}

$segmentPaths | ForEach-Object { "file '$($_.Replace("'", "''"))'" } | Set-Content -LiteralPath $concatList -Encoding ascii
$videoOnly = Join-Path $workRoot 'mortal_kombat_60s_fhd60_rife46_video_only.mp4'
& ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatList -c copy $videoOnly
if ($LASTEXITCODE -ne 0) { throw 'Lossless segment concatenation failed.' }

& ffmpeg -hide_banner -loglevel error -y -i $videoOnly -i $sourceMaster `
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy -t 60 -movflags +faststart $finalMaster
if ($LASTEXITCODE -ne 0) { throw 'Final 60 fps audio mux failed.' }

& ffprobe -v error -count_frames -show_format -show_streams -of json $finalMaster | Set-Content -LiteralPath $qcPath -Encoding utf8
Write-Output $finalMaster
