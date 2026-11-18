param(
    [string]$Python = "python",
    [int]$Steps = 1200,
    [string]$KreaModelPath = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\unet\flux1-krea-dev.safetensors"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root "daily_lora_cycle.py"

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\Pemara\gpu_window_guard.ps1" -Name "sprunki-krea-lora-weekly" -Kind "training"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bloqueado pela janela global de GPU. Permitido somente 00:31-04:59."
    exit 0
}

if (-not (Test-Path -LiteralPath $KreaModelPath)) {
    Write-Error "Modelo Krea de treino nao encontrado: $KreaModelPath"
    exit 1
}

$deadline = (Get-Date).Date.AddHours(4).AddMinutes(59).ToString("s")

& $Python $Script `
    --deadline $deadline `
    --run-prefix "lora_krea" `
    --flux-model $KreaModelPath `
    --steps $Steps `
    --python $Python

exit $LASTEXITCODE
