param(
    [string]$SourceFileName = 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd24.mp4',
    [string]$OutputFileName = 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd60_rife46.mp4',
    [string]$WorkFolderName = 'rife60_20260814_progressao_aprovada'
)

$ErrorActionPreference = 'Stop'

$projectRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s'
$sourceMaster = Join-Path $projectRoot ('deliveries\' + $SourceFileName)
$finalMaster = Join-Path $projectRoot ('deliveries\' + $OutputFileName)
$qcPath = [IO.Path]::ChangeExtension($finalMaster, '.ffprobe.json')
$workRoot = Join-Path $projectRoot ('qc\' + $WorkFolderName)
$rifeRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\tools\bin\rife-ncnn-vulkan-20221029-windows\rife-ncnn-vulkan-20221029-windows'
$rifeExe = Join-Path $rifeRoot 'rife-ncnn-vulkan.exe'
$rifeModel = Join-Path $rifeRoot 'rife-v4.6'
$concatList = Join-Path $workRoot 'segments_60fps.txt'

foreach ($required in @($sourceMaster, $rifeExe, $rifeModel)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required input missing: $required" }
}

$segments = @(
    [pscustomobject]@{ name='01_take01'; start=0;    source=144; target=360 },
    [pscustomobject]@{ name='02_B01_02'; start=144;  source=48;  target=120 },
    [pscustomobject]@{ name='03_take02'; start=192;  source=132; target=330 },
    [pscustomobject]@{ name='04_B02_03'; start=324;  source=48;  target=120 },
    [pscustomobject]@{ name='05_take03'; start=372;  source=132; target=330 },
    [pscustomobject]@{ name='06_B03_04'; start=504;  source=48;  target=120 },
    [pscustomobject]@{ name='07_take04'; start=552;  source=132; target=330 },
    [pscustomobject]@{ name='08_B04_05'; start=684;  source=48;  target=120 },
    [pscustomobject]@{ name='09_take05'; start=732;  source=132; target=330 },
    [pscustomobject]@{ name='10_B05_06'; start=864;  source=48;  target=120 },
    [pscustomobject]@{ name='11_take06'; start=912;  source=132; target=330 },
    [pscustomobject]@{ name='12_B06_07'; start=1044; source=48;  target=120 },
    [pscustomobject]@{ name='13_take07'; start=1092; source=132; target=330 },
    [pscustomobject]@{ name='14_B07_08'; start=1224; source=48;  target=120 },
    [pscustomobject]@{ name='15_take08'; start=1272; source=168; target=420 }
)

if (($segments | Measure-Object source -Sum).Sum -ne 1440) { throw 'Source segment contract must total 1440 frames.' }
if (($segments | Measure-Object target -Sum).Sum -ne 3600) { throw 'RIFE segment contract must total 3600 frames.' }

New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
$workRootFull = [IO.Path]::GetFullPath($workRoot).TrimEnd('\') + '\'
$segmentPaths = [System.Collections.Generic.List[string]]::new()

function Reset-GeneratedFrames([string]$path) {
    $fullPath = [IO.Path]::GetFullPath($path).TrimEnd('\') + '\'
    if (-not $fullPath.StartsWith($workRootFull, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean generated frames outside work root: $fullPath"
    }
    Get-ChildItem -LiteralPath $path -Filter '*.png' -File -ErrorAction SilentlyContinue | Remove-Item -Force
}

foreach ($spec in $segments) {
    $segmentRoot = Join-Path $workRoot $spec.name
    $sourceFrames = Join-Path $segmentRoot '01_source_24fps'
    $rifeFrames = Join-Path $segmentRoot '02_rife46_60fps'
    $segmentVideo = Join-Path $segmentRoot ($spec.name + '_fhd60_nvenc.mp4')
    New-Item -ItemType Directory -Force -Path $sourceFrames, $rifeFrames | Out-Null

    $sourceCount = @(Get-ChildItem -LiteralPath $sourceFrames -Filter '*.png' -File -ErrorAction SilentlyContinue).Count
    if ($sourceCount -ne $spec.source) {
        Reset-GeneratedFrames $sourceFrames
        $endFrame = $spec.start + $spec.source
        $filter = "trim=start_frame=$($spec.start):end_frame=$endFrame,setpts=PTS-STARTPTS"
        & ffmpeg -hide_banner -loglevel error -y -i $sourceMaster -an -vf $filter -fps_mode passthrough `
          -frames:v $spec.source (Join-Path $sourceFrames '%08d.png')
        if ($LASTEXITCODE -ne 0) { throw "Frame extraction failed for $($spec.name)." }
        $sourceCount = @(Get-ChildItem -LiteralPath $sourceFrames -Filter '*.png' -File).Count
        if ($sourceCount -ne $spec.source) {
            throw "$($spec.name) extraction produced $sourceCount frames; expected $($spec.source)."
        }
    }

    $rifeCount = @(Get-ChildItem -LiteralPath $rifeFrames -Filter '*.png' -File -ErrorAction SilentlyContinue).Count
    if ($rifeCount -ne $spec.target) {
        Reset-GeneratedFrames $rifeFrames
        & $rifeExe -i $sourceFrames -o $rifeFrames -m $rifeModel -n $spec.target -g 0 -j '2:4:2' -f '%08d.png'
        if ($LASTEXITCODE -ne 0) { throw "RIFE GPU interpolation failed for $($spec.name)." }
        $rifeCount = @(Get-ChildItem -LiteralPath $rifeFrames -Filter '*.png' -File).Count
        if ($rifeCount -ne $spec.target) {
            throw "$($spec.name) RIFE produced $rifeCount frames; expected $($spec.target)."
        }
    }

    & ffmpeg -hide_banner -loglevel error -y -framerate 60 -start_number 1 -i (Join-Path $rifeFrames '%08d.png') `
      -an -c:v h264_nvenc -preset p6 -tune hq -rc vbr -cq 16 -b:v 0 -maxrate 35M -bufsize 70M `
      -pix_fmt yuv420p -frames:v $spec.target -movflags +faststart $segmentVideo
    if ($LASTEXITCODE -ne 0) { throw "NVENC encoding failed for $($spec.name)." }
    $segmentPaths.Add($segmentVideo)
    Write-Output "RIFE_PASS $($spec.name) $($spec.source)->$($spec.target)"
}

$segmentPaths | ForEach-Object { "file '$($_.Replace("'", "''"))'" } | Set-Content -LiteralPath $concatList -Encoding ascii
$videoOnly = Join-Path $workRoot 'mortal_kombat_60s_transitions_fhd60_rife46_video_only.mp4'
& ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatList -c copy $videoOnly
if ($LASTEXITCODE -ne 0) { throw 'RIFE segment concatenation failed.' }

& ffmpeg -hide_banner -loglevel error -y -i $videoOnly -i $sourceMaster `
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy -t 60 -movflags +faststart $finalMaster
if ($LASTEXITCODE -ne 0) { throw 'Final 60 fps audio mux failed.' }

& ffprobe -v error -count_frames -show_format -show_streams -of json $finalMaster | Set-Content -LiteralPath $qcPath -Encoding utf8
Write-Output $finalMaster
