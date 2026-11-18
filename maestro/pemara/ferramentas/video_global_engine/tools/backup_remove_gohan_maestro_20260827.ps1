[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectId = 'gohan_ssj2_android16_cell_6x10s_liveaction_v1'
$ProjectsRoot = [IO.Path]::GetFullPath('E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos').TrimEnd('\')
$Source = [IO.Path]::GetFullPath((Join-Path $ProjectsRoot $ProjectId)).TrimEnd('\')
$ArchiveRoot = [IO.Path]::GetFullPath('G:\Takes finalizados').TrimEnd('\')
$Destination = [IO.Path]::GetFullPath((Join-Path $ArchiveRoot $ProjectId)).TrimEnd('\')
$ReportRoot = Join-Path $ArchiveRoot '_cleanup_reports'
$RunStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$ExternalReport = Join-Path $ReportRoot ("MAESTRO_GOHAN_BACKUP_REMOVE_{0}.json" -f $RunStamp)
$RobocopyLog = Join-Path $ReportRoot ("MAESTRO_GOHAN_ROBOCOPY_{0}.log" -f $RunStamp)
$EasyExport = 'E:\Pemara\GOHAN_SSJ2_VIDEO_COMPLETO_FHD60_V5.mp4'
$ExpectedFinalSha256 = '09F5938534D58C2D2648B36CAF93282EF6CC2F2A0335951F1C34BC6265700134'
$StudioCatalogUri = 'http://127.0.0.1:8029/api/video-projects'
$ComfyQueueUri = 'http://127.0.0.1:8188/queue'

function Get-CatalogItems {
    $response = Invoke-RestMethod -Uri $StudioCatalogUri -Method Get -TimeoutSec 15
    if ($null -eq $response.data) {
        throw 'A API do Maestro não retornou o campo data.'
    }
    return @($response.data)
}

function Get-QueueSnapshot {
    $response = Invoke-RestMethod -Uri $ComfyQueueUri -Method Get -TimeoutSec 10
    $raw = $response | ConvertTo-Json -Depth 30 -Compress
    return [PSCustomObject]@{
        Running = @($response.queue_running).Count
        Pending = @($response.queue_pending).Count
        ContainsProject = $raw.Contains($ProjectId, [StringComparison]::OrdinalIgnoreCase)
    }
}

function Get-ArchiveInventory {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $files = @(Get-ChildItem -LiteralPath $rootPath -Recurse -File -Force | Sort-Object FullName)
    $inventory = [Collections.Generic.List[object]]::new()
    $index = 0

    foreach ($file in $files) {
        $index++
        $relative = $file.FullName.Substring($rootPath.Length).TrimStart('\').Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $inventory.Add([PSCustomObject]@{
            RelativePath = $relative
            Length = [Int64]$file.Length
            SHA256 = $hash
        })
        if (($index % 250) -eq 0 -or $index -eq $files.Count) {
            [Console]::WriteLine("HASH_{0}={1}/{2}", $Label, $index, $files.Count)
        }
    }

    return @($inventory)
}

function Get-InventoryBytes {
    param([Parameter(Mandatory = $true)][object[]]$Inventory)
    if ($Inventory.Count -eq 0) { return [Int64]0 }
    return [Int64](($Inventory | Measure-Object -Property Length -Sum).Sum)
}

function Get-InventorySignature {
    param([Parameter(Mandatory = $true)][object[]]$Inventory)
    return @($Inventory | ForEach-Object {
        '{0}|{1}|{2}' -f $_.RelativePath, $_.Length, $_.SHA256
    })
}

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Projeto de origem não existe: $Source"
}
if ([IO.Directory]::GetParent($Source).FullName.TrimEnd('\') -ne $ProjectsRoot) {
    throw "Origem não está diretamente dentro da pasta canônica de projetos: $Source"
}
if (-not $Destination.StartsWith(($ArchiveRoot + '\'), [StringComparison]::OrdinalIgnoreCase)) {
    throw "Destino escapou da raiz autorizada no G:: $Destination"
}
if (Test-Path -LiteralPath $Destination) {
    $destinationManifestPath = Join-Path $Destination 'project_manifest.json'
    if (-not (Test-Path -LiteralPath $destinationManifestPath -PathType Leaf)) {
        throw "Destino existente não contém project_manifest.json; retomada bloqueada: $Destination"
    }
    $destinationProjectId = [string]((Get-Content -LiteralPath $destinationManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json).project_id)
    if ($destinationProjectId -ne $ProjectId) {
        throw "Destino existente pertence a outro projeto; retomada bloqueada: $destinationProjectId"
    }
    [Console]::WriteLine("RESUME_VERIFIED_DESTINATION={0}", $Destination)
}

$reparsePoints = @(Get-ChildItem -LiteralPath $Source -Recurse -Force -Attributes ReparsePoint -ErrorAction Stop)
if ($reparsePoints.Count -gt 0) {
    throw "A origem possui $($reparsePoints.Count) reparse points; cópia automática bloqueada."
}

$sourceFilesBefore = @(Get-ChildItem -LiteralPath $Source -Recurse -File -Force)
$sourceBytesBefore = [Int64](($sourceFilesBefore | Measure-Object -Property Length -Sum).Sum)
$gDrive = [IO.DriveInfo]::new('G:\')
if (-not $gDrive.IsReady) {
    throw 'O disco G: não está pronto.'
}
if ($gDrive.AvailableFreeSpace -lt ($sourceBytesBefore + 1GB)) {
    throw 'Espaço livre insuficiente no G: para backup com margem de segurança.'
}

$catalogBefore = @(Get-CatalogItems)
$projectBefore = @($catalogBefore | Where-Object { $_.projectId -eq $ProjectId })
if ($projectBefore.Count -ne 1) {
    throw "Esperava exatamente uma entrada do Gohan no catálogo; encontrei $($projectBefore.Count)."
}
$queueBefore = Get-QueueSnapshot
if ($queueBefore.ContainsProject) {
    throw 'Há um job do projeto Gohan ativo ou pendente; retirada bloqueada.'
}

New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null

Write-Output ("COPY_START_FILES={0}" -f $sourceFilesBefore.Count)
Write-Output ("COPY_START_BYTES={0}" -f $sourceBytesBefore)

$robocopy = Join-Path $env:SystemRoot 'System32\robocopy.exe'
& $robocopy $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /MT:16 /NP /NFL /NDL /LOG:$RobocopyLog
$robocopyExitCode = $LASTEXITCODE
Write-Output ("ROBOCOPY_EXIT={0}" -f $robocopyExitCode)
if ($robocopyExitCode -ge 8) {
    throw "Robocopy falhou com código $robocopyExitCode. A origem foi preservada."
}

$sourceInventory = @(Get-ArchiveInventory -Root $Source -Label 'SOURCE')
$destinationInventory = @(Get-ArchiveInventory -Root $Destination -Label 'DESTINATION')
$sourceSignature = @(Get-InventorySignature -Inventory $sourceInventory)
$destinationSignature = @(Get-InventorySignature -Inventory $destinationInventory)
$differences = @(Compare-Object -ReferenceObject $sourceSignature -DifferenceObject $destinationSignature)
if ($differences.Count -gt 0) {
    throw "A comparação SHA-256 encontrou $($differences.Count) diferenças. A origem foi preservada."
}

& $robocopy $Source $Destination /MIR /L /COPY:DAT /DCOPY:DAT /R:0 /W:0 /XJ /NP /NFL /NDL /LOG+:$RobocopyLog
$dryRunExitCode = $LASTEXITCODE
Write-Output ("ROBOCOPY_DRYRUN_EXIT={0}" -f $dryRunExitCode)
if ($dryRunExitCode -ne 0) {
    throw "A conferência final do Robocopy detectou diferença (código $dryRunExitCode). A origem foi preservada."
}

$manifestPath = Join-Path $Destination 'ARCHIVE_SHA256.csv'
$sourceInventory | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8

$manifest = Get-Content -LiteralPath (Join-Path $Destination 'project_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$relativeFinal = [string]$manifest.final_output.file
$archivedFinal = Join-Path $Destination $relativeFinal
if (-not (Test-Path -LiteralPath $archivedFinal -PathType Leaf)) {
    throw "O vídeo FHD final não existe no backup: $archivedFinal"
}
$archivedFinalSha256 = (Get-FileHash -LiteralPath $archivedFinal -Algorithm SHA256).Hash.ToUpperInvariant()
if ($archivedFinalSha256 -ne $ExpectedFinalSha256) {
    throw "Hash do FHD no backup diverge: $archivedFinalSha256"
}

$easyExportArchived = $null
if (Test-Path -LiteralPath $EasyExport -PathType Leaf) {
    $easyExportSha256 = (Get-FileHash -LiteralPath $EasyExport -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($easyExportSha256 -ne $ExpectedFinalSha256) {
        throw "A cópia fácil em E: não corresponde ao FHD esperado: $easyExportSha256"
    }
    $easyExportArchived = Join-Path $Destination 'GOHAN_SSJ2_VIDEO_COMPLETO_FHD60_V5.mp4'
    Copy-Item -LiteralPath $EasyExport -Destination $easyExportArchived
    $easyArchiveSha256 = (Get-FileHash -LiteralPath $easyExportArchived -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($easyArchiveSha256 -ne $ExpectedFinalSha256) {
        throw 'Falha ao validar a cópia fácil do FHD no backup.'
    }
}

$queueBeforeRemoval = Get-QueueSnapshot
if ($queueBeforeRemoval.ContainsProject) {
    throw 'Um job do Gohan apareceu durante o backup; retirada bloqueada e origem preservada.'
}

$verifiedAt = (Get-Date).ToString('o')
$report = [ordered]@{
    status = 'ARCHIVE_VERIFIED_PENDING_SOURCE_REMOVAL'
    project_id = $ProjectId
    source = $Source
    destination = $Destination
    source_files = $sourceInventory.Count
    source_bytes = Get-InventoryBytes -Inventory $sourceInventory
    destination_files_before_archive_metadata = $destinationInventory.Count
    destination_bytes_before_archive_metadata = Get-InventoryBytes -Inventory $destinationInventory
    all_source_destination_sha256_match = $true
    archive_manifest = $manifestPath
    archived_final = $archivedFinal
    archived_final_sha256 = $archivedFinalSha256
    easy_export_archived = $easyExportArchived
    robocopy_exit_code = $robocopyExitCode
    robocopy_dry_run_exit_code = $dryRunExitCode
    catalog_before_count = $catalogBefore.Count
    catalog_before_gohan_count = $projectBefore.Count
    queue_running_before = $queueBefore.Running
    queue_pending_before = $queueBefore.Pending
    queue_running_before_removal = $queueBeforeRemoval.Running
    queue_pending_before_removal = $queueBeforeRemoval.Pending
    verified_at = $verifiedAt
    source_removed = $false
    recoverable_from = $Destination
}
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ExternalReport -Encoding UTF8
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Destination 'ARCHIVE_VERIFICATION_20260827.json') -Encoding UTF8

$resolvedBeforeRemoval = [IO.Path]::GetFullPath($Source).TrimEnd('\')
if ($resolvedBeforeRemoval -ne $Source -or [IO.Directory]::GetParent($resolvedBeforeRemoval).FullName.TrimEnd('\') -ne $ProjectsRoot) {
    throw 'Validação final do alvo de remoção falhou.'
}

Write-Output 'SOURCE_REMOVAL_START=True'
Remove-Item -LiteralPath $resolvedBeforeRemoval -Recurse -Force
if (Test-Path -LiteralPath $resolvedBeforeRemoval) {
    throw 'A pasta de origem ainda existe após a remoção.'
}

$catalogAfter = @(Get-CatalogItems)
$projectAfter = @($catalogAfter | Where-Object { $_.projectId -eq $ProjectId })
$queueAfter = Get-QueueSnapshot

$report.status = if ($projectAfter.Count -eq 0) { 'PASS_ARCHIVED_AND_REMOVED_FROM_MAESTRO' } else { 'FAIL_STILL_VISIBLE_IN_MAESTRO' }
$report.catalog_after_count = $catalogAfter.Count
$report.catalog_after_gohan_count = $projectAfter.Count
$report.queue_running_after = $queueAfter.Running
$report.queue_pending_after = $queueAfter.Pending
$report.source_removed = $true
$report.removed_at = (Get-Date).ToString('o')
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ExternalReport -Encoding UTF8
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Destination 'ARCHIVE_VERIFICATION_20260827.json') -Encoding UTF8

if ($projectAfter.Count -ne 0) {
    throw 'O backup foi validado e a origem removida, mas a API do Maestro ainda lista o projeto.'
}

Write-Output 'FINAL_STATUS=PASS_ARCHIVED_AND_REMOVED_FROM_MAESTRO'
Write-Output ("ARCHIVE={0}" -f $Destination)
Write-Output ("REPORT={0}" -f $ExternalReport)
Write-Output ("CATALOG_BEFORE={0}" -f $catalogBefore.Count)
Write-Output ("CATALOG_AFTER={0}" -f $catalogAfter.Count)
Write-Output ("FINAL_SHA256={0}" -f $archivedFinalSha256)
