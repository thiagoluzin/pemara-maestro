param(
    [Parameter(Mandatory = $true)]
    [string]$SourceProject,

    [Parameter(Mandatory = $true)]
    [string]$DestinationProject,

    [switch]$ReplaceIncompleteDestination,

    [switch]$RemoveVerifiedJunction
)

$ErrorActionPreference = 'Stop'

function Get-NormalizedFullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}

function Assert-PathBelow {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $normalizedPath = Get-NormalizedFullPath -Path $Path
    $normalizedRoot = Get-NormalizedFullPath -Path $Root
    if (-not $normalizedPath.StartsWith($normalizedRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label fora da raiz permitida: $normalizedPath"
    }
    return $normalizedPath
}

function Get-TreeStats {
    param([Parameter(Mandatory = $true)][string]$Root)

    $files = @(Get-ChildItem -LiteralPath $Root -File -Recurse -Force)
    $bytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)
    return [pscustomobject]@{
        Files = $files.Count
        Bytes = $bytes
    }
}

function Remove-VerifiedTarget {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$AllowedRoot,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[object]]$Audit
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $verified = Assert-PathBelow -Path $Path -Root $AllowedRoot -Label 'Alvo de exclusao'
    $item = Get-Item -LiteralPath $verified -Force
    if ($item.PSIsContainer) {
        $files = @(Get-ChildItem -LiteralPath $verified -File -Recurse -Force)
        $bytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)
        $count = $files.Count
    }
    else {
        $bytes = [int64]$item.Length
        $count = 1
    }

    Remove-Item -LiteralPath $verified -Recurse -Force
    $Audit.Add([pscustomobject]@{
        Path = $verified.Substring((Get-NormalizedFullPath -Path $AllowedRoot).Length + 1)
        Files = $count
        Bytes = $bytes
    })
}

$allowedSourceRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos'
$allowedDestinationRoot = 'G:\Backups'
$source = Assert-PathBelow -Path $SourceProject -Root $allowedSourceRoot -Label 'Projeto de origem'
$destination = Assert-PathBelow -Path $DestinationProject -Root $allowedDestinationRoot -Label 'Projeto de destino'

if ($RemoveVerifiedJunction) {
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Juncao de origem ausente: $source"
    }
    if (-not (Test-Path -LiteralPath $destination -PathType Container)) {
        throw "Backup de destino ausente: $destination"
    }
    $junctionItem = Get-Item -LiteralPath $source -Force
    if (-not ($junctionItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "O alvo nao e uma juncao; remocao recusada: $source"
    }
    $junctionTarget = Get-NormalizedFullPath -Path (@($junctionItem.Target)[0])
    if ($junctionTarget -ne $destination) {
        throw "A juncao aponta para destino inesperado: $junctionTarget"
    }
    Remove-Item -LiteralPath $source -Force
    [pscustomobject]@{
        Status = 'PASS_ARCHIVE_OFFLINE_JUNCTION_REMOVED'
        JunctionRemoved = -not (Test-Path -LiteralPath $source)
        BackupStillPresent = Test-Path -LiteralPath $destination -PathType Container
        Destination = $destination
    } | ConvertTo-Json
    exit 0
}

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Projeto de origem ausente: $source"
}
if ((Get-Item -LiteralPath $source -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    throw "A origem ja e um link/juncao; migracao recusada: $source"
}
if (Test-Path -LiteralPath $destination) {
    if (-not $ReplaceIncompleteDestination) {
        throw "O destino ja existe: $destination"
    }
    $existingDestination = Get-Item -LiteralPath $destination -Force
    if ($existingDestination.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Recusa em substituir destino de estagio que e link/juncao: $destination"
    }
    Remove-Item -LiteralPath $destination -Recurse -Force
}

$sourceDrive = Get-PSDrive -Name E
$destinationDrive = Get-PSDrive -Name G
$sourceFreeBefore = [int64]$sourceDrive.Free
$destinationFreeBefore = [int64]$destinationDrive.Free
$sourceStats = Get-TreeStats -Root $source
if ($destinationDrive.Free -lt ($sourceStats.Bytes * 2)) {
    throw "Espaco de seguranca insuficiente no G:. Necessario: $($sourceStats.Bytes * 2); livre: $($destinationDrive.Free)"
}

$destinationParent = Split-Path -Parent $destination
New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
& robocopy.exe $source $destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /NFL /NDL /NJH /NJS /NP
$robocopyExit = $LASTEXITCODE
if ($robocopyExit -gt 7) {
    throw "Robocopy falhou com codigo $robocopyExit"
}

$copiedStats = Get-TreeStats -Root $destination
if ($copiedStats.Files -ne $sourceStats.Files -or $copiedStats.Bytes -ne $sourceStats.Bytes) {
    throw "A copia inicial divergiu. Origem: $($sourceStats.Files) arquivos/$($sourceStats.Bytes) bytes; destino: $($copiedStats.Files)/$($copiedStats.Bytes)."
}

$criticalFiles = @(
    [pscustomobject]@{
        Relative = 'final\candidates\route_r6_heavy_foley_60fps_attempt01\vejito_blue_vs_goku_black_rose_route_r6_heavy_foley_60fps_attempt01.mp4'
        Sha256 = '746a2700237107938e52f6169b90ce9a60999a6d72d9357bcbf2681d6937da58'
    },
    [pscustomobject]@{
        Relative = 'qc\upscaled\take_R6_review_candidate_1920x1080_60fps_83313a436d0f.mp4'
        Sha256 = '8aecbdcf095f571d4f66b9845639a21a02d44236aa12ef096b2ff1bd5c730ef5'
    }
)

foreach ($critical in $criticalFiles) {
    $criticalPath = Join-Path $destination $critical.Relative
    if (-not (Test-Path -LiteralPath $criticalPath -PathType Leaf)) {
        throw "Arquivo critico ausente no destino: $($critical.Relative)"
    }
    $actual = (Get-FileHash -LiteralPath $criticalPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $critical.Sha256) {
        throw "Hash divergente no arquivo critico $($critical.Relative): $actual"
    }
}

$deletionAudit = [System.Collections.Generic.List[object]]::new()
$rejectedTargets = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

$rejectionsPath = Join-Path $destination 'qc\rejections.json'
if (Test-Path -LiteralPath $rejectionsPath -PathType Leaf) {
    $rejections = Get-Content -LiteralPath $rejectionsPath -Raw | ConvertFrom-Json
    foreach ($rejection in @($rejections.items)) {
        if (-not $rejection.output) {
            continue
        }
        $relativeOutput = ([string]$rejection.output).Replace('/', '\')
        if ($relativeOutput -match '^takes\\candidates\\([^\\]+)\\') {
            [void]$rejectedTargets.Add((Join-Path $destination ("takes\candidates\" + $Matches[1])))
        }
        elseif ($relativeOutput -match '^final\\[^\\]+$') {
            [void]$rejectedTargets.Add((Join-Path $destination $relativeOutput))
        }
    }
}

Get-ChildItem -LiteralPath $destination -Filter 'render_manifest.json' -File -Recurse | ForEach-Object {
    try {
        $manifest = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        if (([string]$manifest.status) -match 'REJECTED') {
            [void]$rejectedTargets.Add($_.Directory.FullName)
        }
    }
    catch {
        throw "Manifesto invalido durante classificacao: $($_.FullName)"
    }
}

$explicitRejected = @(
    'archive\route_r1_owner_rejected_20260827_052500',
    'audio\foley_route_r5',
    'final\candidates\route_r5_foley_60fps_attempt01',
    'qc\audio\route_r5_foley_review_waveform_spectrogram.png',
    'qc\final\picture_lock_60s_12frames.jpg',
    'qc\final\route_r5_foley_60fps_attempt01_9frames.jpg',
    'takes\approved',
    'transitions'
)
foreach ($relative in $explicitRejected) {
    [void]$rejectedTargets.Add((Join-Path $destination $relative))
}

$r6MixManifestPath = Join-Path $destination 'audio\foley_route_r6_heavy\mix_attempt01\mix_manifest.json'
if (Test-Path -LiteralPath $r6MixManifestPath -PathType Leaf) {
    $r6Mix = Get-Content -LiteralPath $r6MixManifestPath -Raw | ConvertFrom-Json
    foreach ($chunk in @($r6Mix.chunks)) {
        if ($chunk.old_source) {
            $oldRelative = ([string]$chunk.old_source).Replace($source + '\', '')
            if ($oldRelative -match '^audio\\video_sound\\[^\\]+\\[^\\]+\\') {
                $jobRelative = Split-Path -Parent $oldRelative
                [void]$rejectedTargets.Add((Join-Path $destination $jobRelative))
            }
        }
    }
}

$orderedTargets = @($rejectedTargets) | Sort-Object { $_.Length } -Descending
foreach ($target in $orderedTargets) {
    Remove-VerifiedTarget -Path $target -AllowedRoot $destination -Audit $deletionAudit
}

foreach ($critical in $criticalFiles) {
    $criticalPath = Join-Path $destination $critical.Relative
    $actual = (Get-FileHash -LiteralPath $criticalPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $critical.Sha256) {
        throw "Arquivo critico mudou apos a limpeza: $($critical.Relative)"
    }
}

$ffmpeg = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
if ($ffmpeg) {
    foreach ($critical in $criticalFiles) {
        $criticalPath = Join-Path $destination $critical.Relative
        & $ffmpeg.Source -v error -i $criticalPath -map 0 -f null NUL
        if ($LASTEXITCODE -ne 0) {
            throw "Decode integral falhou: $($critical.Relative)"
        }
    }
}

$manifestPath = Join-Path $destination 'BACKUP_MANIFEST_SHA256.csv'
$manifestRows = Get-ChildItem -LiteralPath $destination -File -Recurse -Force |
    Where-Object { $_.FullName -ne $manifestPath } |
    Sort-Object FullName |
    ForEach-Object {
        [pscustomobject]@{
            RelativePath = $_.FullName.Substring($destination.Length + 1)
            Bytes = [int64]$_.Length
            SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
$manifestRows | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding utf8
$manifestSha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()

$postCleanupStats = Get-TreeStats -Root $destination
$retiredSource = $source + '.nvme_retirement_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$retiredSource = Assert-PathBelow -Path $retiredSource -Root $allowedSourceRoot -Label 'Origem temporaria'
Move-Item -LiteralPath $source -Destination $retiredSource

try {
    New-Item -ItemType Junction -Path $source -Target $destination | Out-Null
    foreach ($critical in $criticalFiles) {
        $throughJunction = Join-Path $source $critical.Relative
        $actual = (Get-FileHash -LiteralPath $throughJunction -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $critical.Sha256) {
            throw "Validacao pela juncao falhou: $($critical.Relative)"
        }
    }
}
catch {
    if (Test-Path -LiteralPath $source) {
        Remove-Item -LiteralPath $source -Force
    }
    Move-Item -LiteralPath $retiredSource -Destination $source
    throw
}

$retiredVerified = Assert-PathBelow -Path $retiredSource -Root $allowedSourceRoot -Label 'Copia antiga no NVMe'
if ((Get-Item -LiteralPath $retiredVerified -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    throw "Recusa em apagar: a copia antiga inesperadamente e um reparse point."
}
Remove-Item -LiteralPath $retiredVerified -Recurse -Force

$sourceFreeAfter = [int64](Get-PSDrive -Name E).Free
$destinationFreeAfter = [int64](Get-PSDrive -Name G).Free
$junction = Get-Item -LiteralPath $source -Force

[pscustomobject]@{
    Status = 'PASS_MIGRATED_AND_REJECTED_MEDIA_REMOVED'
    SourceJunction = $source
    JunctionTarget = @($junction.Target)[0]
    Destination = $destination
    SourceFilesBefore = $sourceStats.Files
    SourceBytesBefore = $sourceStats.Bytes
    BackupFilesAfterCleanup = $postCleanupStats.Files
    BackupBytesAfterCleanup = $postCleanupStats.Bytes
    RejectedTargetsRemoved = $deletionAudit.Count
    RejectedFilesRemoved = [int](($deletionAudit | Measure-Object -Property Files -Sum).Sum)
    RejectedBytesRemoved = [int64](($deletionAudit | Measure-Object -Property Bytes -Sum).Sum)
    NvmeBytesFreed = [int64]($sourceFreeAfter - $sourceFreeBefore)
    BackupDriveBytesUsed = [int64]($destinationFreeBefore - $destinationFreeAfter)
    Manifest = $manifestPath
    ManifestSha256 = $manifestSha256
    ApprovedR6Sha256 = $criticalFiles[0].Sha256
    PendingFhdSha256 = $criticalFiles[1].Sha256
    FullDecodeChecked = [bool]$ffmpeg
} | ConvertTo-Json -Depth 4
