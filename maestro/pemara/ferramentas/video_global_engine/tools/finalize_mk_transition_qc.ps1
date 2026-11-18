param(
    [string]$ProjectDir = "E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_transicoes_h3"
)

$ErrorActionPreference = "Stop"

$evidenceByTake = [ordered]@{
    B01_02 = "qc/B01_02_contact_4x3.jpg and qc/B01_02_editorial_2s_gpu_preview.mp4"
    B02_03 = "qc/B02_03_occlusion_contact_4x3.jpg"
    B03_04 = "qc/B03_04_contact_4x3.jpg"
    B04_05 = "qc/B04_05_contact_4x3.jpg"
    B05_06 = "qc/B05_06_contact_4x3.jpg"
    B06_07 = "qc/B06_07_contact_4x3.jpg"
    B07_08 = "qc/B07_08_contact_4x3.jpg"
}

$manifestPaths = @(
    (Join-Path $ProjectDir "production_manifest.json"),
    (Join-Path $ProjectDir "take_queue.json")
)

foreach ($manifestPath in $manifestPaths) {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    foreach ($take in $manifest.takes) {
        if (-not $evidenceByTake.Contains($take.id)) {
            continue
        }

        $gate = $take.qc.transition_motion_gate
        $gate.status = "approved"
        $gate.evident_camera = $true
        $gate.real_depth = $true
        $gate.internal_action = $true
        $gate.clear_progression = $true
        $gate.evidence = $evidenceByTake[$take.id]
    }

    if ($manifest.PSObject.Properties.Name -contains "updated_at") {
        $manifest.updated_at = [DateTime]::UtcNow.ToString("o")
    }
    $manifest | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}

Write-Output "QC visual registrado para $($evidenceByTake.Count) conectores em $($manifestPaths.Count) manifestos."
