param(
    [string]$Python = "python",
    [switch]$DownloadKrea,
    [switch]$DownloadKreaFullTrainingModel,
    [switch]$RunCompare,
    [switch]$InstallKreaWeeklyTraining
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComfyModels = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models"
$KreaFp8 = Join-Path $ComfyModels "unet\flux1-krea-dev_fp8_scaled.safetensors"
$KreaFull = Join-Path $ComfyModels "unet\flux1-krea-dev.safetensors"

Push-Location $Root
try {
    if ($RunCompare) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Pemara\gpu_window_guard.ps1" -Name "sprunki-flux-weekly-compare" -Kind "gpu-generation"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Comparacao FLUX bloqueada pela janela global de GPU. Permitido somente 00:31-04:59."
            return
        }
    }

    & $Python .\freeze_baseline.py
    if ($LASTEXITCODE -ne 0) { throw "freeze_baseline.py falhou" }

    if ($DownloadKrea) {
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\download_krea_assets.ps1", "-Python", $Python)
        if ($DownloadKreaFullTrainingModel) {
            $args += "-FullTrainingModel"
        }
        & powershell @args
        if ($LASTEXITCODE -ne 0) { throw "download_krea_assets.ps1 falhou" }
    }

    $comfyOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -UseBasicParsing -TimeoutSec 5
        $comfyOk = ($resp.StatusCode -eq 200)
    } catch {
        $comfyOk = $false
    }

    if ($RunCompare) {
        if (-not $comfyOk) {
            Write-Warning "ComfyUI nao esta rodando em 8188. Comparacao A/B pulada."
        } elseif (-not (Test-Path -LiteralPath $KreaFp8)) {
            Write-Warning "Krea FP8 nao encontrado em $KreaFp8. Comparacao A/B pulada."
        } else {
            & $Python .\compare_flux_models.py
            if ($LASTEXITCODE -ne 0) { throw "compare_flux_models.py falhou" }
        }
    }

    if ($InstallKreaWeeklyTraining) {
        if (-not (Test-Path -LiteralPath $KreaFull)) {
            Write-Warning "Modelo Krea completo nao encontrado em $KreaFull. Tarefa semanal Krea nao instalada."
        } else {
            & powershell -NoProfile -ExecutionPolicy Bypass -File .\install_weekly_krea_lora_task.ps1 -Python $Python
            if ($LASTEXITCODE -ne 0) { throw "install_weekly_krea_lora_task.ps1 falhou" }
        }
    }
} finally {
    Pop-Location
}
